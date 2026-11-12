# Vývoj na Windows a prenos na ďalší počítač

Aktuálny program je **Release v1** (1.0.0). Hlavné rozhranie je QML/Qt Quick.
`src/version.py` je jediný zdroj zobrazeného označenia, číselnej Windows verzie
aj príznaku stabilného vydania; generujú sa z neho VERSIONINFO aj assembly manifest.
Bežný SYNC tieto hodnoty nemení a nevytvára vydanie bez výslovnej požiadavky.
Historické poznámky Pre-release/Tk opisujú predchádzajúce stavy.

Zostavovanie a testy vyžadujú Windows x64 a presný CPython 3.12.10 s Tk.
Autoritatívny pin je `.python-version`, ktorý čítajú lokálne skripty aj CI.
Staršie záznamy o 3.12.14 sú historické, nie aktuálny predpis.
Python 3.12.10 má [oficiálnu Windows distribúciu](https://www.python.org/ftp/python/3.12.10/).
Pri inštalácii povoľte Tcl/Tk a pip. Potrebujete Git, internet na inštaláciu
balíkov/modelov a niekoľko GB voľného miesta. PyAV wheel obsahuje dekódovanie;
samostatný systémový FFmpeg sa pre aplikáciu nevyžaduje
([dokumentácia faster-whisper](https://github.com/SYSTRAN/faster-whisper#requirements)). Natívne runtime
vyžadujú Microsoft Visual C++ Redistributable x64; pri chýbajúcej DLL opravte
jeho inštaláciu zo stránky Microsoftu. Proxy/certifikáty riešte s IT, nikdy
nevypínajte TLS kontrolu. Skripty rešpektujú politiku spúšťania PowerShellu.

## Aktuálne rozhranie QML

`run.ps1` spúšťa produkčné Qt Quick rozhranie (`src/qml_main.py`), ktoré
používa existujúci používateľský profil a projektové formáty. Bežné
ovládanie je na jednej obrazovke bez kariet; editor a doplnkové nástroje
sa otvárajú podľa potreby. PySide6-Essentials a shiboken6 sú súčasťou
runtime locku a inštaluje ich štandardný `setup.ps1`.

`test.ps1` je povinná úplná sada; `test-qt.ps1` vykoná navyše produkčné
Qt scenáre v samostatnom procese, aby sa nemiešali event loopy Tk a Qt.
Predvolený `build.ps1` deleguje na `build-qt.ps1`, vykoná obe sady,
porovná všetky pribalené moduly a QML/preklady/assets a spustí reálne
Windows EXE s izolovaným profilom. Diagnostika skúša projekty na mieste,
uloženie, päť exportov, nemenný originál, posun zvuku, témy, importy
ASR knižníc a izolovaný ASR proces pri offline chybe chýbajúceho modelu.
Nevykonáva inferenciu váh ani meranie GPU.

QML zostava štandardne vzniká v novom `dist/qt-<čas>/ND TranskripThor/`;
konkrétny cieľ určuje `build.ps1 -OutputDirectory <priečinok>`. Spúšťajte
EXE spolu s celým priečinkom `_internal`. Manifest obsahuje aj kontrolné
súčty QML a presný zdroj použitý na zostavenie.

Pôvodné Tk rozhranie zostáva pre historické regresie a explicitné
`build.ps1 -Frontend tk`. Nasledujúce staršie odseky o Tk diagnostike sa
týkajú tejto voľby. `prototype_qml` a `build-qml.ps1` sú starší oddelený
experiment; nepredstavujú aktuálnu QML aplikáciu.

## Čistý počítač

V PowerShelli (z ľubovoľného vlastného pracovného priečinka):

```powershell
git clone https://github.com/ndxnraw/TranskripThor.git
cd TranskripThor
git switch main
git status --short --branch
.\scripts\setup.ps1 -Mode development
.\scripts\run.ps1
.\scripts\test.ps1
.\scripts\setup.ps1 -Mode build
.\scripts\build.ps1
```

Ak Python nie je v PATH ani v launcheri `py`, prvý setup spustite s
`-Python 'C:\cesta k Pythonu\python.exe'`. Skript vyžaduje Windows x64
Python podľa `.python-version` a Tk, vytvorí `.venv` len ak chýba a existujúce prostredie nemaže.
Opakovaná inštalácia je bezpečná; pip skontroluje locky a konzistenciu.
Pri zlyhaní vráti nenulový výsledok. Nepoužívajte `PYTHONPATH`/`PYTHONHOME`
ani `work/model-packages`. Príkazy fungujú aj s medzerami a diakritikou
v názve klonu; skripty odvodzujú cesty od vlastného umiestnenia.

Bežné spustenie: `setup.ps1 -Mode runtime`; vývoj používa rovnaké runtime
závislosti a štandardný `unittest` bez ďalšieho testovacieho frameworku.
Voliteľné hlasy pridá `setup.ps1 -Speakers`; režim build ich zahŕňa vždy,
pretože existujúca diagnostika EXE overuje aj tento runtime.

Editor sprístupní **Group similar voices / Zoskupiť podobné hlasy** až po
kontrole lokálnej cache a importov NumPy, ONNX Runtime (CPU provider) a
kaldi-native-fbank. Kontrola pri otvorení podrobností beží mimo Tk vlákna,
nesťahuje ani nenačítava váhy; pri spustení sa dostupnosť znovu preverí.
Import kontroluje aj chýbajúce natívne DLL, nie iba prítomnosť balíka.
Úspešný preflight nie je inferencia ani nové hashovanie váh: integritu
kontroluje správca modelov, chybu pri vytvorení ONNX session zachytí worker.
Ručné označenia a prepis fungujú aj bez voliteľných súčastí. Zoskupovanie
existujúcich úsekov nie je identifikácia osôb ani separácia prekryvov.
Algoritmus a prah sa pri F18 nemenia; ich zmena vyžaduje referenčné meranie.

Výsledok je `dist/ND TranskripThor/ND TranskripThor.exe`; `_internal` musí
zostať vedľa neho. Build vykoná celú regresnú sadu, porovná pribalený kód
so zdrojmi a spustí izolovanú diagnostiku Tk, ikon, prekladov, tkdnd, natívnych
importov a nového procesu. Táto skúška nepotrebuje model ani súkromný zvuk.
Bežné otvorenie okna sa dá overiť aj s izolovaným profilom:

```powershell
.\scripts\run.ps1 --profile "$env:TEMP\Thor vlastny test"
```

Voliteľný lokálny ZIP z už overeného buildu (nevytvára GitHub vydanie):

```powershell
.\.venv\Scripts\python.exe scripts\package.py --app 'dist\ND TranskripThor' --output 'outputs\kandidat-Windows.zip'
```

## Závislosti a ich udržiavanie

### Bežný prepis na jednej obrazovke

Hlavné okno nepoužíva viditeľné pracovné karty. `ViewStack` zobrazuje jeden
rámec; interné meno `workspace_tabs` zostáva pre kompatibilitu existujúcich
príkazov. Jazyk a kvalita sú priamo pri nahrávkach. Krátke názvy kvality
mapujú na pôvodné stabilné modelové ID, nemenia backend ani uložené nastavenia.

Prázdna plocha má jedinú hlavnú akciu Pridať nahrávky a podporuje pôvodný
COPY-only FileDrop. Po pridaní sa ten istý ovládač presunie nad zoznam,
zobrazí sa Spustiť prepis a pri chýbajúcom výbere sa označí prvá nová
nahrávka. Ukazovatele priebehu sa objavia pri práci, nie ako neaktívna
technická výbava úvodného okna. Podrobnosti, odobratie a poradie sú natívne
príkazy ponuky Akcie/Ďalšie možnosti s pôvodnými podmienkami dostupnosti.

Bežný online štart ide rovno do existujúceho workera; chýbajúce súbory
pripraví ten istý modelový mechanizmus s pôvodnými udalosťami priebehu.
Správcu modelov netreba otvárať. Ak je uložený režim iba offline a potrebný
model chýba, jediná otázka ponúkne vypnutie tohto režimu a pokračovanie
cez internet. Odmietnutie ponechá režim aj hlavnú obrazovku bez spustenia
workera; prijatie je explicitná voľba používateľa, nie tichý sieťový fallback.
Kontroly pripnutej revízie a zariadenia zostávajú zachované.

Možnosti obsahujú pokročilé nastavenia, modely, technické podrobnosti,
výsledky a vzhľad. Doplnkové zobrazenie má Späť na nahrávky; návrat
editor neničí, neukladá ani znovu nevykresľuje. Ctrl+Tab v editore sa vráti
do pracovného toku, nepreskakuje cez modely a nastavenia. Technické vnorené
záložky ostali iba v dobrovoľne otvorených diagnostických nástrojoch.

`test_simple_studio.py` overuje prázdny aj naplnený stav, skutočnú klikateľnosť
hlavnej akcie, ponukové príkazy a ich busy guards, online štart bez správcu
modelov, explicitné vypnutie offline režimu aj návrat z neuloženého editora.
Prázdny stav má samostatnú EN/SK maticu 100–200 % a oboch kontrastných
paliet; pôvodná matica teraz navyše napĺňa front a zobrazuje priebeh, aby
naďalej kontrolovala všetky pracovné ovládače, nie iba úvodnú plochu.

### Uvoľňovanie Tk objektov vo vlákne rozhrania

`presentation/tk_lifecycle.py` poskytuje `TkVariables`: drží pôvodné natívne
StringVar/BooleanVar/DoubleVar do zániku ich konkrétneho okna alebo rámca.
V Destroy obsluhe vo vlákne rozhrania vykoná pôvodné Tk unset/trace cleanup
a odpojí premennú od interpretera. Neskorší Python finalizátor už nevolá Tcl.
Voľby Comboboxu patria samotnému widgetu; premenné exportného dialógu patria
tomuto dialógu, nie živému editoru. Zrušenie zatvárania nič neuvoľňuje.

Zaniknutý interpreter zostáva dočasne pripnutý, kým hlavné vlákno neuprace
nepoužívané cykly widgetov a neostanú k nemu ďalšie odkazy. Uvoľnenie sa
vykoná pri nasledujúcom vytvorení vlastníka alebo pri ukončení procesu.
Zber pamäte sa globálne nevypína; triedy ani finalizátory tkinter sa
neprepisujú a výnimky sa nepotláčajú. Implementácia cieli na podporovaný
CPython 3.12.10 a jeho počítanie odkazov.

Pracovníci lokálnej diagnostiky dostávajú iba snímku vstupov, signál
zastavenia a front udalostí; neuzatvárajú v sebe dialóg ani aplikáciu.
`scripts/run_tests.py` stále vypisuje pôvodné ignorované výnimky a zároveň
ich považuje za zlyhanie celého behu. Samotné unittest OK ich už neprehliadne.

Šesť regresií v `tests/test_tk_lifecycle.py` núti `gc.collect()` v pracovníkovi
pri živom aj zaniknutom vlastníkovi, kontroluje unset/odstránenie traces
v UI vlákne, opakované zániky a uvoľnenie interpreterov, odmietnutie
vytvárania premennej v pracovníkovi a zachovanie rozpracovaného editora,
zrušeného zatvorenia, Späť/Znova aj pôvodného projektu na disku.

### Prístupnosť a integračné doladenie (fáza 5)

Nastavenia oddeľujú pevný spodný panel pomoci od posúvateľného formulára.
`ScrollFrame` odvodzuje rozsah od obsahu a po presune fokusu odhalí celé
pole alebo správu. Koliesko spracúva iba vo vlastnom formulári; textové
polia, natívne voľby a ostatné karty si zachovávajú vlastné správanie.
Pri zániku formulára sa odstránia jeho väzby na okno. Voľba automatického
prehrávania je v spoločnej karte s jazykom rozhrania; jej hodnota a uloženie
zostávajú pôvodné. Dlhšie vysvetlenia ostávajú iba na čítanie a posúvateľné.

`FlowFrame` prepočíta riadky aj po `<<ThemeChanged>>`, aby zmena rozmerov
prvkov neorezala tlačidlá. Pri zániku ruší vlastný čakajúci idle callback.
`MessageView` po zatvorení odregistruje textové pole aj sledovanie hodnoty.
Vysvetlenia vytvorené cez `DialogPanel.message()` zalamujú podľa aktuálnej
šírky obsahu, vrátane zúženého chybového okna a nastavení prehrávania.
Natívne kontrastné checkboxy a prepínače majú explicitné systémové obrysy
a veľkosť indikátora odvodenú od mierky, takže sú rozlíšiteľné aj bez zaškrtnutia.
Hlavné okno vlastní jediný plánovaný kontrolný cyklus: pri priamom obnovení
ho nahradí a pri zániku okna zruší. Zatváranie počas ASR naďalej čaká
na pôvodné bezpečné ukončenie práce.
Rovnako vlastní odložené uloženie nastavení: okamžité uloženie aj zánik
okna rušia pôvodný časovač, aby po zatvorení neostal neplatný Tcl príkaz.

`tests/test_ui_acceptance.py` dopĺňa osem regresií: všetky karty v EN/SK,
Tk scaling 100/125/150/175/200 %, svetlá/tmavá téma a obe simulované
kontrastné palety, zatvorenie pred prekreslením, uvoľnenie správ a traces,
nové rozmery tlačidiel, úzky dialóg, poradie Tab bez zakázaných akcií
a odhalenie nastavení/pomoci pri presune fokusu v nízkom okne a ukončenie
kontrolného cyklu hlavného okna. Pôvodné
regresie editora, neuložených úprav, výstupov, DnD a balenia zostávajú
súčasťou celého behu. Nejde o fyzické prepínanie Windows DPI/kontrastu
ani certifikáciu čítačky obrazovky. Závislosti a verzia sa v tejto fáze nemenia.

### Editor a dialógy (fáza 4)

Editor používa spoločné povrchy pre informácie o zdroji a neuloženom stave,
vyhľadávanie/uloženie a spodné ovládanie. Jedinou vyplnenou hlavnou akciou
editora je Uložiť projekt. Prehrávanie, segmenty, hlasy, titulkový profil,
Undo/Redo a export zachovávajú pôvodné príkazy a podmienky dostupnosti.
Zdrojový názov je v tom istom scrollovateľnom riadku pred stavom audia.

`DialogPanel` v `presentation/responsive.py` zdieľa titulok, povrch a
priestor pre akcie medzi prehrávaním, voľbami exportu, diagnostikou dát a
chybovým dialógom. Veľkosť sa obmedzuje rozmermi obrazovky bez vnoreného
`update_idletasks` počas otvárania. Technické detaily chýb sú naďalej
zbalené a iba na čítanie. Správa modelov používa rovnaké sekčné a akčné
štýly. Systémové výbery súborov a pôvodné potvrdenia zostávajú zachované.

ThemeManager sleduje životný cyklus jednotlivých editorov aj mimo zoznamu
`app.editors`, aby aktualizoval sémantické značky vyhľadávania. Prepnutie
témy ani vysokého kontrastu nevolá `render`, `capture` či uloženie projektu.
Existujúce Text widgety, kurzor, výber, posun a história zostávajú na mieste.
Poslucháči sa pri zániku editora uvoľnia; odložené kreslenie titulnej lišty
vlastní koreň, takže rýchle zatvorenie dialógu nemaže čakajúci Tcl príkaz.
Klasické Tk vstupy/tlačidlá v pôvodných jednoduchých otázkach dostávajú
rovnakú paletu, pričom ttk prvky naďalej používajú svoje ttk štýly.

Regresie `tests/test_editor_theme.py` overujú neuložený text a históriu,
vyhľadávacie značky, rozpracované voľby prehrávania, čitateľný diagnostický
náhľad, životný cyklus dialógov a otvorenie z obsluhy udalosti. Používajú
skutočný Tk a simulované kontrastné palety, nie zmenu nastavení Windows.

### Hlavné pracovné okno (fáza 3)

Karta Nahrávky oddeľuje front so stavmi, kartu Spracovanie a spodný panel
so spustením/zastavením. Front využíva zostávajúcu výšku; ovládanie aj
spracovanie majú rezervované miesto. Ukazovatele nahrávky a dávky sú vedľa
seba, ale naďalej používajú pôvodné nezávislé merania. Technický stav
zariadenia je dostupný na karte Podrobnosti spracovania.

Spustiť prepis je jediná vyplnená hlavná akcia. Je dostupná pri čakajúcich
položkách a neprázdnej výstupnej ceste mimo spracovania; kontrola modelu a
ostatné validačné pravidlá zostávajú zachované. Pokračovanie/opakovanie sa
naďalej spúšťa kontextovou akciou vybranej položky. Odobrať z fronty odstráni
iba položku zo zoznamu, nie zdrojový súbor. Rozpracované projekty zostávajú
dostupné aj cez pôvodnú ponuku Ďalšie možnosti.

Textový stav Pripravené/fáza/Dávka ukončená kopíruje životný cyklus pôvodného
workera; ukončenie dávky nevyhlasuje všetky položky za úspešné. Počty chýb,
prerušenia a dokončenia sú stále v súhrne a v riadkoch frontu. Stavy majú
text aj symbol, nespoliehajú sa na samotnú farbu.

MessageView podporuje povrch `bg` alebo `card` zo spoločnej palety, ktorý
sa zachováva aj pri zmene témy. Žiadne nové závislosti ani zmena verzie.
Regresie `tests/test_workspace.py` dopĺňajú pôvodné testy priebehu,
drag-and-drop, tém a DPI. Náhľad so simulovanými stavmi nie je ASR test.

### Spoločná správa vzhľadu (fáza 2)

Hlavná Tk aplikácia vyžaduje ttkbootstrap 2.2.7 cez `runtime.in` a runtime lock.
`presentation/theme.py` je jediný zdroj paliet a správca témy pre jeden Tk
interpreter. Bežné režimy `thor-light`/`thor-dark` vytvára ttkbootstrap;
existujúce sémantické názvy ttk štýlov zostávajú kompatibilné bez globálneho
prepisovania widget API. Vlastné obrázkové pozadia `rounded_styles` už hlavná
aplikácia nepoužíva.

Windows vysoký kontrast má prednosť: správca prečíta `SPI_GETHIGHCONTRAST`
a `GetSysColor`, aktivuje natívny `clam` bez Bootstrap obrázkov a použije
systémové farby pre prvky, výber, texty, menu a Combobox popdown. Natívna
titulná lišta dostane predvolené systémové farby. Stav sa kontroluje pri
mapovaní/fokuse okien aj každú sekundu. Nastavenia Windows sa nezapisujú.
Uložená používateľská hodnota `light`/`dark` sa pritom nemení; po vypnutí
kontrastu sa zvolený režim obnoví. Používateľ môže voľbu zmeniť aj počas
aktívneho kontrastu pre neskorší návrat.

Nové Tk okná sa farbia pri mapovaní, otvorené okná pri zmene palety.
Textové polia a menu používajú spoločné pomocné metódy; označené oblasti
vyhľadávania upravuje editor bez obnovovania textu alebo nastavení projektu.
Pri Bootstrap theme walk sa zachovávajú existujúce odsadenia a hrúbky okrajov
Tk Text polí. Zmena témy tak nezväčšuje obsah pevných MessageView rámcov
a neorezáva stavové správy; samostatná regresia overuje celú výšku riadka.
Životný cyklus správcu uvoľňuje singleton štýlov/fontov pri zániku koreňa
vytvoreného cez TkinterDnD aj plain Tk, vrátane testovacích reštartov.

Regresie v `tests/test_theme.py` používajú skutočný Tk a simulované čierne
aj biele Windows palety. Nenahrádzajú fyzické prepnutie systému ani
certifikáciu čítačky obrazovky. Kompletnú sadu spúšťa `scripts/test.ps1`.
Štartová diagnostika nového EXE overuje aj oba režimy témy.

Samostatný výstup hlavnej aplikácie bez prepisu predchádzajúcej distribúcie:

```powershell
.\scripts\build.ps1 -OutputDirectory "dist\moja-nova-zostava"
```

### Samostatná vzorka ttkbootstrap (fáza 1)

Vzorka `src/prototype_ttkbootstrap/main.py` má vlastný vstup a nemení bežné
spustenie aplikácie. Používa projektovú `.venv`, ttkbootstrap 2.2.7 a existujúci
Pillow 12.3.0. Úplný reťazec a SHA-256 wheelov pre vzorku sú v
`requirements/ttkbootstrap.lock`. Od fázy 2 je ttkbootstrap aj priamou
závislosťou hlavnej aplikácie; toto je naďalej samostatná ukážka bez ASR.

```powershell
.\scripts\setup-ttkbootstrap.ps1
.\scripts\run-ttkbootstrap.ps1
.\scripts\test-ttkbootstrap.ps1
.\scripts\build-ttkbootstrap.ps1
```

Build najskôr vyžaduje celú stabilnú regresnú sadu a samostatné kompatibilitné
testy. Výsledok je v novom časovo označenom `dist/ttkbootstrap-*`, takže
neprepisuje existujúce EXE. Overenie skopíruje zostavu do dočasnej Unicode
cesty a spustí ju bez Pythonu v PATH. Windows metadata sa generujú z
`src/version.py`; verzia sa nemení.

Vzorka umožňuje pridať súbory cez výber alebo existujúci COPY-only FileDrop,
prepínať tému, upravovať skúšobný text a otvoriť vedľajšie okno. Prepisovanie
je výslovne nedostupné. Používa iba dočasný profil na diagnostiku DnD;
neotvára používateľské profily, projekty ani modely.

Kompatibilitná skúška zahŕňa skutočné Tk widgety, tkdnd registráciu, doručenie
Tcl zoznamu ciest do drop handlera, zachovanie textu/výberu, fokus, EN/SK,
prepínanie tém a tri životné cykly koreňového okna. Tk scaling 100–200 %
nenahrádza fyzickú skúšku Windows DPI ani ťahanie z Prieskumníka.
Vysoký kontrast je zatiaľ iba zistený v diagnostike; jeho integrácia patrí
do ďalšej fázy a vzorka ho ešte nezaručuje.

Pri zmene verzie najskôr získajte čistý Windows resolver report cez projektový
Python s `pip install --dry-run --ignore-installed --only-binary=:all:` pre
`requirements/ttkbootstrap.in` a existujúce `requirements/constraints.txt`.
Do doplnkového locku preneste celý deklarovaný reťazec, presné verzie a
SHA-256 wheelov z reportu. Report je lokálny výstup, nepatrí do Gitu.

### Stabilný runtime

Používame pip/venv. `.in` sú deklarované priame požiadavky;
`constraints.txt` je kontrolovaný reťazec verzií; `runtime.lock`,
`speakers.lock` a `build.lock` uzamykajú všetky nepriame závislosti a konkrétne
Windows wheely SHA-256. Sú určené pre CPython 3.12 x64. Nepreberajú balíky
zo zdieľaného runtime. Zachovali sa zaznamenané verzie existujúcich závislostí;
nové chýbajúce nepriame položky sú z čistého resolvera. Historický zoznam
`BUILD-BASELINE.txt` je evidencia staršej zostavy, nie inštalačný predpis.

Po cielenej úprave `.in` a constraints vytvorte v čistom Windows prostredí
resolver report, vygenerujte locky a zopakujte čistý klon/testy/build:

```powershell
.\.venv\Scripts\python.exe -m pip install --dry-run --ignore-installed --only-binary=:all: -r requirements\build.in -c requirements\constraints.txt --report "$env:TEMP\Thor-resolve.json"
.\.venv\Scripts\python.exe scripts\lock_dependencies.py "$env:TEMP\Thor-resolve.json"
```

Príkaz nemení nainštalované balíky pri resolver kroku. Nevkladajte report do
Gitu: môže obsahovať lokálnu index/proxy konfiguráciu. pip a CPython sú nástroje
prípravy prostredia; build nástroje vrátane PyInstalleru a hooks sú v locku.

## Modely, GPU a offline

Modely nie sú v Git ani v EXE. Správca modelov ich stiahne pomocou existujúceho
overovania, obnoviteľného prenosu a cache. Predvolené modely faster-whisper sú
`Systran/faster-whisper-{tiny,small,medium,large-v3}` s referenciou `main`;
presný commit sa uloží do projektu. KInIT je `kinit/whisper-large-v3-sk`,
ref `v2.0` (historicky `52c12346fbf4fe7c535f87471a57870c04223508`).
WeSpeaker používa commit `f0c48c298fd835726c27956a5d617bad7115627e`.
Tiny použitý v starších skúškach má commit
`d90ca5fe260221311c53c58e660288d3deb8d356`.

Správca rozlišuje chýbajúci, neúplný/zmenený, nájdený/neoverený a overený
model. Staršia štrukturálne úplná cache zostáva použiteľná, ale bez potvrdenia
sa neoznačuje za overenú. **Verify integrity / Overiť integritu** číta všetky
vybrané súbory mimo vlákna rozhrania. Online získa kontrolné súčty presnej
lokálnej revízie z Hubu; nesťahuje váhy ani neposiela nahrávky. Offline použije
kontrolné súčty z existujúceho potvrdenia. Bez nich treba jednorazové online
overenie; kontrolný súčet vypočítaný len z aktuálnych bajtov nie je dôkazom
správnosti starej cache. Zastavenie aj chyba ponechajú súbory na mieste.
Poškodenie opravte tlačidlom Download / Stiahnuť a kontrolu zopakujte.

Obnovenie inventára kontroluje štruktúru, veľkosti a časy zmien z potvrdenia,
nečíta znova všetky váhy. Nie je to ochrana pred úmyselnou manipuláciou
lokálneho používateľa s potvrdením a metadátami; pri pochybnostiach spustite
explicitné online overenie. Návrat na kartu aj dokončenie správy modelov či
dávky obnoví inventár so zachovaním výberu a posunu. Počas ASR/hlasov sa
zápisové operácie a explicitná kontrola vzájomne vylučujú cez zámok cache.

Predbežné stiahnutie presného modelu rovnakou cestou ako v aplikácii:

```powershell
.\.venv\Scripts\python.exe scripts\download_model.py tiny --cache "$env:LOCALAPPDATA\LokalnyPrepis\models" --revision d90ca5fe260221311c53c58e660288d3deb8d356
```

Pri prvom sťahovaní je potrebný internet a pri veľkých modeloch dostatok disku.
Potom zapnite „Iba offline“. Obnova projektu používa uložený snapshot, nikdy
ho potichu nenahradí aktuálnym `main`. Zachovajte celú cache vrátane refs,
snapshots, blobs a verifikačných záznamov; existujúce profily/cache netreba
premiestňovať ani znovu sťahovať kvôli uprataniu.

CPU je základ overovania. NVIDIA CUDA je voliteľná: faster-whisper vyžaduje
kompatibilné CUDA 12/cuDNN 9 runtime knižnice pre CTranslate2 4.8.2
([oficiálny GPU návod](https://github.com/SYSTRAN/faster-whisper#gpu)); KInIT
navyše GPU variant torch 2.8.0. Neinštalujte cudzie DLL do zdrojov. GPU variant
riešte v samostatnom prostredí podľa oficiálneho návodu dodávateľa a uzamknite
ho po reálnom overení; CPU lock nepredstiera uzamknutú ani overenú GPU zostavu.
Základné testy/CI nevyžadujú NVIDIA ovládač, GPU ani veľké modely.

Voliteľná reálna procesová skúška potrebuje oprávnený zvuk a stiahnutý Tiny:

```powershell
.\.venv\Scripts\python.exe scripts\verify_integration.py 'dist\ND TranskripThor\ND TranskripThor.exe' --cache "$env:LOCALAPPDATA\LokalnyPrepis\models" --audio 'C:\vlastne nahravky\ukazka.wav' --output 'outputs\integracia'
```

Ak nemáte oprávnenú ukážku, vytvorte syntetický zvuk zabudovaným Windows SAPI
hlasom: `scripts/create_test_audio.ps1 -Output 'outputs/synthetic-test.wav'`.
Ide o dostupný lokálny hlas, bez certifikácie jazyka alebo kvality prepisu.

`scripts/verify_ui_resume.py --audio ... --cache ... --output ...` navyše
overuje skutočné prerušenie po checkpointe, reštart UI a pokračovanie s pôvodnými
nastaveniami. Spúšťajte ho projektovým Pythonom; výstup musí byť nový priečinok.
Benchmarky `scripts/benchmark_f10.py --output ...` a `benchmark_f11.py --output ...`
merajú odozvu ukladania a diskové PCM, oddelene od povinných regresií.

Procesová skúška testuje dve reálne offline Tiny/CPU inferencie, SQLite a export. Výsledné dáta
sú lokálne. Nie je to meranie presnosti na reálnom korpuse; veľké KInIT/GPU
ani fyzické DPI/Explorer/screen reader sa tým neoverujú. Metodika korpusu je
v [src/eval/README.md](../src/eval/README.md). Súkromný manifest a merania
držte mimo zdrojov (napríklad v `work/`), nie vedľa sledovaného príkladu.

## Používateľské údaje a chyby

Dokončený prepis podporuje rozdelenie pri textovom kurzore s explicitným
časom hranice, zlúčenie susedných úsekov s rovnakým hovoriacim a úpravu
začiatku/konca v sekundách. Operácie zachovajú stabilné ID (nová časť dostane
nové ID), fungujú v projektovom Undo/Redo a pri ukladaní prenášajú len dotknuté
riadky/odstránenia. Neplatné intervaly, prekryvy a časy mimo známej dĺžky
audia sú odmietnuté. Slová po štrukturálnej zmene nemajú tvrdené presné časy.
Ručné hranice sa pri exporte nepredlžujú na mäkké minimum trvania titulku;
nesplnené minimum vyvolá upozornenie pri zachovaní ručne zadaného času.
Zlúčenie pridá jednu medzeru iba tam, kde medzi textami žiadna nie je.
Štrukturálne operácie sú počas ukladania a zoskupovania hlasov zablokované.
Nedokončený ASR projekt ich odmietne, aby sa nemenili hranice pokračovania.

Prvé štrukturálne uloženie zálohuje SQLite a transakčne zapne formát úložiska
2; obsah revízií sa rozšíri o odstránené ID. Staré plné/delta revízie sa stále
čítajú. Originál sa nemení. Starší klient odmietne nový formát namiesto toho,
aby pri čítaní ignoroval odstránené segmenty; záloha je bod návratu.

Uložiť projekt už automaticky nespúšťa export. Exportné možnosti čítajú
výslovne zvolený originál alebo uloženú revíziu na pracovnom vlákne. TXT,
SRT, VTT, DOCX a JSON sa zapíšu do novej generácie a až potom sa atómovo
prepne `exporty/aktualny-balik.json`. Predchádzajúce generácie sa nemažú.
Pri chybe zostane projekt uložený a predchádzajúci publikovaný balík platný.
SRT/VTT majú časovanie vždy; TXT/DOCX/JSON ho pridajú iba na požiadanie.
Označenia hovoriacich sú samostatná voľba pre všetky formáty. TXT/JSON
zachovávajú text aj Unicode; titulky používajú existujúce zalamovanie slov
a validáciu. JSON má `schema=1`, zdroj, revíziu a segmenty. DOCX je jednoduchý
Open XML dokument bez nových runtime závislostí. Neobsahuje makrá ani externé
vzťahy. Pri XML-neprípustnom znaku export zlyhá bez publikovania balíka.
Pôvodné TXT/SRT API a export pri dokončení ASR zostávajú kompatibilné.

V ponuke editora sú **Playback settings / Nastavenia prehrávania**:
výstupné zariadenie a tempo 0,75×, 1×, 1,25×, 1,5×. Voľba platí pre aktuálny
editor, neukladá sa do projektu ani nemení jeho stav úprav. Zoznam výstupov
sa obnoví pri otvorení dialógu. Explicitne vybrané nedostupné zariadenie sa
nenahradí iným; používateľ ho znovu pripojí alebo zvolí iný výstup a pokračuje.
Systémový predvolený výstup sa vyhodnocuje pri otvorení nového audio streamu.
Neočakávané zastavenie streamu pozastaví prehrávanie a zobrazí ďalší postup.

Posun myšou aj šípkami na časovej osi zachová pauzu/prehrávanie a zruší
obmedzenie na vybraný úsek: pokračuje od nového miesta do konca nahrávky.
Zmena rýchlosti alebo zariadenia zachová aktuálne miesto aj hranicu úseku.
F7/F8 sa neuplatnia v textových vstupoch; medzera pri písaní zostáva medzerou.
Tempo používa existujúci PyAV a [FFmpeg atempo](https://ffmpeg.org/ffmpeg-filters.html#atempo)
po blokoch PCM (najviac 4096 vstupných vzoriek), bez preladenia vzorkovacej
frekvencie hlasu a bez vytvárania ďalšej kópie celej nahrávky. Zobrazené časy
sú v pôvodnej časovej osi, s presnosťou audio bloku; latencia zariadenia môže
spôsobiť malý rozdiel oproti fyzicky počutému zvuku. Automatický test frekvencie
syntetického tónu nie je posluchovým hodnotením zrozumiteľnosti reálnej reči.

Vyhľadávanie v editore používa doslovné, neprekrývajúce sa výskyty bez
rozlišovania veľkosti písmen. Zachováva diakritiku; NFC normalizácia a Unicode
casefold slúžia iba na porovnanie, nemenia uložený text. Počet výskytov je
oddelený od počtu nájdených úsekov. Ponuka **Occurrences / Výskyty**, F3
a Shift+F3 prechádzajú dopredu/dozadu cyklicky, aj cez stránky. V aktívnom
textovom poli sa zvýraznia všetky zhody a odlišne aktuálny výskyt; navigácia
nespúšťa zvuk. Prázdny dotaz zruší filter. Po písaní sa zobrazí upozornenie
na neaktuálne výsledky; Hľadať, navigácia výskytov alebo zmena stránky najprv
zachytí úpravy a obnoví index. Pri nezmenenom texte sa index znova nepočíta.

**Open project / Otvoriť projekt** v hlavičke otvorí `projekt.sqlite3`
z existujúceho priečinka bez pridania položky do fronty. Prenášajte celý
priečinok projektu, nie samotné TXT/SRT. Platia existujúce zámky, kontrola
platnosti údajov a upozornenie na neuložené úpravy pred výmenou editora.

V ponuke **Segment and subtitles / Úsek a titulky** editora je akcia
**Locate original recording / Nájsť pôvodnú nahrávku**. Na pozadí overí
SHA-256 a veľkosť oproti uloženému odtlačku; až potom transakčne zmení cestu.
Nezmení originál, opravy, časovú os ani ASR nastavenia. Nahrávku nekopíruje
ani nepresúva. Prekódovaný alebo obsahovo zmenený súbor nie je totožná kópia.
Starý projekt bez odtlačku nemožno bezpečne pripojiť k náhradnej nahrávke.
Text a export zostávajú dostupné aj bez zvuku; stav prehrávania sa zobrazuje
v informačnej ploche editora. Fronta zostáva nezávislá: otvorenie ani oprava
cesty v projekte automaticky nespustí prepis a neprepíše položky fronty.

F20/F21 používa spoločné `app_errors.py`: stabilné kategórie vstup, disk,
oprávnenia, pamäť, GPU, model, sieť, konflikt a neznáma príčina. Rozhodujú typy
výnimiek, OS/SQLite kódy a kontext operácie; preložené hlásenia sa neparsujú.
Príčiny obalených výnimiek ostávajú dostupné v technických podrobnostiach.
Adresy HTTP, bežné tokeny a heslá sa z nich odstraňujú. Neznáma chyba sa
nezamieňa automaticky za sieť. Potvrdenie prechodu GPU → CPU zostáva zachované.
Fronta ukladá kategóriu oddelene od podrobností; správca modelov a uloženie/
export v editore používajú rovnaký rozbaliteľný dialóg. Stav projektu uloženého
pred zlyhaním exportu zostáva oddelený od chyby exportu.

Dokončený prepis bez textových úsekov má výsledok `no_speech` a počet 0,
uložený v projekte aj vo fronte. Zobrazuje „Reč sa nenašla“ a vysvetlenie:
nejde o dôkaz, že v zdroji objektívne nie je reč. TXT/SRT zostávajú prázdne,
nevkladajú sa do nich diagnostické vety. Prerušenie a chyba dekódovania tento
výsledok nevytvárajú. Staršie projekty sa vyhodnotia pri obnovení; nevytvára
sa falošný originál a používateľské opravy sa nemenia.

Priebeh F19 používa samostatné IPC udalosti fázy a dĺžky nahrávok. Pracovný
proces najprv číta dĺžky kontajnerov cez existujúci PyAV; dekódovanie ich
spresní počtom PCM vzoriek. Neznáma dĺžka neblokuje prepis, ale až do jej
zistenia sa neuvádza percento celej dávky. Vážené percento znamená pokrytie
časovej osi bezpečnými checkpointmi (vrátane preskočeného ticha), nie presnosť
textu ani počet úspešných súborov. Vybavené položky sa uvádzajú osobitne ako
úspešné, chybové a prerušené; chyba nepridáva dokončenie zvuku.

ETA extrapoluje zostávajúcu časovú os podľa aktuálneho tempa ASR. Nezahŕňa
sťahovanie, prípravu ani export a nie je zárukou času dokončenia dávky.
Vzorky sa resetujú pri zmene fázy, súboru alebo dĺžky. Potrebné sú aspoň
tri rastúce vzorky, desať sekúnd a posun 2 % dávky. Po 30 sekundách bez
nového checkpointu je odhad neistý; samotné plynutie času neznižuje množstvo
zostávajúcej práce. Chyba, zastavenie a dokončenie nezobrazujú zavádzajúcu
nulovú ETA. Veľmi dlhý chunk môže preto dočasne zobrazovať neistý odhad.

Predvolený profil je `%LOCALAPPDATA%\LokalnyPrepis`; nastavenia, fronta,
modely a zámky zostávajú kompatibilné. `--profile` vyberie samostatný profil.
Výstupný adresár si volí používateľ. Projekt potrebuje celú zložku s databázou,
exportmi, zálohami/revíziami a pôvodný zvuk. Prenos medzi počítačmi môže
vyžadovať opravu pôvodných ciest; aplikácia ich automaticky neprepisuje.
Modely, projekty, fronta a poverenia sa prenášajú osobitnou súkromnou zálohou,
nie cez GitHub. Profil používajte na jednom počítači naraz, nekopírujte ho
počas zápisu. Pred prvým pullom upratovania zálohujte na druhom počítači
lokálne zmeny aj staršie pracovné priečinky, najmä ak obsahujú vlastné dáta.
V tomto repozitári neboli sledované modely ani používateľské databázy;
ignorované lokálne `work/outputs/cache` sa pullom nemažú.

Chýbajúci Python/Tk: použite plnú CPython inštaláciu a `-Python`.
Chýbajúci pip v nedokončenej `.venv`: spustite jej `python -m ensurepip`,
príčinu chyby prístupu opravte; setup prostredie nemaže. Hash mismatch:
neobchádzajte hash, overte index a schválený lock. Nedostatok disku:
PCM cache dlhého audia používa disk; neuvoľňujte miesto mazaním projektov.
Chýbajúci snapshot offline: obnovte celú cache alebo povoľte stiahnutie
presnej revízie. Zamknutý projekt/profil: zavrite druhú inštanciu.
Existujúce Tcl `ThemeChanged`/`after` hlásenia počas rušenia testovacích okien
sa evidujú; rozhoduje dokončený unittest súhrn, nie absencia výpisu.

## Cyklus medzi počítačmi a súbežné vetvy

Pred prácou vždy skontrolujte lokálne dáta; žiadny slepý pull nad zmenami:

```powershell
git status --short --branch
git remote -v
git fetch --prune origin
git log --oneline --left-right HEAD...origin/main
git merge --ff-only origin/main
.\scripts\setup.ps1 -Mode development
```

Fast-forward robte len v správnej čistej vetve. Rozpracované súvisiace zmeny
uložte vlastným skontrolovaným commitom na pracovnej vetve; nesledované dáta
zálohujte mimo Gitu. Pri divergencii vytvorte zálohu a integrujte vedome cez
merge/PR; nevynucujte reset ani force push. Súbežná práca používa samostatné
vetvy, napríklad `git switch -c codex/nazov-opravy`, a pull request. Konflikt
riešte podľa oboch verzií, ponechajte regresie a zopakujte testy; pri neistote
zachovajte obe práce a nezlučujte do main.

Po práci:

```powershell
.\scripts\test.ps1
git diff --check
git diff
git add -- src/ndtranskripthor/application/konkretny_subor.py tests/konkretny_test.py
git diff --cached
git commit -m "Popis konkretnej opravy"
git fetch origin
git push origin HEAD
```

Nahraďte ukážkové súbory vlastnými konkrétnymi cestami. Pred main pushom pri
zmene zdrojov/balenia vytvorte z kandidátskeho commitu nový klon a nové `.venv`,
spustite setup/testy/build a nové EXE. Pri zlyhaní ponechajte commit lokálne
alebo použite schválený draft PR postup. Kontrolujte výsledok Windows CI;
workflow build sa dá vyžiadať ručne. Release/tag/verzia vyžadujú výslovný
režim RELEASE a zadanú novú verziu.


## Referenčné meranie F26

`src/evaluate_mixed.py` vyžaduje validovaný schema=2 korpus, presný commit
modelu a nový výstupný priečinok. `--device cpu|cuda` je explicitná voľba;
GPU chybu nenahradí CPU meraním. `--validate-only` kontroluje referencie bez
načítania modelu. Nástroj používa produkčný `transcribe_job`, diskové PCM,
checkpointy a efektívne nastavenia backendu v izolovanom procese na nahrávku.
Metodika, význam metrík a zoznam chýbajúcich ukážok sú v
[src/eval/README.md](../src/eval/README.md). Bez oprávneného korpusu neuvádzame
reálne WER, presnosť prechodov ani výkon modelov. Jednotkové testy a technická
skúška Windows počítadiel pamäte nie sú meraním kvality prepisu.


## Reprodukovateľné vstupy a povinné kontroly F27/F28

Použite čistý klon a nové `.venv`; existujúce profily ani modely nemažte.
`setup.ps1` zachová existujúce prostredie, odmietne nesprávny Python a
nainštaluje pip 25.0.1 z `bootstrap.lock` s SHA-256. Aplikačné verzie sa v tejto
úlohe nemenili. Runtime/build/speakers locky pokrývajú deklarovaný reťazec;
`verify_environment.py` porovnáva vstupy, constraints, pin transportu a skutočné
verzie distribúcií vrátane závislostí a umiestnenia v projektovom `.venv`.
Neznáme balíky a odlišné verzie sa neodstraňujú automaticky: pripravte čistý
klon/prostredie. Schválené voliteľné build/speaker balíky sú povolené aj pri
vývojových testoch. GPU variant torch potrebuje samostatne overený lock;
základný build ho nebude potichu považovať za zhodný CPU variant.

Jedinou cestou balenia EXE je `scripts/build.ps1` (`zostavit.cmd` je obal).
Build overí prostredie, spustí úplné testy a až potom PyInstaller, porovnanie
zabalených zdrojov a diagnostiku EXE. Testy vyžadujú minimálne 197 objavených
a dokončených testov bez preskočenia. Integračné testy transportu v tej istej
sade používajú lokálny HTTP server a skutočný Hub stream, obnovu, zámky,
kontrolné súčty, prerušenie a časové limity; nesťahujú veľké modely.
PowerShell regresia úmyselne nechá testovací skript zlyhať a overí, že sa
balenie nespustí. Používa dostupný PowerShell 7 (ako CI), inak Windows
PowerShell s platnou lokálnou politikou; politiku neskúša obísť ani meniť.

Na začiatku build označí manifest ako pending; starší manifest zálohuje pod
`build/previous-build-manifests`. Až po všetkých kontrolách vytvorí
`dist/ND TranskripThor/build-manifest.json`: SHA-256 vstupov a súborov zostavy,
commit, Python, jeho spustiteľný súbor a presné verzie knižníc. `package.py`
overí tento manifest, aktuálne vstupy, prostredie aj súbory pred vytvorením
ZIP; manifest sa pribalí. Neúspešný build, zmena zdrojov či poškodená zostava
blokujú balenie. Po pridaní licencií zostáva kontrola aplikačných súborov
platná; licenčné kópie sa do porovnania runtime stromu nezapočítavajú.
Manifest nie je digitálny podpis ani obrana proti úmyselnej úprave vlastného
manifestu. Je to ochrana pred náhodným zabalením nesprávnej zostavy.

Reprodukovateľnosť tu znamená pevné overiteľné vstupy a zopakovateľný postup,
nie potvrdenú bitovú identitu dvoch EXE/ZIP. PyInstaller, cesty a časové značky
môžu ovplyvniť bajty; bitovú identitu na dvoch počítačoch sme nemerali. Python
inštalujte z oficiálnej Windows distribúcie uvedenej vyššie; manifest meria
použitý interpreter, nenahrádza overenie pôvodu jeho inštalátora.

Závislosti aktualizujte po jednej: upravte príslušný `.in` a constraint,
vyriešte celý reťazec na presnom Pythone, vytvorte nové wheel hash locky,
prejdite diff a urobte čistý setup/test/build. Pri Hugging Face Hub navyše
skontrolujte interné API v `download_worker.py`, vedome upravte HUB_VERSION
a úspešne dokončite všetky transportné regresie. Nesúlad pinu kontrola odmietne.
Nikdy neaktualizujte celý lock naslepo ani nevypínajte TLS/hash kontroly.

## Aplikačné vrstvy (úloha 27)

Jediný zdroj je `src/ndtranskripthor/`. Verejné spúšťače `src/prepis.py`
a `src/evaluate_mixed.py` zostávajú malé a zachovávajú existujúce príkazy.
Autoritatívna verzia zostáva `src/version.py`. Nepridávajte ploché kópie modulov
ani úpravy `sys.modules` na obchádzanie importov.

| Balík | Zodpovednosť a rozhranie |
|---|---|
| `presentation/qml` | Hlavné QML okno, virtuálne Qt modely, editor a dialógy; Python ovládač používa spoločné aplikačné služby. Staršie Tk moduly zostávajú pre regresie. |
| `application` | `transcribe_job`, `BatchRunner`, riadený ASR proces, dátové správy, priebeh a `perform_project_io`. |
| `projects` | `Project`: checkpointy, originál/revízie, transakcie; editácia segmentov, Undo/Redo a vyhľadávanie bez Tk. |
| `queueing` | `StateStore`: samostatné nastavenia a transakčná fronta, kompatibilita starého profilu. |
| `asr` | Existujúce faster-whisper/KInIT adaptéry, efektívne dekódovanie a CZ/SK režim; bez načítania pri importe. |
| `models` | Inventár, integrita, cache a izolovaný prenos s rovnakým pinom Hub. |
| `audio` | Diskové PCM, spoločný formát časovej osi, prehrávač a zariadenia. |
| `exports` | Vykreslenie a konzistentné publikovanie TXT/SRT/VTT/DOCX/JSON, validácia titulkov. |
| `core` | Protokoly hraníc (`EventSink`, `Transcriber`, `ProfileStore`, `Playback`, `ExportProject`), chyby, preklady, zámky a atómové zápisy. |
| `evaluation`, `diagnostics` | Meranie cez produkčné služby a izolované source/frozen diagnostiky. |

Služba `perform_project_io` prijíma zachytené dáta, otvorí vlastné pripojenie
k projektu vo worker vlákne a vracia udalosti `io_committed`, `io_done` alebo
`io_error`. Nečíta Tk premenné ani nemení príznak neuložených úprav; to robí
editor až po prijatí udalosti. Editor už nepozná SQL tabuľky na pridelenie ID
ani zoznam revízií. `Project.export/retry_export` zostávajú kompatibilné fasády
pre staršie volania; formátovanie a publikovanie patrí balíku `exports`.
Tento krok nemení databázové schémy, ID segmentov, ASR protokol, názvy súborov,
modelové revízie ani používateľské profily a nevyžaduje migráciu projektov.

`core/resources.py` odvodí `src/` zo súboru pri zdrojovom spustení a `_MEIPASS`
pri frozen behu. Assety a katalógy zostávajú v `src/assets` a `src/locales`.
Balenie zbiera všetky moduly balíka; `verify_frozen.py` rekurzívne porovnáva
ich skutočný bytecode vrátane inicializátorov. Test katalógov tiež prechádza
vnorené zdroje. Testy zostávajú v `tests/`, balenie v `packaging/` a opakovateľné
nástroje v `scripts/`; tieto už správne oddelené priečinky netreba presúvať.

`tests/test_architecture.py` chráni smer importov: dátové vrstvy nepoužívajú Tk
ani prezentačnú vrstvu, `core` nezávisí od vyšších vrstiev. Overuje aj studený
import služieb bez modelových runtime, Unicode zdrojové/frozen cesty a uloženie,
otvorenie a export projektu cez službu bez prepisu originálu. Regresie sú
simulované testy pipeline, nie nové meranie reálnej presnosti ASR/GPU.

## Overenie offline a diagnostiky (úloha 28)

`application/local_data.py` meria iba metadata súborov, mimo Tk vlákna.
Nenasleduje symlinky/reparse body, obmedzuje počet položiek a čas jedného stromu,
rešpektuje zrušenie a pri neúplnom čítaní vráti explicitný čiastočný stav.
Prehľad nič neodstraňuje. Diagnostický JSON je nový allowlist snapshot;
nekopíruje obsah profilov, logov ani projektov. ZIP sa publikuje atómovo až
po úspešnom dokončení; uložené bajty zodpovedajú náhľadu. Nepribudla závislosť.

Voliteľná praktická skúška z existujúcej cache a oprávnenej nahrávky:

```powershell
.\.venv\Scripts\python.exe scripts/verify_offline.py --cache 'C:\vlastna-cache' --audio 'C:\vlastna-nahravka.wav' --output 'outputs\offline-novy-pokus'
```

Výstup musí byť nový priečinok. Nástroj použije skutočný model (predvolene Tiny),
CPU, uloženú presnú revíziu, produkčné `transcribe_job`, dekódovanie a checkpointy.
Blokuje a počíta Python sieťové pokusy od začiatku testu a každých približne 50 ms
meria Windows IPv4/IPv6 TCP tabuľky vlastného procesu. Výsledok musí mať dokončený
projekt, nulové pokusy/spojenia a úspešné merania. Lokálny výstup obsahuje projekt
s prepisom; nepatrí do Gitu ani do diagnostického ZIP. Samotný offline-report.json
obsahuje iba počty a technické výsledky. Ide o meranie jedného procesu, nie packet
capture; nezachytáva UDP, iné procesy ani spojenie medzi dvomi vzorkami. Tento
nástroj neoveruje úplnú sieťovú izoláciu celého Windows alebo všetkých backendov.

Dňa 28. 10. 2026 prešla lokálna syntetická nahrávka vytvorená Windows SAPI:
Tiny CPU, revízia `d90ca5fe260221311c53c58e660288d3deb8d356`, 2 úseky, 2,578 s,
0 Python sieťových pokusov, 42 TCP vzoriek, maximum 0 spojení, 0 chýb merania.
Nejde o meranie presnosti ani test KInIT/GPU. Automatické regresie samostatne
blokujú sieť pri prehľade/diagnostike a pri chýbajúcom offline modeli; UI testy
používajú izolované profily a obe témy/jazyky pri Tk scaling 100–200 %.

## Informácie o zostave a návody

`src/version.py` rozlišuje zobrazené Pre-release od internej verzie kompatibility.
O aplikácii používa tieto hodnoty a presný podpis z presentation/ui.py; SYNC ich
nezvyšuje. Aktuálne používateľské poznámky sú v [RELEASE-NOTES.md](RELEASE-NOTES.md).
Počet testov uvádzajte vždy s dátumom a commitom; minimum 197 nie je výsledok behu.
Historické audity sa neprepisujú na nový výsledok. Neznámy dátum merania označte
ako neznámy; dátum evidencie dokumentu nie je dátum vykonania jeho testov.

## Historický experiment rozhrania (testing vetva)

Distribučné varianty, licenčný inventár a podpisovací postup sú v
[DISTRIBUTION.md](DISTRIBUTION.md). Predvolený build je extended/QML;
`build.ps1 -Frontend tk -Variant basic` meria historický balík bez PyTorch/KInIT runtime.

Starší `prototype_qml` má vlastný profil, lock a zostavu. Nenahrádza aktuálny
produkčný QML program. Spustenie, merania, bezpečnosť pracovných kópií a rozhodnutie
sú v [QML-EXPERIMENT.md](QML-EXPERIMENT.md). Bežný setup/build od Release v1 vyžaduje Qt podľa runtime locku.

## Vydanie Release v1

Tag `v1.0.0`, zobrazené označenie **Release v1**, číselná verzia **1.0.0**.
Pred publikovaním treba z čistého klonu presného kandidáta pripraviť `.venv`,
spustiť `build.ps1` (úplné regresie aj QML scenáre) a skontrolovať nové EXE.

```powershell
.\scripts\build.ps1 -OutputDirectory dist
.\.venv\Scripts\python.exe scripts/package.py --app 'dist/ND TranskripThor' --output 'outputs/ND-TranskripThor-v1-Windows-x64.zip' --release-tag v1.0.0
.\.venv\Scripts\python.exe scripts/verify_distribution.py 'outputs/ND-TranskripThor-v1-Windows-x64.zip' --startup
```

Balenie odmietne nečistý alebo iný commit než ten v overenom build manifeste.
ZIP obsahuje QML aplikáciu, obe ASR knižnice a licenčný inventár, nie modelové
váhy ani súkromné dáta. Publikuje sa celý ZIP a jeho `.sha256`. Vydanie sa
na GitHube označí ako stabilné a najnovšie až po overení nahratých príloh.
