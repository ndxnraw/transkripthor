# F11 — blokový zvuk a uvoľnenie modelu

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

## Zistenie a implementácia

`jobs.py` aj `Player.load()` volali pôvodné `faster_whisper.audio.decode_audio()`, ktoré najprv skladá celý s16 obsah a potom vytvára float32 pole. Táto spotreba rástla s dĺžkou zvuku aj bez modelu. Skoršie F03/F10 riešili bezpečnosť checkpointov a ukladanie prepisu, nie toto dekódovanie.

Nový `pcm_audio.py` používa rovnaký PyAV dekóder, mono s16 resampler, zoskupovanie rámcov a finálny flush ako existujúca knižnica. Výstup však priebežne zapisuje na disk. `DiskAudio` poskytuje počet vzoriek a čítanie intervalov v celých vzorkách; na float32 sa prevedie iba požadovaný interval. Nevykonáva časové seekovanie v komprimovanom zdroji. Nemapuje celý súbor do rezidentnej pamäte.

- Hlavná projektová pipeline používa PCM pre všetky modely, CPU/GPU aj zmiešaný režim. ASR dostáva iba existujúci naplánovaný úsek.
- VAD dostáva najviac 62 s zvuku: 60 s jadro plus sekundový kontext na každej strane. Výsledky sa orežú na jadro, posunú podľa presného počtu vzoriek a dotýkajúce sa intervaly zlúčia. Existujúce `speech_chunks` naďalej určuje hranice ASR. Pri nových projektoch môže blokový VAD určiť iné hranice než predchádzajúci jeden beh nad celým zvukom; akustickú rovnosť VAD výsledkov nesľubujeme.
- Pri pokračovaní sa používa pôvodný uložený plán a overuje presný počet dekódovaných vzoriek aj fingerprint zdroja. Commit stále nastane iba po dokončení celého úseku. Prerušenie prípravy necháva platný stav F03, ktorý prípravu bezpečne zopakuje.
- Prehrávač číta krátke PCM bloky. Pause/seek aj hranice segmentu zostávajú v 16 kHz vzorkách. Kontroluje tiež zmenu zdroja počas dekódovania. Rozlíšenie hlasov používa rovnaké rozhranie rezov a svoje doterajšie trojsekundové okná.
- Samostatný lokálny adaptér a zmiešaný pomocný prepis tiež uvoľňujú vlastný PCM v `finally` po iterovaní. Starý diagnostický helper `transcribe_file` pri priamom použití obyčajného faster-whisper mimo projektovej pipeline stále používa vlastnú cestu knižnice; meranie sa vzťahuje na nové PCM a hlavnú aplikáciu.

## Disk a životný cyklus

Projektové dočasné súbory sú v `.pcm-cache/pcm-…/audio.s16`; pomocné volania bez projektu používajú adresár `nd-transkripthor-pcm` v systémovom temp. Spotreba je približne **115,2 MB za hodinu** mono 16 kHz s16 zvuku. Pred každým zápisom sa kontroluje voľné miesto vrátane 32 MiB rezervy; skutočné ENOSPC/Windows 112 tiež dostane zrozumiteľnú lokalizovanú správu s ďalším krokom. Súbežné zápisy iných programov môžu disk zaplniť aj medzi kontrolami; výnimka stále prejde bezpečnou cestou.

Každý súbor má OS lease. Po prepise, chybe alebo zastavení sa odstráni; pri editore pri zatvorení/uvoľnení prehrávača. Aktívne súbory sa pri čistení neodstraňujú. Zvyšky po tvrdom páde staršie ako 24 hodín sa odstránia pri ďalšej príprave v rovnakom cache adresári, iba ak nemajú vlastníka. Čistenie sa týka výlučne vlastných známych scratch názvov. Pri nemožnom odstránení sa chyba zaznamená a čistenie sa odloží. Nepoužité projekty sa globálne neprehľadávajú.

