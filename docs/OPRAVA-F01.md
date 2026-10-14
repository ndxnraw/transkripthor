# F01 – zachovanie úprav pri dokončení rozlíšenia hlasov

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Oprava z 8. októbra 2026, bez zmeny verzie a bez publikovania vydania.

## Potvrdená príčina a riešenie

Editor pri doručení výsledku hlasov zrušil aktívny výber a prekreslil bloky bez
zachytenia textu vo vstupnom poli. Pracovné vlákno navyše dostávalo živý zoznam
segmentov a výsledky sa priraďovali podľa poradia.

`src/editor.py` teraz pred zlúčením zachytí aktívnu editáciu. Výpočet
dostáva nemenný obraz ID a časových hraníc; výsledky sa vracajú ako mapa podľa
existujúcich databázových ID. Každý výpočet má vlastný token. Zastaralý výsledok
sa nepoužije a nezhodný počet výsledkov skončí chybou bez zmeny priradení.

Pri spustení sa zapamätajú časové hranice, hovoriaci a revízia ručného priradenia
každého segmentu. Ručné zmeny počas výpočtu majú prednosť, vrátane premenovania
v celom prepise a zmeny následne vrátenej na pôvodnú hodnotu. Zmenené časové
hranice sa tiež neprepíšu. Samotná úprava textu priradeniu hlasu nebráni.

`src/transcript_blocks.py` aktualizuje iba existujúce hlavičky blokov.
Aktívny Text sa nevytvára znova: zostáva výber, kurzor, história undo, stránka,
filter aj posun textu a zoznamu. Formát projektu, modely a závislosti sa nemenia.

## Overenie

`tests/test_editor_speakers.py` obsahuje šesť úspešných regresných testov:

- Písanie počas skutočného pracovného vlákna, zmena stránky, zachovanie kurzora,
  označeného textu a nenulového posunu; uloženie a nové otvorenie editora,
  kontrola TXT, SRT a časových značiek v oboch vzhľadoch.
- Vyhľadávanie počas výpočtu a zachovanie úprav aj mimo aktuálneho filtra.
- Ručné priradenie a zmena späť na pôvodného hovoriaceho.
- Hromadné premenovanie počas výpočtu.
- Ignorovanie starého výsledku a zmenených časov; priradenie podľa ID aj pri
  inom poradí segmentov a ID odlišných od indexov rozhrania.
- Chybný počet výsledkov bez straty rozpísaného textu, následné uloženie.

Celá sada pri prvom behu: 94 testov, 93 úspešných; jediná chyba je už
zdokumentované F02 – nedostupné tlačidlo „Spustiť čakajúce“ pri mierke 2.
Po doplnení samostatného scenára vyhľadávania opätovne prešlo všetkých šesť
testov F01. Sada naďalej vypisuje existujúce upozornenia Tcl ThemeChanged pri
rušení testovacích okien. Testy používajú výhradne dočasné projekty a stav.

Spustenie s existujúcimi projektovými závislosťami a `src` na PYTHONPATH:

```text
python -m unittest test_editor_speakers -v
powershell -NoProfile -File scripts/test.ps1 -v
```

## Hranice overenia

Tk editor, pracovné vlákno, databáza a exporty sú skutočné; výsledky hlasového
modelu a načítanie audia sú v týchto testoch simulované. Nejde o meranie kvality
rozlíšenia hlasov. Oprava nerieši súbežný zápis iného procesu do toho istého
projektu ani ostatné zistenia auditu. EXE nebolo nanovo zostavené ani publikované.
Existujúce používateľské dáta a nesúvisiace rozpracované zmeny zostali zachované.
