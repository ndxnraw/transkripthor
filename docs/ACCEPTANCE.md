# Záverečné prijímacie overenie — Pre-release

Dátum: 5. 11. 2026. Základ kandidáta: `52a4f5cbc894ade5b0280d16aecf518dff69ad11`,
Windows Tk, basic aj extended. Toto je protokol úlohy 32, nie nové vydanie.
Produkčný kód sa pri tomto overení nemenil; pribudla regresia kapacity SQLite.
Historický analytický dokument je zoznam rizík, nie dôkaz ich dnešného výskytu.

**Odporúčanie: kandidát zatiaľ NIE JE pripravený na finálne verejné vydanie.**
Automatické kontroly a dostupné lokálne skúšky prešli, ale nižšie uvedené
systémové, hardvérové, kvalitatívne a distribučné podmienky ostávajú otvorené.
Neoverené scenáre nie sú vydávané za potvrdené chyby ani za úspech.

## Prostredie a dôkazy

Windows 11 Pro 10.0.26300, Intel Core i5-12450HX, približne 15,7 GiB RAM,
Intel UHD / Intel Arc A530M. NVIDIA GPU nie je dostupné; CTranslate2 hlási
0 CUDA zariadení, PyTorch 2.8.0+cpu hlási CUDA nedostupnú. Python 3.12.10,
projektová `.venv`, uzamknuté závislosti podľa `requirements/`.
Kompletný lokálny KInIT model sa nenašiel; nové veľké váhy sa nesťahovali.
Windows Sandbox nie je dostupný. Hostiteľ má nainštalovaný Python.

Prvý úplný beh `scripts/test.ps1`: **301 testov, 274,107 s, OK, 0 preskočených**.
Následne nová regresia SQLite: **1 test, 0,070 s, OK**. To nie je tvrdenie
o jednom úplnom behu 302 testov. Presný commit musí pred synchronizáciou
prejsť novým úplným behom a zostavením z čistého klonu; výsledok identifikuje
lokálny build manifest a správa o synchronizácii, nie starší počet testov.

Lokálne dôkazy (ignorované, nepublikovať zvuk, projekty ani súkromné logy):
`outputs/acceptance32-tests.log`, `acceptance32-storage.log`,
`acceptance32-offline/offline-report.json`, `acceptance32-resume/report.json`,
`acceptance32-long-audio.json`, `acceptance32-large-editor.json`,
`acceptance32-exe-basic.log`, `acceptance32-exe-extended.log`.

## Matica podľa analytického dokumentu

| Scenár | Skutočne vykonané overenie | Výsledok a hranica dôkazu |
| --- | --- | --- |
| 1. Čistý Windows, prvý model, offline | Reálny Tiny CPU z existujúcej cache; izolované EXE basic aj extended; offline sieťová kontrola | PASS v existujúcom Windows. Čistý OS bez Pythonu a prvé sťahovanie na ňom **NEOVERENÉ**. Odstránenie Pythonu z PATH nie je čistý OS. |
| 2. Súbory, Prieskumník, Unicode | Regresie Tcl zoznamov, registrácie cieľov, duplicít, busy a odmietnutia; otvorený reálny Explorer a EXE v izolovanom profile | Automatika PASS. Reálny drop medzi oknami sa nepodarilo dokončiť: **NEOVERENÝ**, vrátane viac súborov a busy. Priame volanie handlera ho nenahrádza. |
| 3. Prerušenie a pád | Reálny Tiny CPU zastavený po checkpointe a obnovený cez Tk; regresie prípravy, exportu a worker procesu | PASS: 1 checkpoint pred zastavením, po obnove 12 chunkov / 24 segmentov, zachovaný prefix a bez duplicít. Pády workerov sú reálne procesy s mock ASR; nie pád reálnej GPU inferencie. |
| 4. Poškodené a presunuté dáta | Regresie projektov, odtlačku zdroja, modelovej revízie, neúplnej cache, nastavení; dekódovanie poškodeného WAV | PASS v testovacích dátach. Bez zásahov do používateľských projektov. Náhodné poškodenie produkčného disku sa nesimulovalo. |
| 5. Disk, oprávnenia, zamknutie, sieť | Nová reálna SQLite kapacitná chyba; Windows zámok súboru; injektované chyby exportu/oprávnení/ENOSPC a transportné integračné testy | PASS. SQLITE_FULL zachová text aj počet revízií, quick_check OK, opakovanie a otvorenie zachová originál. Fyzické zaplnenie disku, odpojenie siete pri veľkom modeli a skutočne odobraté ACL **NEOVERENÉ**. |
| 6. CPU/GPU, oba backendy | Reálna Tiny CPU inferencia v oboch EXE, každá dvakrát; mock CUDA/cuBLAS/VRAM a potvrdenia fallbacku | CPU PASS. NVIDIA, reálna VRAM chyba a KInIT inferencia **NEOVERENÉ**. Intel GPU nie je CUDA. |
| 7. Editor, hlasy, história, audio | Regresie aktívnej editácie počas hlasov, stránkovania, vyhľadávania, Undo/Redo, revízií, ukladania, prehrávania; benchmark 10k/100k | Automatika PASS. Hlasy a audio zariadenia sú v príslušných UI testoch nahradené mockmi. Skutočné odpojenie reproduktora a posluchové hodnotenie rýchlosti **NEOVERENÉ**. |
| 8. Exporty a titulky | TXT/SRT/VTT/DOCX/JSON regresie vrátane Unicode, textu, časov, limitov a revízií; reálny EXE export TXT po inferencii | PASS. Validácia formátu nie je praktická kontrola každého cieľového prehrávača/Wordu. |
| 9. DPI, klávesnica, čítačka | Tk geometrická matica EN/SK, obe témy, 100/125/150/175/200 %, malé viewporty, klávesnicové regresie; reálne otvorenie tmavého EXE | Automatika PASS. Systémové DPI, prechod medzi monitormi, vysoký kontrast a Narrator **NEOVERENÉ**. Strom UIA hlavného Tk okna ukázal prevažne nepomenované panely; dostupnosť pre čítačku nemožno potvrdiť. |
| 10. Referenčná kvalita | Syntetický vlastný Windows SAPI zvuk, reálne Tiny spracovanie; validačné testy vyhodnocovacieho nástroja | Funkčné overenie PASS, nie meranie presnosti. Oprávnený ručne skontrolovaný korpus CZ/SK, mien, čísel a prechodov nebol k dispozícii; WER ani jazykovú presnosť neuvádzame. |

