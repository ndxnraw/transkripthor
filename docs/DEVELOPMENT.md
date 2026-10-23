# Vývoj na Windows a prenos na ďalší počítač

Podporujeme Windows x64 a CPython 3.12 s Tk a pip. Na toto overenie sa používa
samostatný oficiálny Python 3.12.10; pôvodná zostava zaznamenala 3.12.14.
Python 3.12.10 má [oficiálnu Windows distribúciu](https://www.python.org/ftp/python/3.12.10/).
Pri inštalácii povoľte Tcl/Tk a pip. Potrebujete Git, internet na inštaláciu
balíkov/modelov a niekoľko GB voľného miesta. PyAV wheel obsahuje dekódovanie;
samostatný systémový FFmpeg sa pre aplikáciu nevyžaduje
([dokumentácia faster-whisper](https://github.com/SYSTRAN/faster-whisper#requirements)). Natívne runtime
vyžadujú Microsoft Visual C++ Redistributable x64; pri chýbajúcej DLL opravte
jeho inštaláciu zo stránky Microsoftu. Proxy/certifikáty riešte s IT, nikdy
nevypínajte TLS kontrolu. Skripty rešpektujú politiku spúšťania PowerShellu.

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
Python 3.12 a Tk, vytvorí `.venv` len ak chýba a existujúce prostredie nemaže.
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
lokálne zmeny aj starý `outputs/zdroj`, najmä ak ste tam vložili vlastné dáta.
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
git add -- src/konkretny_subor.py tests/konkretny_test.py
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
