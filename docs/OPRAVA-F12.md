# F12 – riadený lokálny proces ASR

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Vývojový bod návratu `F12-20261014`; verzia ostáva **2.1.3b**, bez publikovania.
Zachované sú predchádzajúce rozpracované opravy, oba preklady a používateľské dáta.

## Potvrdený stav a zmena

Hlavná cesta prepisovania používala daemon vlákno `App.work`. Natívnu inferenciu nebolo možné spoľahlivo prerušiť a potvrdenie zápisu fronty nemalo časový limit. Existujúce transakčné checkpointy a disková PCM cache už boli implementované; ostávajú základom obnovy.

- `asr_batch.py` obsahuje pôvodné riadenie dávky, s rovnakým `ModelManager`, backendmi a `jobs.transcribe_job`. Celá príprava, načítanie modelu a prepis bežia v lokálnom procese vytvorenom pomocou `spawn`. Jeden model sa opakovane používa v rámci dávky a pri skončení procesu sa uvoľní. Medzi dávkami sa načíta znova.
- `asr_process.py` oddeľuje správy od objektov Tk. Protokol v1 používa náhodné ID behu, rastúce poradové číslo, ID potvrdenia a pri zmene položky ID fronty. Nesprávny beh/protokol/poradie či neplatné ID položky sa odmietne. Príkazy pracujú len cez lokálnu rúru; nahrávky ani text sa neposielajú na externú službu.
- Potvrdenie zápisu fronty má limit 15 sekúnd. Dialóg GPU → CPU automaticky odmietne po 120 sekundách; transport čaká najviac 125 sekúnd. Bez výslovného potvrdenia sa CPU nepoužije. Technická príčina zostáva v spracovaní.
- Signál zastavenia sa prenesie do procesu. Po 10 sekundách sa nereagujúci proces ukončí. Heartbeat má limit 60 sekúnd; samotné heartbeat správy neobnovujú limit 900 sekúnd bez pracovného pokroku. Tieto limity sú pomenované konštanty v `asr_process.py`.
- Windows Job Object s `KILL_ON_JOB_CLOSE` vlastní ASR aj jeho prípadné vnorené procesy sťahovania. ASR nezačne pracovať pred pridelením vlastníctva. Pri páde rodiča Windows ukončí strom; uzavretie komunikačnej rúry je ďalšia ochrana.
- Rozhranie povoľuje ďalší beh až po ukončení pracovníka. Zatvorenie okna najskôr zastaví ASR, potom vykoná existujúce kontroly uloženia. Plná fronta udalostí má samostatný neblokujúci signál dokončenia. Správy zo staršieho behu sa ignorujú.
- Po neočakávanom ukončení sa rozpracovaná položka označí ako prerušená. Existujúce pokračovanie overí vstup a nastavenia a zopakuje iba nedokončený chunk. Úplné checkpointy sa neprepisujú. Vynútené zastavenie môže zanechať dočasné PCM súbory; existujúce bezpečné čistenie odstráni neaktívne súbory staršie než 24 hodín.

Reálny test navyše odhalil, že Windows môže pri riadnom zatvorení rúry vrátiť `BrokenPipeError` namiesto `EOFError`. Obe situácie sa teraz považujú za koniec komunikácie; úspech stále vyžaduje správu o dokončení a úspešné ukončenie procesu.

## Overenie

`test_asr_process.py` spúšťa skutočné procesy Windows. Simulovaná inferencia pokrýva pád s kódom 17 po prvom checkpointe, pokračovanie a opakované spustenie bez duplicít, potvrdenie/odmietnutie GPU fallbacku, nedoručené potvrdenie, neodpovedajúci výpočet s heartbeat, zastavenie, zaplnenie fronty, odmietnutie starého behu, zatvorenie skutočného Tk okna a haváriu rodiča s overením ukončenia pracovníka.

Zachované testy GPU kontrolujú aj chybu pri iterovaní výsledkov a zmiešaný režim. Kompletné regresné testy kontrolujú checkpointy, exporty, históriu úprav, oba jazyky a vzhľady vrátane simulovaných mierok Tk. Nejde o ručné overenie všetkých systémových DPI Windows.

Nový diagnostický príkaz používa skutočný procesový pipeline, lokálny model Tiny, CPU, offline režim, VAD, zmiešaný CZ/SK režim, projekt a export:

Konečné overenie 14. 10. 2026: **187 regresných testov prešlo** (173,789 s); po posledných úpravách životného cyklu a zachovania jazyka relácie prešlo aj **25 cielených testov** (16,358 s). Finálne EXE vykonalo dva prepisy syntetickej nahrávky po troch segmentoch za 3,828 s a 3,140 s. Diagnostika overila rozdielne PID rodiča a ASR procesu. Prešla aj samostatná skúška Tk, tkdnd, sounddevice, importu voliteľného hlasového runtime, projektu a TXT/SRT exportu. Testy používajú oddelené profily a výstupy.

```powershell
& '.\ND TranskripThor.exe' --self-test-process C:\cesta\ku\cache C:\cesta\nahravka.wav C:\cesta\diagnostika
```

Cache musí obsahovať kompletný Tiny model v existujúcej štruktúre aplikácie. Príkaz nič nesťahuje a výstupom je `process-diagnostic.json`. Používajte samostatný diagnostický priečinok. Ide o prevádzkovú skúšku, nie o meranie jazykovej presnosti Tiny. Presné výsledky a protokoly sú pri zostave v `OVERENIE.json`.

## Zostavenie a návrat

Nie je potrebná nová externá závislosť. Zachovaný `TranskripTHOR.spec` zahŕňa nové importované moduly; vstupný bod naďalej volá `multiprocessing.freeze_support()` pred spracovaním argumentov.

V existujúcom Windows prostredí so závislosťami projektu:

```powershell
python -m PyInstaller --noconfirm --distpath outputs/dev-F12-20261014 --workpath work/build-F12-20261014 packaging/TranskripTHOR.spec
python work/run_f08_tests.py
```

Samostatná zostava je v `outputs/dev-F12-20261014`. `Spustit-vyvojovu-zostavu.cmd` používa vlastný profil. Zachovajte celý podpriečinok aplikácie vrátane `_internal`. Modely nie sú pribalené. Predchádzajúce zostavy zostávajú nezmenené. Zdrojový archív, kontrolné súčty a testové protokoly tvoria bod návratu; existujúce projekty skúšajte z kópie.

## Obmedzenia

Skutočné GPU/CUDA ani plný KInIT model sa v tejto úlohe neoverujú; hardvérové chyby a rozhodnutie používateľa sú simulované. Nová ASR izolácia nemení samostatnú funkciu rozlíšenia hlasov. Veľmi pomalý jednotlivý výpočet bez udalosti pokroku dlhší než 15 minút sa zámerne zastaví; vhodný je menší model alebo výkonnejšie zariadenie. Nie je pridaný automatický nekonečný reštart po chybe: používateľ spustí pokračovanie prerušenej položky.

Zostava bola spustená na tomto Windows počítači, nie na samostatnej čistej inštalácii Windows. Diagnostika tkdnd overuje načítanie rozšírenia, nie reálne pretiahnutie z Prieskumníka. Prehrávanie cez reproduktory ani Narrator neboli v tejto úlohe manuálne skúšané.
