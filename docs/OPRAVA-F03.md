# F03 – bezpečná príprava a pokračovanie projektu

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Oprava z 8. októbra 2026. Verzia zostáva nezmenená, vydanie ani EXE neboli vytvorené.

## Príčina

Projekt predtým vznikal až po hashovaní a jeho metadata sa zapisovali až po
dekódovaní a detekcii reči. Zastavenie po dekódovaní zanechalo prázdne tabuľky.
Fronta poznala cestu projektu, ale editor očakával platný zdroj a mohol spadnúť.

## Zmeny

- `src/project.py`: vytvorenie tabuliek a zápisy metadát používajú
  explicitné transakcie. Pred hashovaním sa uloží zdroj, jeho veľkosť a čas zmeny,
  nastavenia, nulový checkpoint a fáza `preparing`.
- Príprava rozlišuje kroky `hashing`, `decoding` a `vad`. Úplný kontrolný súčet
  sa uloží pred dekódovaním. Plán úsekov, počet vzoriek a fáza `ready` sa zapíšu
  spolu až po dokončení prípravy. Nasledujú fázy `transcribing` a `complete`.
- `src/jobs.py`: prerušená príprava sa pri pokračovaní bezpečne zopakuje.
  Nastavenia a zdroj sa kontrolujú; ak už existuje úplný kontrolný súčet, musí sa
  zhodovať. Pripravený projekt použije uložený plán a existujúci checkpoint.
  Zastavenie sa kontroluje aj po hashovaní, dekódovaní, VAD a zostavení plánu.
- Staré projekty bez označenia fázy sa naďalej otvárajú. Prázdna stará databáza
  sa môže inicializovať znova; neúplné metadata s existujúcimi dátami sa nesmú
  potichu resetovať. Databáza bez tabuliek po veľmi skorom páde sa obnoví.
- `src/prepis.py` a `editor.py`: kontrola projektu prebehne pred
  vytvorením editora alebo zatvorením iného otvoreného editora. Prerušená príprava,
  projekt bez textu a dokončený prázdny prepis majú zrozumiteľné odlišné správy.

Pri prerušenej položke použite **Pokračovať**. Ak príprava ešte nebola dokončená,
zopakuje sa. Pri zmenenej nahrávke alebo nastaveniach aplikácia pokračovanie odmietne;
použite pôvodné nastavenia alebo nový prepis do nového projektu.

## Overenie

Nových osem testov v `test_preparation.py` a `test_ui_v2.py` overuje:

- zastavenie počas hashovania, dekódovania, VAD a pred prvým checkpointom;
- násilné ukončenie skutočného podprocesu cez `os._exit` v rovnakých fázach,
  následné otvorenie databázy a pokračovanie bez duplicitného textu;
- rollback nedokončeného prvého zápisu metadát aj zápisu pripraveného plánu;
- zachovanie existujúcich dát pri neúplných metadátach, starý prázdny projekt,
  kompatibilitu pripraveného projektu bez nového označenia fázy;
- odmietnutie zmenených nastavení a obsahu nahrávky aj pri zachovanej veľkosti
  a čase zmeny, keď je už uložený úplný kontrolný súčet;
- správne časové značky a export po obnovení;
- blokovanie otvorenia prázdneho editora a konkrétne používateľské vysvetlenia.

Celá sada: **103 testov, 102 úspešných**. Jediné zlyhanie zostáva predchádzajúce
F02: tlačidlo „Spustiť čakajúce“ pri 200 % mierke. Prešli aj všetky testy F01
a existujúce testy pokračovania po uložených checkpointoch. Existujúce upozornenia
Tcl ThemeChanged pri rušení testovacích okien zostávajú.

S projektovými závislosťami a `src` na PYTHONPATH:

```text
python -m unittest test_preparation test_ui_v2.DesktopTest.test_editor_rejects_unprepared_and_empty_projects_without_creating_window -v
powershell -NoProfile -File scripts/test.ps1 -v
```

## Obmedzenia

Dekódovanie, VAD a ASR sú v regresných scenároch simulované; databáza, exporty,
Tk a ukončenie podprocesu sú skutočné. Nešlo o nové meranie reálneho modelu.
Zastavenie počas blokujúceho dekódovania alebo VAD sa vykoná po návrate príslušnej
knižnice; táto oprava nepridáva násilné ukončovanie jej vlákna.

Pred dokončením prvého hashovania možno zdroj porovnať iba podľa cesty, veľkosti
a času zmeny. Úplný kontrolný súčet ešte neexistuje. Po jeho uložení sa overuje aj
obsah. Starý úplne prázdny projekt nemá pôvodnú identitu ani nastavenia: obnoví sa
pre zdroj a nastavenia aktuálnej položky fronty. Používateľské dáta, oprava F01
a ostatné nesúvisiace zmeny sa nemenia.
