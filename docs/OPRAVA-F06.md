# F06 – vlastníctvo profilu, projektu a modelov

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Oprava z 9. októbra 2026. Verzia sa nemení, vydanie ani nový EXE sa nepublikujú.

## Jedna aktívna inštancia

Pred načítaním fronty aplikácia získa OS zámok profilu. Bežná cesta zostáva
`%LOCALAPPDATA%/LokalnyPrepis`. Druhé bežné spustenie nevytvorí App a nečíta ani
nezapisuje jej frontu. Absolútne cesty z argumentov uloží atómovo do `incoming/`
a skončí. Prvý proces požiadavky spracuje na Tk vlákne, keď práve neprepisuje.

Príjem používa rovnakú validáciu a deduplikáciu ako Pridať nahrávky. Požiadavka
sa odstráni až po úspešnom uložení fronty. Pri chybe zápisu ostáva na opakovanie;
pri páde medzi uložením a potvrdením sa znovu doručené cesty deduplikujú.
Poškodené požiadavky dostanú príponu `.invalid`, odmietnuté neexistujúce cesty
`.rejected`. Pridanie súborov nespúšťa prepis.

Zámok vlastní OS otvoreným súborovým handle, nie uložené PID či časový limit.
Pri páde procesu sa uvoľní automaticky; ponechaný súbor zámku nebráni štartu.
Živému procesu sa zámok nekradne. Súbory `.instance.lock`, `.project.lock`
a `.models.lock` počas práce ručne nemažte.

Samostatný profil možno spustiť:

```text
python src/prepis.py --profile C:\Testy\Thor-profil "C:\Zvuk\ukážka.wav"
```

Taký profil má vlastné nastavenia, frontu, doručovací priečinok, modelovú cache
a predvolený priečinok výsledkov. Pôvodne uložený výstupný priečinok sa rešpektuje.
Bežný profil zachováva doterajšie cesty. Diagnostické režimy si zachovávajú svoje
oddelené testovacie priečinky.

## Projekty a modely

`Project` drží zámok počas celej práce s databázou vrátane prípravy, migrácie,
prepisu a exportu. Editor pred uvoľnením počiatočného databázového prístupu
prevezme ďalšiu referenciu na zámok a drží ju až do zničenia okna. Druhý proces
projekt neotvorí; dostane slovenské vysvetlenie namiesto tichého prepísania.
Vnorené prístupy rovnakého procesu sú povolené, aby editor mohol ukladať.

ModelManager drží zámok cache od načítania po uvoľnenie modelu, aj medzi súbormi.
Rovnaká ochrana pokrýva sťahovanie a výpočet hlasov. Odstránenie vyžaduje výhradný
zámok bez vnoreného zdieľania: odmietne sa aj v tom istom procese, pokiaľ cache
ešte používa iná operácia. Správca modelov pred bežným odstránením uvoľní načítaný
model, ako doteraz. Po zavretí aplikácie sa model aj profil uvoľnia.

Cache sa zamyká konzervatívne ako celok. Dve rôzne inštancie preto nemôžu súčasne
používať jednu spoločnú cache, ani keď vybrali odlišné modely. Použite samostatné
profilové cache alebo najprv zavrite inštanciu, ktorá spoločnú cache vlastní.

## Overenie

Osem testov v `test_ownership.py` používa reálne Windows podprocesy a izolované
dočasné profily. Overuje súčasný štart dvoch procesov, jedného vlastníka,
odovzdanie viacerých Unicode ciest reálnej App cez produkčný vstup programu,
nezmenenú frontu pred doručením, odloženie počas busy, deduplikáciu, haváriu,
obnovu nevybavenej požiadavky, chybu uloženia, nezávislé profily, blokovanie
projektu otvoreným Tk editorom a zámky modelovej cache vrátane odstránenia.
Načítanie modelu je simulované; nesťahovali sa veľké modely.

Celá sada pred poslednými dvoma doplnenými scenármi: **121 testov, 120 úspešných**.
Jediné zlyhanie zostáva známe F02 pri 200 % škálovaní. Finálne cielené testy
vlastníctva, pracovných kariet a príjmu súborov: **21/21 úspešných**. Existujúce
upozornenia Tcl ThemeChanged pri rušení okien v celej sade zostávajú.

```text
python -m unittest test_ownership test_studio.StudioTest test_file_drop -q
```

Príkaz vyžaduje projektové závislosti a `src` na PYTHONPATH. Zmenené sú
`ownership.py`, `prepis.py`, `project.py`, `editor.py`, `speech_models.py`,
`model_catalog.py` a nové testy. Existujúce opravy F01/F03/F04/F05 zostali zachované.

## Hranice

Odovzdanie je trvalá lokálna požiadavka, nie potvrdenie jej okamžitého pridania.
Ak vlastník skončí práve počas odovzdávania, požiadavku prevezme ďalšie spustenie.
Počas prepisu sa môže vybavenie odložiť až do jeho skončenia alebo zastavenia.
Externé editory databázy, staré verzie aplikácie ignorujúce zámky a ručné mazanie
zámkov sa touto kooperatívnou ochranou nedajú bezpečne koordinovať. Sieťové disky
a zostavený EXE neboli novým testom overené; overenie bežalo natívne vo Windowse
zo zdrojov, bez WSL. Používateľské profily sa na testovanie nepoužili.