PCM je regenerovateľný dočasný súbor, nie checkpoint ani databáza. Nedokončené dekódovanie sa nezačína uprostred komprimovaného súboru: pri obnove sa zopakuje. Už dokončený prepis a časové značky zostávajú zachované. Používateľské audio ani výsledky sa nemažú.

## Model v pamäti

Správca modelov má akciu **Release model memory / Uvoľniť model z pamäte**. Používa existujúci `ModelManager.close()`, zruší aj referenciu aplikácie a uvoľní príslušný lease. Beží mimo Tk vlákna, počas prepisu alebo rozlíšenia hlasov sa odmietne. Súbory stiahnutého modelu zostávajú na disku; nasledujúci prepis model načíta znova. Akcie správcu sa zalamujú pri malej šírke.

## Meranie

`work/benchmark_f11.py`: skutočné PyAV dekódovanie hodinového a dvojhodinového syntetického WAV, pôvodná/nová implementácia v samostatných procesoch Windows. Oba varianty následne čítajú 30-sekundové bloky a počítajú kontrolný súčet. `GetProcessMemoryInfo` meria špičkový working set procesu, vrátane importov (základ približne 49 MiB). Nejde o meranie reálneho ASR, GPU ani celej aplikácie s modelom. Výsledky: `work/benchmark-f11-results.json`.

| Dĺžka | Pôvodné maximum | PCM maximum | Pôvodný čas | PCM čas |
|---|---:|---:|---:|---:|
| 1 h | 600,86 MiB | 61,31 MiB | 1,081 s | 0,982 s |
| 2 h | 1 150,17 MiB | 62,36 MiB | 1,884 s | 1,728 s |

Počet vzoriek a kontrolný súčet boli zhodné (57 600 000 a 115 200 000 vzoriek). Ide o jedno meranie každej kombinácie na tomto počítači. Model, VAD a embeddingy majú vlastné nároky; úspora zvukového bufferu negarantuje dostupnú VRAM pre veľký model. PCM prehrávanie číta disk v callbacku, preto jeho plynulosť na veľmi pomalom alebo preťaženom úložisku nie je zaručená.

## Overenie

Nové testy kontrolujú vzorkovo presnú zhodu s pôvodným dekóderom na stereo 44,1 kHz WAV cez hranicu dekódovacích blokov, náhodné rezy aj koniec súboru, VAD hranice a maximálny vstup, nedostatok miesta, chybu dekódera, zastavenie, ochranu aktívnej cache, čistenie opusteného súboru, prehrávač a reálny PCM stop/checkpoint/resume bez duplicít a s časmi 0,1 a 6,1 s. Uvoľnenie modelu overuje zákaz počas spracovania, pracovné vlákno a zachovanie modelových súborov pomocou testovacej inštancie, nie reálne meranie GPU VRAM.

Celá regresná sada: **178 testov, OK (145,740 s)**, log `work/tests-f11-final.log`. Cielené testy PCM, modelu a ASR: **30 testov, OK**. Prvý úplný beh odhalil dve staré testovacie náhrady (globálne VAD intervaly a pôvodné miesto dekódovania); boli presunuté na nové integračné miesto bez odstránenia pôvodných kontrol jazykov, časov a chýb GPU. Záverečná kontrola PCM/prehrávača, uvoľnenia modelu a lokalizácie prešla tiež (`work/tests-f11-check.log`, 14. 10. 2026). `git diff --check` bez chýb whitespace. Testy a merania bežali natívne vo Windowse, s oddelenými testovacími dátami.

Zmenené: `pcm_audio.py`, `jobs.py`, `playback.py`, `editor.py`, `speech_models.py`, `mixed_language.py`, `model_dialog.py`, oba katalógy a príslušné testy v `src`. Žiadne nové závislosti; používa sa existujúce PyAV/numpy/faster-whisper. Verzia a vydanie sa nemenia. Nové EXE, ručná skúška zvukového zariadenia a kvalita VAD na reálnych rozhovoroch neboli v tomto kroku overené.
