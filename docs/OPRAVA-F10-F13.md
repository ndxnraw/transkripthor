# F10/F13 — ukladanie na pozadí a samostatná fronta

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

## Potvrdená príčina

Po opravách F01–F09 editor stále volal SQLite zápis, vytváranie revízie a TXT/SRT export priamo v obsluhe tlačidla. Stránkovanie neznižovalo túto záťaž. `save_state()` zapisoval nastavenia aj celú frontu JSON; odobratie a presun nemali rovnaký rollback ako pridanie.

## Zmeny

- Editor sleduje zmenené segmenty podľa stabilného ID a lokálneho poradového čísla zmeny. Pri Save zachytí aktívny text a odovzdá iba zmenené záznamy, titulkový profil a konkrétny bod Undo histórie. SQLite pripojenie aj export vlastní pracovné vlákno; pracovník nikdy nevolá Tk.
- Počas zápisu a exportu zostáva možné písať, vyhľadávať, meniť segmenty a používať Undo/Redo. Opakované spustenie Save/Retry export sa odmietne s vysvetlením, kým prebieha predchádzajúca operácia. Zatvorenie počas zápisu sa odloží: po dokončení ho používateľ zopakuje. Aplikácia nerozhoduje sama o zahodení novších zmien.
- Potvrdenie transakcie označí za uložený iba odoslaný bod a profil. Novšie textové, hlasové a titulkové úpravy zostanú neuložené. Chyba databázy zachová zoznam zmien pre opakovanie; chyba exportu nemení už úspešné uloženie projektu.
- `Project.edit()` kontroluje aj návrat textu cez Undo a nezapisuje nezmenený záznam. Prvá uložená revízia tvorí úplný nemenný základ. Ďalšie revízie obsahujú odkaz na základ/predchádzajúcu revíziu a iba rozdiely. Staré úplné revízie zostávajú čitateľné. Čítanie reťazca je iteratívne; originály modelu sa nemenia. Export stále publikuje konzistentnú dvojicu TXT/SRT podľa F05, z konkrétnej uloženej revízie.
- Fronta používa samostatnú SQLite transakciu, poradie a ID. Zapisujú sa iba nové/zmenené položky alebo zmenené pozície, odstránenia patria do tej istej transakcie. Nastavenia naďalej používajú malý atómový `settings.json` a nikdy nezapisujú frontu.
- Pridanie, odobratie, presun a stavy úloh používajú spoločný postup: pri úspechu obnovia zobrazenie; pri chybe zachovajú pôvodnú frontu aj výber a oznámia príčinu. Potvrdenie workerovi/IPC nastane až po zápise.
- Starý `queue.json` sa pri prvom otvorení importuje a zostáva nedotknutou zálohou. Po úspešnom importe je autoritatívny `queue.sqlite3`; prázdna nová fronta nespustí opätovný import starej zálohy. Prerušené vytvorenie databázy bez tabuľky sa dá zopakovať.

## Meranie odozvy

`work/benchmark_f10.py` používa izolované syntetické projekty, skutočný Tk event loop a 10 ms periodický callback. Meria Save po úprave jedného segmentu, najprv vytvorenie základnej revízie a potom rozdielovú revíziu. Nezahŕňa otvorenie editora, dekódovanie zvuku ani ASR. Doba zahŕňa potvrdenie databázy, celý export aj doručenie výsledku do UI.

Meranie na tomto Windows (13. 10. 2026), `work/benchmark-f10-results.json`:

| Segmenty | Revízia | Odovzdanie Save | Celé uloženie/export | Najdlhšia medzera UI | 95. percentil medzier |
|---:|---|---:|---:|---:|---:|
| 10 000 | základná | 0,84 ms | 0,306 s | 157,59 ms | 26,14 ms |
| 10 000 | rozdielová | 0,95 ms | 0,302 s | 89,09 ms | 33,18 ms |
| 100 000 | základná | 0,53 ms | 2,006 s | 206,75 ms | 126,83 ms |
| 100 000 | rozdielová | 0,92 ms | 1,918 s | 217,73 ms | 85,16 ms |

Ide o jedno meranie každej kombinácie, nie garanciu výkonu. Python vlákna zdieľajú GIL; krátke oneskorenia počas serializácie a väčších alokácií zostávajú merateľné. Rozhranie nečakalo na celý zápis ani export.

## Overenie a obmedzenia

Nové regresie overujú úpravu počas zablokovaného pracovného zápisu, presnú exportovanú revíziu bez novšieho textu, ďalšie uloženie, odmietnutie súbežného Save/Retry/zatvorenia, chybu databázy a opakovanie, skutočný SQL zákaz zápisu nezmenených segmentov, Undo bez zbytočného zápisu, rollback pridania/odobratia/presunu, oddelenie nastavení, migráciu starej fronty a rollback chyby uprostred SQLite transakcie.

Existujúce testy ukladania čakajú na dokončenie skutočného pracovného vlákna pri pokračujúcom spracovaní udalostí Tk; pôvodné kontroly textu, časov, originálov, exportných chýb, titulkov a Undo zostali zachované.

Celá regresná sada: **171 testov, OK (125,909 s)**, `work/tests-f10-final.log`. Cielená sada súbežného ukladania a titulkov: **10 testov, OK**. Prvý úplný beh mal jediný neúspešný test očakávajúci okamžité zatvorenie pri Save; teraz výslovne overuje otvorené okno počas zápisu a zatvorenie až po dokončení. `git diff --check` bez chýb whitespace. Testy bežali natívne vo Windowse, nie vo WSL. Nové EXE ani ručné vizuálne scenáre sa pri tejto úlohe neoverovali.

Implementácia: `src/editor.py`, `project.py`, `prepis.py`, `state.py`, katalógy `locales/en.json` a `locales/sk.json`. Nové testy: `test_background_save.py` a pomocný `test_io_support.py`. Adaptované existujúce testy: `test_edit_history.py`, `test_editor_speakers.py`, `test_export_pair.py`, `test_ownership.py`, `test_studio.py`, `test_subtitle_profile.py`, `test_ui_v2.py`. Merací skript je `work/benchmark_f10.py`; nevyžaduje nové závislosti ani model.

Krátke zápisy nastavení a transakcie fronty ostávajú synchrónne (SQLite čakanie na zámok najviac 1 s). Meranie 10k/100k sa týka segmentov prepisu, nie počtu položiek fronty. Otvorenie celého prepisu a veľké dávkové úpravy nie sú predmetom tohto merania. Revízie sa na export rekonštruujú v pamäti pracovníka; dlhá história zvyšuje čas a pamäť. Staršie EXE bez podpory rozdielových revízií nemajú otvárať novo uložené projekty; starý JSON fronty je záloha, nie synchronizovaná kópia.

Používateľské dáta a existujúce nesúvisiace zmeny zostali zachované. Verzia sa nezvyšuje, EXE ani release sa nepublikuje.