## Merania na tomto hostiteľovi

Offline Tiny revízia `d90ca5fe260221311c53c58e660288d3deb8d356`: 2 segmenty,
1,953 s, 0 Python sieťových pokusov, 30 vzoriek TCP, maximum 0 spojení,
0 chýb merania. Rozsah je Python audit a TCP aktuálneho procesu: nie úplný
packet capture, UDP, iné procesy ani fyzicky odpojená sieť.

Reálna inferencia/export cez samostatný proces zo zmrazených EXE:
extended 3,296 / 2,453 s, basic 3,453 / 2,875 s, vždy 2 segmenty.
Pomocník použil režim cs-sk nad syntetickým anglickým zvukom; výsledok dokazuje
funkčnú cestu spracovania a opakovanie, **nie kvalitu CZ/SK detekcie**.

| Dĺžka syntetického PCM | Pôvodné dekódovanie, peak RSS | Disková PCM cache, peak RSS | Počet vzoriek |
| --- | ---: | ---: | ---: |
| 1 hodina | 601,41 MiB | 62,75 MiB | 57 600 000 |
| 2 hodiny | 1 150,71 MiB | 62,76 MiB | 115 200 000 |

Počty a kontrolné sumy zhodné. Ide o reálne dekódovanie a blokové čítanie
generovaného zvuku, nie hodinový prepis reči.

| Syntetický prepis | Odovzdanie uloženia baseline/delta | Najväčšia medzera Tk heartbeat baseline/delta |
| --- | ---: | ---: |
| 10 000 segmentov | 1,45 / 0,80 ms | 38,16 / 17,96 ms |
| 100 000 segmentov | 0,57 / 0,67 ms | 76,33 / 101,91 ms |

Pri 100k p95 heartbeat 45,81 / 42,86 ms. Reálne Tk a ukladanie v pozadí,
syntetické segmenty a mock načítania audia; nie subjektívne meranie celého UI.

## Podmienky pred vydaním a opakovateľný postup

1. Na čistom Windows x64 bez Pythonu rozbaliť oba kandidátske ZIP, overiť SHA-256,
   spustiť ako bežný používateľ, stiahnuť model, prepis/export, reštart a offline opakovanie.
2. V Explorerovi pretiahnuť jeden a viac vlastných WAV s Unicode do prázdnej plochy
   aj naplnenej fronty; overiť počet, duplicity, tlačidlo pridania a odmietnutie pri práci.
3. Prakticky prejsť všetky karty a editor v oboch témach pri systémových DPI
   100–200 %, cez viac monitorov, minimalizáciu, Tab/Ctrl+S/vyhľadávanie;
   zapnúť Narrator a vysoký kontrast. Ak editor nie je použiteľný, opraviť pred vydaním.
4. Na NVIDIA stroji overiť oba backendy, vyčerpanie VRAM a potvrdený CPU fallback;
   na dostupnom CPU doplniť KInIT. Zmerať oprávnený referenčný korpus a dlhú reč.
5. V izolovanom testovacom zväzku doplniť fyzický nedostatok miesta pri PCM/exporte,
   ACL, prerušenie prenosu modelu a odpojenie audio zariadenia. Nezapĺňať systémový disk.
6. Uzavrieť natívne licenčné/redistribučné podmienky podľa [DISTRIBUTION.md](DISTRIBUTION.md).
   Chýbajúci podpisovací certifikát znamená nepodpísaný kandidát; nevytvárať falošný podpis.

Zostávajúce medzery sú blokermi úplného prijatia podľa zadania. Synchronizácia
tohto protokolu neznamená schválenie vydania ani publikovanie balíkov.
Autorstvo zostáva: Created by Daniel Návojský (ndxnraw) using Codex | 2026.
