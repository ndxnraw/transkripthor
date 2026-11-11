# Stav projektu

Hlavná vývojová a distribučná línia je **Release v1**, verzia **1.0.0**,
Qt Quick/QML, Windows x64. Autoritatívne označenie a Windows metadata sú
v `src/version.py`; príznak Pre-release je vypnutý. Výslovná požiadavka
používateľa na vydanie nahrádza predchádzajúci režim iba SYNC.

[Release v1 a stiahnutie](https://github.com/ndxnraw/TranskripThor/releases/tag/v1).
Tag `v1` má ukazovať na rovnaký overený commit ako `main`. Repozitár zostáva
súkromný; prístup k vydaniu a prílohám vyžaduje prístup k repozitáru.
Pred publikovaním sa vyžaduje úplná regresia bez skipov, produkčné QML
scenáre, nové Windows EXE z čistého klonu presného kandidáta, porovnanie
modulov a zdrojov, rozbalenie ZIPu a štart rozbaleného EXE. Konkrétny
commit, aktuálne počty/výsledky a SHA-256 balíka uvádzajú poznámky GitHub
Release; priložené build/distribution manifesty identifikujú presné vstupy.
Nasledujúce merania sú predchádzajúce dôkazy implementácie, nie náhrada
za overenie presného release commitu.

## Produkčná aplikácia QML (11. 11. 2026)

Na výslovnú požiadavku používateľa nahrádza hlavné rozhranie Qt Quick/QML
cez PySide6-Essentials 6.12.0 a shiboken6 6.12.0. Je to samostatná aplikácia
v `src/ndtranskripthor/presentation/qml`, nie starý experiment `prototype_qml`.
`run.ps1` a predvolený `build.ps1` používajú QML. Historické Tk rozhranie je
zachované pre regresie a explicitné `build.ps1 -Frontend tk`.
V čase implementácie sa zachovala verzia **2.1.3b / Pre-release** bez publikovania;
nasledujúca výslovná požiadavka používateľa ju povýšila na Release v1.

- Hlavná obrazovka nemá karty: pridanie alebo pretiahnutie nahrávok,
  jazyk, kvalita, spustenie. Chýbajúci model pripravuje existujúci ASR
  worker automaticky. Offline režim vyžaduje výslovný súhlas s internetom.
  Doplnkové nástroje sú v ponuke, s návratom na nahrávky alebo do editora.
- Front, poradie, opakovanie/obnovenie, stavy, podrobnosti, priebeh a stop
  používajú existujúcu databázu a izolovaný ASR proces. Podporené zostávajú
  faster-whisper, slovenský KInIT, CPU a CUDA s potvrdením náhrady CPU.
- Editor otvára pôvodný projekt na mieste so zámkom. Zachováva originál,
  revízie, neuložené zmeny a históriu. Ponúka vyhľadávanie Unicode,
  hovoriacich, delenie/spájanie a časy úsekov, titulky, päť exportných
  formátov, prehrávanie/posun/rýchlosť/výstupné zariadenie a lokálne hlasy.
  Ukladanie je na pozadí; neskoršie úpravy zostávajú neuložené.
- Správa modelov, nastavenia, diagnostika s náhľadom pred uložením,
  prevádzkové správy, svetlá/tmavá téma a živé čítanie vysokého kontrastu
  Windows majú QML rozhranie. Pri štarte sa neimportuje Tk.
- Qt závislosti sú presunuté do úplného runtime reťazca s existujúcimi
  SHA-256 Windows wheelov. Príprava čistého prostredia nevyžaduje
  inštaláciu voliteľného prototypu. Zdrojom zostávajú výlučne `src/`.
- Dvadsať produkčných Qt scenárov prešlo bez preskočenia (14,364 s).
  Zahŕňajú skutočné písanie do okna, klávesové uloženie, výber úsekov,
  neuložené zmeny, chybu disku, úpravy počas uloženia, všetky exporty,
  nemenný originál, chýbajúce audio, Unicode a vysoký kontrast.
  Samostatná diagnostika zdrojovej aplikácie overila aj natívne importy
  oboch ASR runtime a skutočný izolovaný proces s očakávanou offline
  chybou chýbajúceho modelu; nejde o inferenciu modelu/GPU.
- Finálny úplný beh **338 regresií prešiel za 401,319 s**, bez preskočení
  a bez nezachytených chýb finalizátorov. Nasledovalo všetkých 20 Qt
  scenárov (14,364 s), tiež bez preskočenia.
- Reálna inferencia: existujúci overený large-v3/faster-whisper na CPU
  prepísal offline vlastnú syntetickú nahrávku za 26,063 s presne na
  „This is a local transcription test. The recording stays on this computer.“
  Výsledok sa otvoril v produkčnom QML ovládači, prehrávanie bolo dostupné,
  úprava sa uložila do pôvodného projektu a originál zostal nemenný.
  Súkromné nahrávky sa nepoužili, váhy sa nesťahovali. Reálna inferencia
  KInIT ani GPU sa tým netestovala; CUDA zariadenie sa nenašlo.
- Vizuálne sa skontroloval naplnený front s vybraným jazykom/kvalitou,
  slovenský editor a jeho nástroje. Pri kontrole Windows výberu súboru
  pomocník nedokázal spoľahlivo zacieliť pole modálneho dialógu; editor
  sa preto vizuálne overil na vlastnej fixture. Otváranie projektov,
  písanie a klávesové uloženie sú pokryté produkčnými Qt scenármi.
- Nová Windows QML zostava **prešla**: všetkých 74 pribalených modulov
  sa zhoduje so zdrojom, QML/preklady/assets sú zhodné, skutočné EXE
  overilo projekt, uloženie, päť exportov, prehrávanie/posun, témy,
  natívne ASR importy a izolovaný proces. Bez QML upozornení a bez
  importu Tk. Manifest zostavy je `verified`, všetky kontroly skončili 0.
  Kandidát: `dist/qt-production-20261111/ND TranskripThor/`.
  Bežná kópia **`dist/ND TranskripThor/ND TranskripThor.exe` už používa QML**.
  Pred výmenou sa celá stará zostava skopírovala a overila pomocou SHA-256;
  pôvodný priečinok je navyše zachovaný v `retired`. Záloha je v lokálnom
  `outputs/previous-standard-before-qml-20261111-133120/`. Následné overenie
  manifestu bežnej kópie prešlo: vstupy, súbory aj prostredie sú zhodné
  s overeným kandidátom. Nahrávky, projekty, profily ani váhy sa nemenili.

## Historický medzikrok Tk: jedna obrazovka (11. 11. 2026)

Medzikrok pred prechodom na QML nad `affb100` menil samotný pracovný postup podľa
spätnej väzby používateľa. Predchádzajúce lokálne úpravy zostali zachované.
Verzia 2.1.3b / Pre-release, ASR backendy, závislosti a projektové formáty
sa nemenia; nevznikol commit, push, tag ani publikované vydanie.

- Hlavné karty Nahrávky/Editor/Modely/Nastavenia/Podrobnosti nahradil
  skutočný zásobník rámcov `ViewStack`, nie iba prefarbenie alebo skrytie
  hlavičky Notebooku. Bežný postup je Pridať nahrávku → jazyk/kvalita →
  Spustiť prepis. Potrebné voľby sú na jednej obrazovke.
- Prázdna plocha má výrazné pridanie súborov a pôvodný COPY-only FileDrop.
  Po pridaní sa zobrazí zoznam a spustenie; ak výber chýbal, označí sa
  prvá nová nahrávka. Technický priebeh sa zobrazí až pri práci.
  Podrobnosti, odobratie a poradie sú príkazy ponuky so zachovanými
  kontrolami dostupnosti. Zdrojové súbory sa odobratím z frontu nemažú.
- Kvalita má stručné názvy, ale používa pôvodné modelové identifikátory.
  Bežný online štart pripraví chýbajúce súbory v existujúcom workerovi
  s priebehom na rovnakej obrazovke. Návšteva správcu modelov nie je
  predpokladom. V režime iba offline zostáva prípadný internet explicitnou
  voľbou; odmietnutie nič nesťahuje a nepresmeruje do modelov.
- Možnosti obsahujú pokročilé nastavenia, modely, diagnostiku, výsledky
  a vzhľad. Doplnkové zobrazenia majú Späť na nahrávky. Návrat z editora
  zachováva text, kurzor, výber, históriu aj neuložený stav bez zápisu
  projektu. Ctrl+Tab nevedie cez modely a nastavenia.
- Vizuálne sa overila úvodná aj naplnená obrazovka a simulovaná príprava
  súborov bez odchodu do modelov v svetlej/tmavej téme. Nešlo o reálne
  sťahovanie váh ani inferenciu ASR/GPU. Prázdna plocha má samostatnú
  EN/SK maticu 100–200 % a čiernej/bielej kontrastnej palety; pôvodná
  matica navyše testuje naplnený front so zobrazeným priebehom.
- Cielených 21 skúšok toku/tém/kontrastu prešlo za 67,419 s. Návrat
  neuloženého editora a úplná matica malých obrazoviek prešli tromi
  skúškami za 96,219 s. Sú to prekrývajúce sa kontroly, nesčítavajú sa
  k celému behu. Finálny výsledok po prechode na QML je uvedený vyššie.

Zistenie k spúšťaniu: bežné `dist/ND TranskripThor/ND TranskripThor.exe`
malo čas zostavenia 10. 11.; novšie fázy boli v samostatných priečinkoch.
Po overení novej zostavy sa aktualizuje aj bežná cesta s lokálnou zálohou.
Lokálny finálny log je `outputs/easy-studio-build.log`; nepatrí do Gitu.

## Oprava uvoľňovania Tk premenných (11. 11. 2026)

Aktuálny pracovný strom nad `affb100` odstraňuje príčinu upozornenia
`Variable.__del__: RuntimeError: main thread is not in main loop` zo záveru
fázy 5. Predchádzajúce lokálne zmeny zostali zachované. Verzia 2.1.3b /
Pre-release, závislosti, ASR backendy a projektové formáty sa nemenia.
Nevznikol commit, push, tag ani vydanie.

- `TkVariables` drží natívne Tk premenné po dobu života konkrétneho okna,
  rámca alebo Comboboxu. Pri jeho zániku vykoná unset a odstráni traces
  vo vlákne rozhrania, potom odpojí premennú od interpretera. Neskoršie
  upratovanie cyklov vo vedľajšom vlákne už nevolá Tcl. Platí to pre
  hlavné okno, editor, správu modelov, lokálne dáta aj exportný dialóg.
- Zaniknuté interpretery ostávajú pripnuté, kým hlavné vlákno neuprace
  staré widgetové cykly a neuvoľní posledné odkazy. Nedochádza k ich
  zániku vo vlákne, ktoré náhodou spustilo zber pamäte. Regresia kontroluje
  aj skutočné uvoľnenie, nie iba odloženie do neobmedzeného registra.
- Pracovníci diagnostiky zachytávajú iba dátové vstupy a front udalostí,
  nie dialóg ani aplikáciu. Triedy a finalizátory tkinter sa neprepisujú,
  globálny zber pamäte sa nevypína a pôvodné hlásenia sa nepotláčajú.
- Šesť nových regresií núti upratovanie v pracovníkovi pri živom aj
  zaniknutom vlastníkovi, overuje UI vlákno pri unset, odstránenie traces,
  opakované zatváranie a uvoľnenie interpreterov aj odmietnutie vytvárania
  premennej mimo UI vlákna. Pri diagnostike a zrušenom zatvorení ostávajú
  text, kurzor, výber a história editora zachované; Späť/Znova funguje
  a pôvodný projekt na disku sa nemení.
- Testovací runner považuje ignorovanú výnimku finalizátora za neúspech
  celého behu a stále ju vypíše pôvodným spôsobom. Samotné unittest OK
  už nemôže zakryť pôvodné upozornenie.
- Cielených 19 skúšok zachovania úprav/exportov/ukladania prešlo za
  24,309 s; finálnych šesť životných regresií za 5,098 s, OK.
  Tieto skúšky sa prekrývajú s celou sadou, nesčítavajú sa k nej.
- **Úplný finálny beh: 330 testov, 421,437 s, OK, bez preskočenia.**
  Prísna kontrola nehlásila žiadnu ignorovanú výnimku; log neobsahuje
  pôvodné upozornenie ani chybu Tk callbacku. Záverečné vyhľadanie hlásení
  Tk/finalizátorov vo finálnom logu: **0**. `git diff --check` prešiel.
- **Aktuálna overená zostava:**
  `dist/tk-lifecycle-20261111-092029/ND TranskripThor/ND TranskripThor.exe`.
  SHA-256 EXE: `f04c0134f41f3fbf8b9c6b5bab5767ef1c8eedc9da8ab470e951ff088e1465d8`.
  Priečinok vrátane manifestu má 15 398 súborov, 1 648 829 586 B.
  Úplný `build.ps1 -OutputDirectory` dokončil audit 67 zhodných aplikačných
  modulov a izolovaný štart Tk/tkdnd/tém/prekladov/ikon/natívnych importov
  a nového procesu. Create aj následné verify manifestu prešli.
  Predchádzajúce zostavy zostali zachované.

Lokálny log úplného overenia: `outputs/tk-lifecycle-build.log`; nepatrí
do Gitu. Postup a vlastníctvo objektov sú opísané v DEVELOPMENT.
Ide o overenie životného cyklu a existujúcich regresií, nie nový test
reálnej inferencie ASR/GPU ani čistej Windows VM.

## ttkbootstrap – prístupnosť a integračné doladenie, fáza 5 (11. 11. 2026)

Aktuálny pracovný strom nad `affb100` dopĺňa záverečné doladenie mierky,
klávesnice a životného cyklu rozhrania. Predchádzajúce lokálne zmeny zostali
zachované. Verzia 2.1.3b / Pre-release, závislosti, faster-whisper, KInIT
a projektové formáty sa nemenili. Nevznikol commit, push, tag ani vydanie.

- Nové kontroly preukázali skrytú voľbu automatického prehrávania pri
  175–200 % na malej obrazovke. Nastavenia teraz používajú posúvateľný
  formulár a pevné spodné akcie. Presun fokusu odhalí celé pole alebo
  pomocnú správu; koliesko zostáva obmedzené na tento formulár a nepreberá
  ovládanie textových polí ani natívnych volieb. Hodnoty a ukladanie
  nastavení zostali pôvodné. Pri zániku sa odpoja väzby formulára na okno.
- Riadky akcií prepočítavajú rozmery po zmene témy a pri zatvorení rušia
  čakajúce prekreslenie. Opakované krátke otvorenie/zatvorenie tak
  nezanecháva neplatné Tcl príkazy. Správy po zániku odregistrujú textové
  pole aj sledovanie hodnoty; register nenarastá pri zatváraní dialógov.
- Vysvetlenia v chybovom okne a nastaveniach prehrávania sa zalamujú
  podľa aktuálnej šírky. Technické podrobnosti ostali zbalené na požiadanie,
  iba na čítanie a posúvateľné. Tab poradie zabalených akcií vynecháva
  zakázané tlačidlá. Kontrastné checkboxy a prepínače majú explicitný
  systémový obrys a veľkosť indikátora odvodenú od mierky.
- Úplný beh odhalil aj staršie nezrušené `App.poll` a odložené uloženie
  nastavení pri zániku hlavného okna. Okno teraz vlastní jediný naplánovaný
  cyklus, priamym obnovením ho nahradí a pri zániku zruší. Pri okamžitom
  uložení aj zániku ruší tiež časovač nastavení. Pôvodné bezpečné ukončenie
  ASR a ochrana neuložených úprav zostávajú zachované. Finálny beh sa dokončil z opravených
  nemenných zdrojov; medzikandidáty nie sú overenou distribúciou.
- Osem nových regresií zahŕňa všetky pracovné karty, EN/SK,
  Tk scaling 100/125/150/175/200 %, svetlú/tmavú a čiernu/bielu kontrastnú
  paletu, zúžený dialóg, zatváranie, prepočet riadkov, Tab a odhalenie
  obsahu klávesnicou. Pôvodné testy neuložených úprav, histórie, exportov,
  prehrávania, DnD a procesov zostali zachované.
- Vizuálne sa overili Nastavenia pri 200 %, posúvanie celého formulára,
  čitateľné checkboxy v čiernom kontraste, návrat do tmavej a svetlej témy
  a úzky chybový dialóg so zbalenými aj rozbalenými podrobnosťami.
- **Úplný finálny beh: 324 testov, 403,867 s, OK, bez preskočenia.**
  Zahŕňa osem nových regresií. Samostatných 13 skúšok životného cyklu
  a ukladania prešlo za 14,454 s; ide o prekrývajúce sa kontroly,
  nesčítavajú sa k 324. `git diff --check` prešiel.
- **Aktuálna overená zostava:**
  `dist/acceptance-phase5-verified-20261111-082430/ND TranskripThor/ND TranskripThor.exe`.
  SHA-256 EXE: `495e35c83b6927bdf0155a20bfd0910ce4a3b47587e5b183573ab90ccbd5e6c2`.
  Priečinok vrátane manifestu má 15 398 súborov, 1 648 826 588 B.
  Úplný `build.ps1 -OutputDirectory` dokončil audit 66 zhodných aplikačných
  modulov a izolovaný štart Tk/tkdnd/tém/prekladov/ikon/natívnych importov
  a nového procesu. Create aj následné verify manifestu prešli.
  Predchádzajúce zostavy zostali zachované.

Pri hromadnom UI teste lokálnych dát log obsahuje ignorované výnimky
`Variable.__del__: RuntimeError: main thread is not in main loop` pri
uvoľňovaní Tk premenných vo vedľajšom vlákne. Úplný beh sa dokončil s OK,
ale nejde o úplne čistý výstup diagnostiky. Ide o historický výsledok
zostavy fázy 5; uvedené upozornenie odstraňuje oprava opísaná vyššie.
Samostatná finálna vizuálna ukážka sa ukončila bez týchto hlásení.

Nastavenia Windows sa nemenili. Mierky a kontrastné palety sú simulované
v skutočnom Tk; nejde o fyzické prepnutie systémového DPI/kontrastu,
certifikáciu čítačky obrazovky, nový test inferencie ASR/GPU ani čistú VM.
Lokálny finálny log: `outputs/ttkbootstrap-phase5-verified-build.log`;
nepatrí do Gitu. Opakovateľný postup a hranice sú v DEVELOPMENT.

## ttkbootstrap – editor a dialógy, fáza 4 (11. 11. 2026)

Aktuálny pracovný strom nad `affb100` zjednocuje editor prepisu a dialógy
so spoločným vzhľadom ttkbootstrapu. Predchádzajúce lokálne zmeny zostali
zachované. Verzia 2.1.3b / Pre-release, závislosti, faster-whisper, KInIT
a projektové formáty sa nemenili. Nevznikol commit, push, tag ani vydanie.

- Editor má spoločné kartové povrchy, prehľadnú hlavičku so zdrojom
  a stavom uloženia, vyhľadávanie, zvýraznenú akciu Uložiť a zjednotené
  ovládanie prehrávania, exportu a podrobností. Existujúce príkazy,
  klávesové skratky, stránkovanie a úpravy blokov zostávajú zachované.
- Spoločný `DialogPanel` usporadúva nastavenia prehrávania, export,
  lokálne dáta a chybové hlásenia. Správa modelov používa rovnakú
  hierarchiu hlavičky a akcií. Technické podrobnosti chyby sú spočiatku
  zbalené a iba na čítanie. Natívne výbery súborov a existujúce
  potvrdzovacie dialógy zostávajú zachované.
- Každý editor sleduje zmenu vzhľadu samostatne; menia sa aj farby
  vyhľadávania bez nového vykreslenia, zachytávania alebo uloženia textu.
  Regresie kontrolujú totožnosť textového poľa, neuložený obsah, kurzor,
  výber, posun, históriu aj následné Späť/Znova. Projekt na disku zostáva
  nezmenený. Rozpracované voľby dialógov a diagnostický náhľad prežijú
  prepnutie svetlej/tmavej témy aj čiernej/bielej kontrastnej palety.
- Zánik editora odregistruje sledovanie. Odložené farbenie titulkov
  spravuje koreň okna a ruší ho pri ukončení; rýchle zatvorenie dialógu
  nezanechá neplatný Tcl príkaz. Klasické Tk vstupy a tlačidlá dostávajú
  paletu bez aplikovania ich volieb na ttk prvky.
- Vizuálna kontrola odhalila blokovanie otvorenia dialógu pri vnorenom
  spracovaní nečinných udalostí. `DialogPanel.fit()` teraz iba ohraničí
  maximálnu veľkosť podľa obrazovky a nechá vykreslenie na hlavný cyklus.
  Nová regresia otvorenia prehrávania z udalosti a vizuálna kontrola
  potvrdili vykreslenie aj odozvu dialógu vo vysokom kontraste.
- **Úplný beh: 316 testov, 321,477 s, OK, bez preskočenia.** Zahŕňa päť
  nových regresií zachovania stavu editora a dialógov. Cielené behy sa
  s touto sadou prekrývajú a nesčítavajú sa k 316. Vizuálne sa overil
  svetlý/tmavý editor, simulovaná čierna kontrastná paleta, nastavenia
  prehrávania a zbalené/rozbalené podrobnosti chyby.
- **Aktuálna overená zostava:**
  `dist/editor-phase4-20261111-072543/ND TranskripThor/ND TranskripThor.exe`.
  SHA-256 EXE: `cd517a7bd871be52e012808258f6585c3358b4d8bee494e7a62b702ce5260ccb`.
  Priečinok vrátane manifestu má 15 398 súborov, 1 648 823 456 B.
  Úplný `build.ps1 -OutputDirectory` dokončil audit 66 zhodných aplikačných
  modulov a izolovaný štart Tk/tkdnd/tém/prekladov/ikon/natívnych importov
  a nového procesu. Create aj následné verify manifestu prešli.
  Predchádzajúce zostavy zostali zachované.

Dôkazy patria tejto zostave a aktuálnym zdrojom. Nastavenia Windows sa
nemenili; vysoký kontrast a DPI neboli fyzicky prepnuté v systéme.
Nejde o nový test reálnej inferencie ASR/GPU ani čistej Windows VM.
Lokálny úplný log: `outputs/ttkbootstrap-phase4-build.log`; nepatrí do Gitu.
Opis a hranice overenia sú v DEVELOPMENT.

## ttkbootstrap – hlavné pracovné okno, fáza 3 (11. 11. 2026)

Aktuálny pracovný strom nad `affb100` modernizuje hlavnú kartu Nahrávky
na základe spoločných tém z fázy 2. Predchádzajúce lokálne zmeny zostali
zachované. Verzia 2.1.3b / Pre-release, závislosti, oba ASR backendy,
projektové formáty a existujúca distribúcia sa v tejto fáze nemenili.
Nevznikol commit, push, tag ani nové publikované vydanie.

- Okno oddeľuje front nahrávok, kartu Spracovanie a spodný panel akcií.
  Hlavička, sekundárne tlačidlá, názvy sekcií, počet súborov a prázdny stav
  používajú spoločnú vizuálnu hierarchiu. Riadky frontu majú väčšiu výšku;
  stavy naďalej obsahujú text aj symbol a zachovávajú stabilné ID položiek.
- Spustiť prepis je jediná vyplnená hlavná akcia. Je dostupná pri čakajúcich
  položkách a neprázdnej výstupnej ceste mimo práce. Pokračovanie/opakovanie
  vybranej položky zostáva samostatné a dostupné aj bez čakajúcich položiek.
  Označenie Odobrať z fronty výslovne odlišuje odobratie položky od zmazania
  súboru; regresia overila, že pôvodný súbor zostal na disku.
- Ukazovatele nahrávky a dávky sú vedľa seba a zostali nezávislé. Nový
  textový štítok preberá fázu workera; Dávka ukončená nevyhlasuje všetky
  položky za úspešné. Technický stav zariadenia je v Podrobnostiach
  spracovania. ETA, počty chýb a prerušenia ostávajú v pôvodnom súhrne.
- Zachované sú dvojklik/Enter, viacnásobný výber, poradie, pôvodná ponuka
  ďalších možností, editor, otvorenie projektov/výsledkov aj FileDrop.
  MessageView má spoločné povrchy bg/card, ktoré sa zachovávajú pri zmene
  témy. Pribudlo päť zhodných kľúčov v EN/SK katalógoch.
- Cielené testy odhalili nedostatok výšky pri 200 %; kompaktný dvojstĺpcový
  priebeh, rezervácia miesta pre ovládanie a presun technického stavu ho
  odstránili. Celá DPI matica oboch jazykov/tém a 100–200 % následne prešla.
  Vizuálne boli skontrolované prázdne aj naplnené okno, oba režimy a
  simulovaná čierna vysokokontrastná paleta. Nastavenia Windows sa nemenili.
- **Posledný úplný beh: 311 testov, 301,196 s, OK, bez preskočenia.**
  Zahŕňa štyri nové regresie pracovného okna. Samostatné cielené behy
  (24 testov; 6 testov s DPI; 4 finálne testy pracovného okna) sa s touto
  sadou prekrývajú, nesčítavajú sa k 311. `git diff --check` prešiel.
- **Aktuálna overená zostava:**
  `dist/workspace-phase3-20261111-064433/ND TranskripThor/ND TranskripThor.exe`.
  SHA-256 EXE: `3574d2b293829cd0afa965b0e9def6504c05f766afde722acd5216f7654d202a`.
  Priečinok vrátane manifestu má 15 398 súborov, 1 648 820 319 B.
  Úplný `build.ps1 -OutputDirectory` dokončil audit 66 zhodných aplikačných
  modulov a izolovaný štart Tk/tkdnd/tém/prekladov/ikon/natívnych importov
  a nového procesu. Create aj následné verify manifestu prešli.

Dôkazy patria tejto zostave a aktuálnym zdrojom. Nejde o nový test inferencie
ASR/GPU, fyzického systémového DPI ani zapnutia Windows vysokého kontrastu.
Lokálny úplný log: `outputs/ttkbootstrap-phase3-build.log`; nepatrí do Gitu.
Opis ovládania a opakovateľný postup sú v DEVELOPMENT.

## ttkbootstrap – spoločná správa vzhľadu, fáza 2 (10. 11. 2026)

Aktuálny pracovný strom nad `affb100` používa v hlavnej Tk aplikácii
`presentation/theme.py` / `ThemeManager`. Zostáva Windows x64, CPython
3.12.10, Tk 8.6.15 a interná verzia 2.1.3b / Pre-release. Predchádzajúce
lokálne úpravy vrátane fázy 1 zostali zachované; nevznikol commit ani push.

- Témy `thor-light`/`thor-dark` vytvára ttkbootstrap 2.2.7 zo spoločných
  paliet. Existujúce štýly a uložené hodnoty `light`/`dark` zostávajú
  kompatibilné; globálne Tk/ttk widget API sa neprepisuje. Hlavná aplikácia
  už nepoužíva vlastné obrázkové pozadia `rounded_styles`.
- Windows vysoký kontrast má prednosť: číta sa SPI_GETHIGHCONTRAST a
  GetSysColor, používa sa natívny clam bez Bootstrap obrázkov a systémové
  farby vrátane výberu, zakázaných, aktívnych a neaktívnych stavov.
  Nastavenia Windows sa nemenia. Kontrola beží pri mapovaní/fokuse a každú
  sekundu; po vypnutí kontrastu sa obnoví zvolený režim. Systémová zmena
  neprepisuje uloženú voľbu svetlej/tmavej témy.
- Spoločné farbenie pokrýva editor, menu, Canvas, stavové správy, správu
  modelov, lokálnych dát a nové/otvorené Tk dialógy. Tcl Combobox popdown
  dostáva rovnaké farby. Pri zániku koreňa sa uvoľnia singleton štýlov,
  fonty a systémový kontrolný timer.
- Vizuálna kontrola odhalila, že Bootstrap theme walk menil odsadenia
  Tk Text polí a orezával správy: regresia pred opravou namerala 27 px
  dostupnej výšky oproti 37 px požadovanej. Správca teraz zachováva pôvodné
  odsadenia a okraje. Celé riadky sú overené novou regresiou a vizuálne
  v svetlom aj tmavom rozhraní.
- ttkbootstrap pribudol do runtime.in/constraints/runtime.lock. Čistý
  Windows resolver a generátor lockov zachovali všetky ostatné verzie
  a wheel hashe. Kontrola 46 nainštalovaných distribúcií a pip check prešli.
  Balenie zahŕňa témy, zdroje a metadata knižnice; startup kontroluje oba
  režimy. Audit hlavnej aplikácie vynecháva samostatnú vzorku fázy 1.
- **Posledný úplný beh: 307 testov, 297,888 s, OK, bez preskočenia.**
  Samostatných 14 cielených UI skúšok prešlo za 24,879 s; ide o prekrývajúce
  sa kontroly, nie prírastok k 307. Testy pokrývajú aj čiernu/bielu systémovú
  paletu, otvorené aj nové dialógy, zachovanie textu/kurzora/výberu a návrat
  k uloženej téme. Windows vysoký kontrast nebol fyzicky zapnutý; simulovaná
  čierna paleta bola navyše vizuálne skontrolovaná vrátane checkboxu.
- **Aktuálne EXE:**
  `dist/theme-phase2-reviewed-20261110-151224/ND TranskripThor/ND TranskripThor.exe`.
  SHA-256: `4d7ece0a72ddfeb05877089e1a40e699dba23a825d8f095b6c9b4a9ebd3382e1`.
  Priečinok má 15 398 súborov, 1 648 819 075 B vrátane manifestu.
  Audit zhodných 66 aplikačných modulov, izolovaný štart Tk/tkdnd/tém/
  prekladov/ikon/natívnych importov a nového procesu aj create/verify
  manifestu prešli. Predchádzajúca distribúcia sa neprepisovala.

Výsledky patria finálnemu pracovnému stromu, nie starším medzikandidátom
v `dist/theme-phase2-*`. Reálna inferencia ASR/GPU ani čistá Windows VM
neboli súčasťou tejto UI úpravy. faster-whisper, KInIT a projektové formáty
sa nemenili. Úplný lokálny záznam je
`outputs/ttkbootstrap-phase2-reviewed-build.log`; nepatrí do Gitu.
Postup a hranice overenia sú v DEVELOPMENT.

## ttkbootstrap – kompatibilitná vzorka, fáza 1 (10. 11. 2026)

V pracovnom strome nad `affb100` vznikla samostatná vzorka
`src/prototype_ttkbootstrap/main.py`. Bežný vstup aplikácie, oba ASR backendy,
projektové formáty a verzia 2.1.3b / Pre-release zostávajú zachované.
Pôvodná lokálna úprava tohto dokumentu zostala zachovaná; nevznikol commit,
push, tag ani nové vydanie.

- Overený runtime: projektová `.venv`, CPython 3.12.10 x64, Tk 8.6.15,
  ttkbootstrap **2.2.7**, Pillow **12.3.0**, tkdnd **2.9.4**.
  Doplnkový lock obsahuje celý deklarovaný reťazec a SHA-256 wheelov z
  čistého Windows resolver reportu. Kontrola prostredia aj `pip check` prešli.
- Vzorka má päť pracovných kariet, pridávanie súborov, skutočný COPY-only
  FileDrop, Treeview, textový editor, Combobox, prepínač, progressbar a
  vedľajšie okno. Prepisovanie je výslovne nedostupné. Dáta zostávajú iba
  v pamäti a dočasnej diagnostike; používateľské profily/modely neotvára.
- Zistené a opravené: zánik TkinterDnD koreňa neuvoľňoval singleton štýlov
  ttkbootstrapu. Vzorka zrkadlí cleanup `ttk.App.destroy()` verzie 2.2.7.
  Ďalší test odhalil skrytie spodných ovládačov pri veľkom písme; rozloženie
  im teraz rezervuje miesto pred rozťahujúcim sa zoznamom.
- Finálny úplný `scripts/test.ps1`: **302 testov, 323,684 s, OK, bez
  preskočenia**. Doplnková sada: **3 testy, 7,489 s, OK, bez preskočenia**.
  Kontroluje EN/SK, tri životné cykly koreňa, témy, Tk scaling 100–200 %,
  zachovanie textu/výberu/nastavení, fokus, Unicode cesty, duplicity a busy
  odmietnutie dropu; tiež izoláciu widget API a konflikt doplnkového locku.
- Nové samostatné EXE je v
  `dist/ttkbootstrap-20261110-143309/ND TranskripThor ttkbootstrap Preview/`.
  Celý priečinok má **1 106 súborov, 77 884 597 B**. SHA-256 EXE:
  `6dd306a0cd150d3f22181c9e90788438262db699498232a16bb38b5d79031933`.
  Stabilná distribúcia sa neprepisovala. Windows metadata sú z `src/version.py`.
- Overenie skutočne skopírovaného EXE v Unicode ceste s medzerami a bez
  Pythonu v PATH prešlo, vrátane tkdnd, tém a troch životných cyklov.
  Audit PYZ potvrdil neprítomnosť torch/transformers/faster_whisper/
  ctranslate2 a aplikačného ASR. Pôvodný nadbytočný freezer po zistení
  nepriamych importov bol zastavený; výsledkom je nová oddelená zostava
  s explicitnými výnimkami iba pre vzorku, nie zmena stabilného balenia.
- Vizuálne skontrolované svetlé/tmavé zdrojové okno a spustené finálne EXE.
  Vysoký kontrast je zatiaľ iba detegovaný; nebol aktívny. Natívna titulná
  lišta bola pri vizuálnej skúške svetlá aj pri tmavom obsahu; doladenie
  jej vzhľadu zostáva otvorené pre ďalšiu fázu.

Rozsah dôkazov: doručenie Tcl zoznamu do skutočného drop handlera nie je
fyzické ťahanie z Prieskumníka; Tk scaling nie je zmena systémového DPI ani
presun medzi monitormi. Tieto ručné skúšky, systémový vysoký kontrast a
reálna inferencia ASR/GPU tu nie sú potvrdené. Prvá fáza poskytuje funkčnú
vzorku a overené základné spolužitie knižníc, nie dokončenú migráciu aplikácie.
Postup opakovania je v DEVELOPMENT. Lokálne logy sú
`outputs/ttkbootstrap-build-final.log`, `outputs/ttkbootstrap-package-final.log`
a `outputs/ttkbootstrap-exe-final.log`; nepatria do Gitu.

## Synchronizácia a nové EXE (10. 11. 2026)

Na výslovný pokyn autora sa lokálna `main` posunula fast-forward na
`33bf71319bcf45dd6916ada6fadf525f9fcdfd01`, zhodne s `origin/main`.
Rozpracovaný obsah tohto dokumentu zostal zachovaný a index zostal prázdny.
Pred zmenou vznikla lokálna záloha mimo repozitára: história Gitu,
samostatné staged/unstaged patche a pôvodný súbor STATUS. Používateľské
nahrávky, profily, projekty a modely sa nemenili ani nemažú.

Nové extended/Tk EXE vzniklo v čistom klone presného existujúceho tagu
`pre-release-1` / `abf0ae8c73ccd7af71e458d4a59c3ce16a04e439`; jeho Git strom
bol v čase zostavenia zhodný s main `33bf713`. Nová `.venv` vznikla cez `setup.ps1`
z uzamknutých Windows závislostí. Úplný `build.ps1` dokončil **302 testov,
286,494 s, OK, bez preskočenia**, audit 65 pribalených aplikačných modulov,
štart Tk/tkdnd/prekladov/ikon/natívnych importov a nového procesu.
Manifest zostavy bol vytvorený úspešne; čistý klon nemal zmeny zdrojov.

ZIP prešiel kontrolou všetkých súborov, SHA-256 a štartom skutočne rozbaleného
EXE z dočasného Unicode priečinka s PATH bez Pythonu. Nie je to nová skúška
na čistej Windows VM ani inferencia KInIT/GPU. Predchádzajúce obmedzenia
ACCEPTANCE.md a nepodpísané EXE zostávajú platné.

- ZIP: `ND-TranskripThor-pre-release-1-Windows-x64.zip`, 438 054 385 B.
- Rozbalený obsah: 1 651 406 490 B.
- SHA-256 ZIP: `0dd13879ec70a691a59e76d3aef4fb0df741c88bbc1b3f0259a318e1cf4822ac`.
- Lokálne `dist/ND TranskripThor` bolo nahradené rovnakou novou zostavou;
  po kopírovaní znovu prešlo manifestom, auditom zdrojov a štartom EXE.
  Stará zostava je zálohovaná mimo repozitára a zachovaná aj v lokálnom
  `dist/ND TranskripThor-before-20261110`.
- Pôvodný ZIP aj checksum z GitHubu sú zálohované a hashovo overené.
  Prílohy existujúceho Pre-release 1 boli úspešne nahradené. Obe nové prílohy
  sa po nahratí znovu stiahli a ich veľkosti/SHA-256 sa zhodovali s lokálnymi.
  Finálny read-back GitHubu potvrdil presne ZIP a checksum, bez dočasných
  príloh: ZIP asset `730705286`, checksum asset `730715434`, release
  `435155379`. Názov, text, tag a príznak pre-release zostali zachované.
  https://github.com/ndxnraw/TranskripThor/releases/tag/pre-release-1

Verzia, existujúci tag a aplikačné zdroje sa nemenili. Nevzniká nový release.
Lokálne dôkazy sú v `outputs/sync-pre-release-1-*.log`; nepatria do Gitu.

## Kontrola pred synchronizáciou (10. 11. 2026)

- Overený remote: `https://github.com/ndxnraw/TranskripThor.git`.
  Pracovná vetva `codex/final-acceptance` aj jej vzdialený náprotivok sú
  `abf0ae8`; GitHub `main` je `33bf713`. HEAD, tag `pre-release-1` a
  `origin/main` majú identický Git strom `2e7818d84b817c153c54c3937b5c7791ec2f793d`.
  Dva dodatočné merge commity teda nemenia obsah. Lokálna vetva `main`
  zostáva na `fb69872`, deväť commitov za vzdialenou; pri kontrole sa neprepínala.
- GitHub Windows regression pre `33bf713` úspešne skončil 6. 11. 2026:
  https://github.com/ndxnraw/TranskripThor/actions/runs/42168704265.
  Regresná úloha prešla; voliteľná build úloha bola preskočená podľa workflow.
  Tento CI beh preto sám osebe nie je dôkaz nového EXE.
- Release `pre-release-1` existuje ako publikované pre-release s Windows ZIP
  (438 055 221 B) a súborom SHA-256. Tag smeruje na `abf0ae8`.
  Overené boli metadáta GitHubu; publikovaný ZIP sa pri tejto kontrole
  nesťahoval ani znovu nespúšťal.
- Lokálne `dist/ND TranskripThor` nie je synchronizované so zdrojmi.
  Manifest uvádza základ `fb69872`; `verify_frozen.py` skončil chybou
  `Frozen code differs: speech_models.py`. Rozdiely vstupov zahŕňajú aj
  preklady, balenie, skripty a testy. Tento priečinok nemožno považovať za
  aktuálnu zostavu Pre-release 1; vyžaduje nový overený build.
- Závislosti: kontrola uzamknutého prostredia potvrdila 45 distribúcií,
  `pip check` nenašiel porušené požiadavky; Python 3.12.10 x64, Tk 8.6.15.
  Verzia a Windows metadata sa naďalej odvodzujú zo `src/version.py`;
  balenie zahŕňa `src/assets` a `src/locales`.
- Aktuálny úplný beh `scripts/test.ps1` nad `abf0ae8`: **302 objavených
  a vykonaných testov, 338,039 s, OK, bez preskočenia**, návratový kód 0.
  Prvý obmedzený beh síce dokončil 302 testov, ale zlyhal pri prístupe
  k dočasným priečinkom Windows (WinError 5); nepočíta sa za úspech.
  Uvedený úspech patrí samostatnému opakovaniu s povoleným prístupom.
  Lokálny log: `outputs/sync-check-2026-11-10-tests-unrestricted.log`.
  Ide o regresnú sadu, nie nové meranie skutočného ASR/GPU alebo čistý build.
- Pred kontrolou bola jedinou lokálnou zmenou staršia unstaged poznámka
  k F24 v tomto dokumente. Zostala zachovaná, index zostal bez zmien.
  `docs/RELEASE-NOTES.md` je výslovne datovaný historický prehľad z 28. 10.;
  aktuálne vydanie opisujú README, GitHub Release a tento záznam.

Kontrola nemení aplikačný kód, verziu, vetvu, tag ani publikované balíky.
Nový build a reálna inferencia modelov/GPU neboli súčasťou tejto kontroly.

## Ako čítať výsledky

Nasledujúce záznamy sú chronologická história, nie súčet testov ani potvrdenie
aktuálneho HEAD. Staršie bloky bez presného dátumu patria vývojovej línii
2.1.3b; ich chýbajúci dátum merania spätne nedopĺňame. Nové merania uvádzajú
dátum a commit. Minimum 197 je kontrolná hranica, nie aktuálny počet testov.
Súhrn používateľského stavu: [RELEASE-NOTES.md](RELEASE-NOTES.md).

## Zachované opravy

Pracovný strom obsahoval F01–F15, lokalizáciu EN/SK, prístupnosť a dizajn:
ochrana aktívnej editácie pri hlasoch, DPI rozloženie, bezpečná príprava,
nemenný originál/revízie a migrácia so zálohou, samostatný projekt/export,
vlastníctvo profilu/projektov/modelov, titulkový profil a validácia, Undo,
ukladanie mimo UI, diskové PCM, procesové ASR a presná revízia/dekódovanie.
Historické záznamy `OPRAVA-F*.md` opisujú priebeh, nie výsledok tohto buildu.
Audit `ANALYZA-FINALNEJ-VERZIE.md` predchádzal týmto opravám; jeho pôvodné
zistenia F01–F15 nie sú automaticky dnešnými chybami.

## Upratanie a lokálne dáta

Zdroje sa presunuli z `outputs/zdroj` do `src`; všetkých 196 regresií a ich
pomocníci do `tests`. Ikony/preklady zostali pri zdrojoch. Spec/manifest
a verzovací template sú v `packaging`; záznam verzií starého buildu je
`BUILD-BASELINE.txt`. Neuzamknuté requirements a duplicitný version_info
nahradili kontrolované locky a generovanie z jedného modulu. Zdrojová cache
`__pycache__` bola odstránená ako obnoviteľný výstup.

Použiteľné testovacie, procesové, balíčkové a benchmark postupy z `work/`
sú udržiavané v `scripts/`, s parametrami a cestami odvodenými od projektu.
Historické opravy a audity zostávajú v docs; nepridáva sa archív do zdrojov.

Po zálohe sa odstránili štyri výhradne generované PyInstaller cache
`work/build`, `build151`, `build152test`, `build200` (TOC/PYZ/PKG a kópie EXE).
Použiteľné distribúcie ani dáta neobsahovali. Šesť nahradených pracovných
skriptov `run_f08_tests`, `benchmark_f10`, `benchmark_f11`, `verify_f12_build`,
`check_f12_frozen`, `package_release` má náhrady v scripts a originály v zálohe.
Novšie F12/vydané zostavy a všetky dáta/modely zostávajú lokálne.

`work/`, `outputs/`, `cache/`, `.venv/`, `build/`, `dist/` sú mimo Gitu.
Obsahujú aj zvuk, modely, profily, projekty a staršie použiteľné zostavy;
tieto dáta sa fyzicky nemažú. Staré experimentálne kópie, balíky a release
adresáre zostávajú na lokálne preverenie, kým nie je potvrdená ich náhrada.
Záloha pred upratovaním je mimo repozitára a obsahuje históriu, pôvodný HEAD,
staged/unstaged patche, zdroje, docs a všetky pracovné Python skripty.

## Overenie a otvorené veci

Pôvodný beh z koreňa: **196 testov, 12 zlyhaní**, všetky pri importe zdrojov
v podprocesoch bez PYTHONPATH. Nový spúšťač a explicitné cesty podprocesov
odstraňujú závislosť od pôvodného pracovného adresára, bez zníženia pokrytia.
Po oprave ciest a ohraničenom čakaní na natívny fokus/uvoľnenie Windows zámku:
**196 testov, OK, 175,564 s, bez preskočených testov**, CPython 3.12.10
z nezávislej oficiálnej distribúcie. Predbežný beh v pôvodnom runtime skončil
natívnou chybou Tk bez súhrnu a nepočíta sa za úspech. Prvý nezávislý beh
ukázal obe testovacie preteky; pôvodné kontroly sa neodstránili ani nezoslabili.

Nový lokálny Windows EXE bol zostavený; kontrola 33 pribalených aplikačných
modulov zodpovedala zdrojom a model-free štart s Tk/tkdnd, ikonami, prekladmi,
natívnymi importmi a skutočne novým procesom prešiel. Starší `download_progress`
sa nepoužíva v runtime; jeho kompatibilný helper aj regresie zostávajú zachované.
Úplný build z presného kandidátskeho commitu sa musí pred pushom zopakovať
v čistom klone s novým prostredím, bez work/cache/PYTHONPATH pôvodného projektu.

Windows CI spúšťa povinnú celú sadu bez modelov/GPU; ručné spustenie umožňuje
aj build s kontrolou EXE. CI má iba contents:read a nenahráva používateľské dáta.
Výsledky vzdialeného CI sa overujú až po pushi; lokálny úspech ich nenahrádza.

Prvé Windows CI pre commit `f5377db` dokončilo 196 testov s jediným zlyhaním:
pri 200 % mierke sa v editore orezalo tlačidlo Pause (šírka 179, požadovaná
203 bodov). Rozdielne rozmery/fontové metriky runnera odhalili pevný riadok
prehrávania. Tlačidlo podrobností je teraz v hlavičke editora, takže neuberá
miesto prehrávaniu ani nepridáva ďalší riadok na nízkej obrazovke. DPI matica zahŕňa aj 1280 × 768; ďalší
regresný test simuluje širšie tlačidlá a overuje ich celé rozmery/dostupnosť.
Pôvodné kontroly a všetkých 196 testov zostávajú povinné (spolu 197). Oprava nemení prehrávanie,
ASR, projektové dáta ani verziu. Nový kandidát vyžaduje nové čisté overenie.

Nasledujúce CI odhalilo aj orezanie Redo a širších prehrávacích tlačidiel.
Editor preto používa šírku tlačidiel podľa textu namiesto pevného minima
a zalamovací riadok prehrávania; pri dostatku miesta sa posuvník rozťahuje.
Kompaktnejšie okraje tlačidiel a pole hlasu zamedzujú zbytočnému druhému
riadku pri 200 % mierke. Matica pokrýva aj 1024 × 768.
Regresia širších tlačidiel simuluje aj udalosť zmeny rozmerov kontajnera.
Žiadna pôvodná kontrola rozmerov sa nevypína.
Celá cielená DPI matica vrátane pôvodného StudioScaling testu prešla:
3 testy, 68,987 s, bez preskočenia. Predchádzajúci čistý kandidát `824b5c4`
prešiel všetkými 197 testmi (175,402 s), buildom, štartom nového EXE,
reálnym Tiny CPU v dvoch procesových behoch a reálnym UI stop/restart/resume.
Táto následná úprava rozloženia vyžaduje rovnaké overenie pred pushom;
presný commit, logy, SHA-256 EXE a výsledok CI sa uchovávajú v lokálnom
bode obnovy mimo Gitu. Stav vzdialených kontrol je dostupný v GitHub Actions.

Reálne CUDA a plná KInIT inferencia, presnosť na oprávnenom CZ/SK korpuse,
všetky fyzické systémové DPI/prepínanie monitorov, Explorer OLE drop
a manuálny screen reader vyžadujú osobitné overenie. Automatické Tk/mock
testy ich nenahrádzajú. GPU lock zatiaľ nie je overený. Historický audit
F18–F21 zostáva podkladom na cielený funkčný audit (dostupnosť voliteľných hlasov, váženie postupu/ETA,
klasifikácia chýb a ticho). Upratanie nesľubuje opravu týchto tém.

## F16/F17 – integrita a inventár (15. 10. 2026)

Potvrdené v aktuálnom kóde pred opravou: štrukturálne úplná cache bez
potvrdenia sa zobrazovala rovnako ako overená a návrat na existujúcu kartu
Modely neobnovoval inventár. Tieto dve zistenia sú opravené.

- Inventár rozlišuje chýbajúci, neúplný/zmenený, nájdený/neoverený a overený
  model. Rýchla kontrola používa manifest, veľkosti a časy zmien; nehashuje
  váhy pri štarte ani pri každom návrate na kartu. Stará úplná cache zostáva
  použiteľná, bez falošného tvrdenia o overenej integrite.
- Explicitné overenie je mimo UI, používa existujúci mechanizmus cache
  a presný snapshot. Online kontroluje voči Hub metadátam bez sťahovania
  váh; offline voči uloženým kontrolným súčtom. Bez dôveryhodných súčtov
  vysvetlí potrebu online kontroly. Súbory sa pri tejto kontrole nemažú ani
  nepresúvajú. Zastavenie alebo nesúlad nezanechá platné potvrdenie.
- Zmena súboru počas hashovania sa odmietne. Správca obnovuje riadky aj po
  chybe/zastavení operácie, po dávke a pri návrate na kartu. Zachová výber,
  fokus, posun a rozbalenie skupín; výsledok pre starú cestu cache zahodí.
- EN/SK texty sú v spoločných katalógoch. Závislosti, formáty projektov,
  používateľské dáta a verzia sa nemenia.

Úplný čistý beh kandidáta `1e459ed`: **212 testov, OK, 221,185 s,
bez preskočenia**, nové prostredie z lockov, Windows build, zhoda 33 modulov
a úspešná diagnostika nového EXE (Tk/tkdnd, preklady, ikony, natívne importy
a nový proces).
Pribudlo 16 testov: stavy cache a chýbajúce potvrdenie, digest, poškodenie
rovnakej veľkosti, zmena metadát/ref/súboru, zrušenie a opakovanie, presná
revízia a UI obnova vrátane výberu, posunu, chyby a starej cesty.
Malé HTTP fixtures preverili faster-whisper, delený KInIT aj WeSpeaker cez
skutočný lokálny prenos a procesový worker; explicitná kontrola nepoužila
ďalšie prenosy váh. Nie je to stiahnutie veľkých modelov z verejného Hubu
ani test inferencie/GPU. Existujúca Tk matica EN/SK, oba vzhľady a mierky
100–200 % prešla; fyzické systémové DPI sa v tejto úlohe nemenilo.

Obnova odložená počas rozlišovania hlasov sa dokončí automaticky; ďalší
odchod a návrat na kartu nie je potrebný. Prvý vzdialený CI beh kandidáta
`1e459ed` skončil natívnym pádom Tk `0xC0000005` po úspešnej DPI matici,
bez úplného súhrnu. Nepočíta sa za úspešné overenie; opakovanie je oddelený
beh. Presná príčina natívneho pádu zatiaľ nie je potvrdená.

Pri kontrole sa našiel problém testovacieho prípravku: mock obnovy modelov
platil len pri vytvorení karty, automatický návrat už spúšťal worker počas
matice, ktorá okná okamžite ruší. DPI test teraz izoluje obnovu počas celého
behu, zachováva všetky pôvodné geometrické kontroly a navyše kontroluje
zachovanie dlhých stavových textov. Štyri samostatné integračné testy naďalej
vykonávajú skutočné obnovovanie inventára. Cielený beh: **6 testov, OK,
72,906 s, bez preskočenia**. Spúšťač navyše zapína výpis všetkých vlákien
pri natívnom páde. Kandidát `ec2d600` lokálne dokončil 212 testov (194,479 s),
ale jeho build bol prerušený pred dokončením, preto sa nepočíta za overené EXE.

Doplnenie 16. 10.: druhý CI beh `1e459ed` dokončil 212 testov s jedným
zlyhaním pôvodného 20-sekundového limitu procesového testu. Po chybe zostalo
bežať pomocné vlákno a CI bol neskôr zrušený limitom úlohy. Testovací helper
teraz v `finally` zastaví a ohraničene počká na svoj bridge; pôvodný limit
aj všetky kontroly checkpointu zostali nezmenené. Nová regresia vynucuje
prekročenie limitu a overuje ukončenie vlákna. Cielených 10 procesových
testov prešlo za 19,801 s. Príčina pôvodného prekročenia 20 sekúnd nie je
potvrdená; oprava čistenia ho nezamlčuje. Finálna sada má **213 testov**.

Pred synchronizáciou je povinný ešte build presného kandidátskeho commitu
z čistého klonu s novou `.venv`, opakovaním celej sady a diagnostikou nového
Windows EXE. Jeho SHA, logy a výsledok synchronizácie sa evidujú lokálne
mimo Gitu a v závere úlohy; historické buildy nie sú dôkazom pre tento strom.
Rýchla kontrola metadát nenahrádza explicitný hash pri podozrení na zmenu
bajtov so zachovanými metadátami ani ochranu pred úpravou samotného potvrdenia.

## F18 – dostupnosť a význam zoskupovania hlasov (16. 10. 2026)

Východiskový strom `a9955af` bol čistý. F16/F17 je synchronizované; jeho
čistá zostava prešla 213 testmi, novým EXE a GitHub Windows CI. Tieto výsledky
sú historické a nenahrádzajú overenie F18.

Potvrdený problém: kontrola modelu bola až v obsluhe kliknutia a chýbajúci
kaldi-native-fbank sa zistil až počas výpočtu embeddingov. Ručné priradenie,
hromadné premenovanie, ochrana súbežných úprav a Undo už existovali.

- Zoskupovanie sa sprístupní až po kontrole lokálneho modelu a importov
  NumPy, ONNX Runtime s CPU providerom a kaldi-native-fbank. Dôvod chýbajúcej
  súčasti aj technický detail sú viditeľné pred spustením. Kontrola pri
  zobrazení podrobností beží mimo Tk, bez sťahovania a načítania váh.
  Návrat k podrobnostiam/pomoc kontrolu zopakuje; kliknutie znovu preverí
  dostupnosť, aby odstránenie cache medzi kontrolou a spustením neprešlo.
- Pole hlasu ponúka existujúce označenia a zostáva voľne editovateľné.
  Vymazanie priradenia, premenovanie, Undo/Redo aj uloženie fungujú bez modelu.
- EN/SK pomoc, potvrdenie, stavové hlásenia a návod dôsledne opisujú
  zoskupovanie podobných hlasov v existujúcich úsekoch. Nejde o identifikáciu
  osôb ani presnú separáciu prekryvov či zmien hlasu vnútri jedného úseku.
  Algoritmus, prah, váhy, používateľské označenia a ASR sa nemenia.
- Závislosti a balenie nevyžadovali zmenu; build už obsahuje voliteľný runtime.

Overenie: prvý úplný beh odhalil orezanie titulkových polí pri 1024×768/200 %.
Pomoc bola presunutá vedľa statusu, bez oslabenia geometrických kontrol.
Cielených 14 testov potom prešlo (91,903 s). Finálny pracovný strom:
**219 testov, OK, 194,450 s, bez preskočenia**. Šesť nových regresií pokrýva
chýbajúci/neúplný model, každý chýbajúci import aj natívnu DLL, CPU provider,
blokovanie akcie, opakovanú kontrolu, zmenu cache, vlákno kontroly bez dirty
stavu a ručné opravy s Undo/Redo, uložením a otvorením databázy. Pôvodné
regresie úprav počas výpočtu a hromadného premenovania zostali zachované.
Tk matica preverila EN/SK, oba vzhľady a 100/125/150/175/200 % mierky.

Syntetické fixtures a mocky neoverujú presnosť WeSpeaker na reálnych hlasoch;
referenčné meranie sa nevykonalo a algoritmus sa preto nemenil. Preflight
nie je úplná validácia ONNX ani nový hash váh; slúži na včasnú kontrolu
predpokladov. Fyzické systémové DPI a manuálny Narrator neboli skúšané.
Pred pushom musí presný kandidát ešte prejsť čistým klonom, novou `.venv`,
celou sadou a novým Windows EXE. SHA a výsledky tejto kontroly sa zaznamenajú
lokálne mimo Gitu a v závere úlohy. Verzia sa nemení; nevzniká tag ani Release.

## F19 – priebeh dávky a odhad času (19. 10. 2026)

Východiskový strom `07e2eb5` bol čistý a synchronizovaný. Potvrdené pôvodné
chyby: rovnaká váha krátkeho a dlhého súboru, syntetických 100 % aj po chybe
a ETA odpočítavaná počas stagnácie bez nového checkpointu.

- Dĺžky sa zisťujú cez existujúci PyAV v pracovnom procese; po dekódovaní
  sa spresnia podľa PCM vzoriek. Neznáme dĺžky sa nezamieňajú za rovnakú váhu.
  Dávka používa časovú váhu a zvlášť počíta úspešné, chybové a prerušené
  položky. Chyba nezvyšuje priebeh; už uložený čiastočný postup zostáva.
- Stabilné udalosti fázy oddeľujú zisťovanie dĺžok, načítanie/sťahovanie,
  hashovanie, dekódovanie, VAD, prepis, export a zastavovanie. Príprava má
  neurčitý indikátor. Číselný priebeh zvuku sa nemení prenosovými udalosťami.
- ETA používa iba rastúce checkpointy v prepise, neodpočítava prácu počas
  čakania. Po 30 s bez postupu je neistá. Zmena súboru, fázy či dĺžky resetuje
  meranie; obnovený checkpoint sa nepovažuje za čerstvo vykonanú prácu.
  Text výslovne nezahŕňa prípravu. Pri chybe/zastavení sa neuvádza nulová ETA.
- EN/SK rozhranie a vývojový návod opisujú význam pokrytia časovej osi.
  Kontajnery môžu mať len približnú dĺžku; finálny údaj opraví dekódovanie.
  Závislosti, projekty, používateľské dáta, ASR algoritmus a verzia sa nemenia.

Overenie pred kandidátskym buildom: prvý beh odhalil prepísanie indikátora
sťahovania resetom percent v jednej dávke udalostí. Oprava prešla celou sadou
**227 testov, OK, 226,944 s, bez preskočenia**, vrátane DPI matice EN/SK,
oboch vzhľadov a mierok 100–200 %. Následné spresnenie neurčitých prípravných
fáz a prerušenia procesu prešlo **9 cielenými testmi, OK, 1,440 s**.
Finálna sada má **228 testov**. Nové regresie pokrývajú pomer dĺžok 1:999,
neznáme/nulové/neplatné a opravené dĺžky, skutočné metadáta malých WAV,
stagnáciu, obnovenie, chyby, zastavenie a nezávislosť sťahovania od dávky.

Ide o testy riadenia priebehu s mock ASR a malými syntetickými súbormi,
nie meranie presnosti ETA na dlhom reálnom CPU/GPU prepise. Výpočet závisí
od aktuálneho tempa a môže byť neistý počas dlhého chunku. Systémové DPI sa
nemenilo. Pred pushom sa vyžaduje čistý klon presného commitu, nová `.venv`,
všetkých 228 testov a nové overené Windows EXE; SHA a výsledky sa evidujú
lokálne mimo Gitu a v závere úlohy. Bez zmeny verzie, tagu alebo vydania.

## F20/F21 – konkrétne chyby a výsledok bez reči (20. 10. 2026)

Východiskový strom `0094f6e` bol čistý; vzdialená `main` zodpovedala tomuto
commitu. Potvrdená bola všeobecná rada o internete/menšom modeli a chýbajúci
samostatný výsledok prázdneho prepisu vo fronte.

- Spoločná vrstva chýb rozlišuje vstup, disk, oprávnenia, pamäť, GPU, model,
  sieť a konflikt projektu; neznáme príčiny označuje osobitne. Používa typy,
  kódy a kontext, nie preložené texty. EN/SK správy uvádzajú ďalší krok.
- Fronta uchováva kategóriu oddelene od technických podrobností. Podrobnosti
  sú v rozbaliteľnom dialógu; používa ho aj správca modelov a zápis/export
  editora. Zachovaný je stav uloženého projektu pri neúspešnom exporte.
  Bežné poverenia a HTTP adresy sa z diagnostiky odstraňujú.
- IPC prenáša nové voliteľné polia; stará fronta ostáva kompatibilná.
  Modelový loader zachováva pôvodnú príčinu; nedostatok miesta pri PCM
  má explicitný OS kód. Potvrdenie GPU → CPU sa nemení.
- Dokončené projekty a fronta uchovávajú výsledok `no_speech` a počet úsekov.
  „Reč sa nenašla“ vysvetľuje aj možnosť nerozpoznanej reči, nie iba ticha.
  Prázdny TXT/SRT neobsahuje diagnostické vety. Prerušenie ani poškodený
  vstup sa za tento výsledok nevydávajú; obnovenie výsledok znovu oznámi.

Pridaných sedem regresií: všetky kategórie a vnorené príčiny, odstránenie
poverení, reálny PyAV/VAD nad syntetickým tichom, poškodený súbor, uloženie/
obnova fronty, zobrazenie výsledku a oddelené rozbaliteľné podrobnosti.
Staršie testy nových hlásení boli aktualizované s ponechaním dátových kontrol.
Prvý beh odhalil kompatibilitu normalizácie fronty a whitelist IPC; opravené.
Druhý celý beh dokončil 235 testov za 202,536 s bez preskočenia s jedinou
chybou starého očakávania dialógu exportu. Test teraz navyše kontroluje
kategóriu oprávnení a technickú príčinu. Následných 21 cielených testov chýb,
exportu a procesového ASR prešlo za 15,467 s bez preskočenia.

Prvý čistý kandidát `cfd529a` dokončil 235 testov za 200,740 s s jediným
zlyhaním súbežného spustenia. Diagnostika ho reprodukovala 6-krát z 30:
pri inicializácii byte locku zlyhal bufferovaný zápis a `close()` zopakoval
flush, čím prekryl `OwnershipError` výnimkou `PermissionError`. Windows
stream zámku teraz zapisuje bez bufferovania; existujúci súbežný test
následne prešiel 30-krát z 30 za 6,994 s. Nejde o vypnutie zámku ani
uvoľnenie testových podmienok. Kandidát pred touto opravou nebol pushnutý.

Pred pushom sa vyžaduje úplný úspešný beh 235 testov presného kandidáta
v čistom klone s novou `.venv` a nové Windows EXE s diagnostikou. SHA
a konečné výsledky sa zaznamenajú lokálne mimo Gitu a v závere úlohy.
Skutočné vyčerpanie RAM/GPU ani zaplnenie disku sa nevykonáva; tieto chyby
sú simulované. Syntetické ticho nie je meranie presnosti na reálnom korpuse.
Fyzické DPI Windows ani Narrator neboli manuálne overené. Bez zmeny verzie,
závislostí, tagu a GitHub Release.

## F22 – samostatné otvorenie projektu a oprava cesty (22. 10. 2026)

Východiskový strom `70525c0` bol čistý a zhodný so vzdialenou `main`;
predchádzajúci Windows CI prešiel. Editor už ponechával text dostupný po
chybe zvuku, ale chýbalo otvorenie mimo fronty a overené pripojenie súboru.

- Otvoriť projekt v hlavičke vyberá `projekt.sqlite3`; používa rovnakú
  validáciu, zámok a ochranu neuložených zmien ako otvorenie z fronty.
  Nevytvára položku fronty ani nespúšťa prepis.
- Ponuka Úsek a titulky obsahuje Nájsť pôvodnú nahrávku. Existujúci worker
  overí veľkosť a SHA-256; až po zhode transakčne uloží cestu. Odtlačok,
  originál, úpravy, checkpointy, časovanie a ASR nastavenia sa nemenia.
- Nezhodný súbor, prerušená kontrola alebo chýbajúci odtlačok cestu nemenia.
  Bez zvuku je dostupná editácia a TXT/SRT; samostatný stav vysvetľuje
  obmedzenie prehrávania a hlasov. EN/SK katalógy aj návod sú doplnené.

Tri nové regresie prešli za 1,995 s: Unicode presunutá kópia, nezmenené
metadáta/originál, nesprávny súbor rovnakej veľkosti, chýbajúci odtlačok,
zrušenie hashovania a reálny Tk tok odobratia z fronty → otvorenie → úprava
bez zvuku → uloženie → opätovné otvorenie → odmietnutie → pripojenie.
Použitý je malý syntetický WAV s reálnym dekódovaním, nie ASR meranie.

Prvý celý beh 238 testov odhalil 20 DPI zlyhaní pre nové riadky editora.
Oprava nezaberá ďalšie riadky; druhý cielený beh odhalil skryté tlačidlo
v prázdnom paneli. Otvorenie je teraz v hlavičke. Samostatná finálna DPI
matica (2 testy, 74,441 s, OK) overila EN/SK, oba vzhľady, Tk mierky 100–200 %
a malé obrazovky. Kontroly neboli oslabené; zahŕňajú aj nový ovládací prvok
a zmenu tlačidla na ponuku. Medzibeh celej sady bol prerušený počas DPI
diagnostiky; nie je deklarovaný ako úspešný.

Pred pushom je povinný celý beh 238 testov bez preskočenia a nové Windows
EXE z čistého klonu presného kandidáta s novou `.venv`. Výsledok, SHA
a kontrolný súčet zostavy sa evidujú lokálne mimo Gitu a v závere úlohy.
Fyzické systémové DPI, Narrator ani zvukový výstup reproduktorov sa manuálne
neoverovali. Bez zmeny verzie, závislostí, tagu a vydania.

## F24 – vyhľadávanie jednotlivých výskytov (22. 10. 2026)

Východiskový strom `cce57d7` bol čistý a zhodný so vzdialenou `main`.
Potvrdené bolo filtrovanie úsekov bez pozícií jednotlivých zhôd.

- Samostatná Unicode logika vracia rozsahy v pôvodnom texte. Doslovné
  neprekrývajúce sa hľadanie ignoruje veľkosť písmen, zachováva diakritiku
  a podporuje NFC aj casefold bez zmeny obsahu projektu.
- Editor zobrazuje aktuálny/celkový výskyt oddelene od počtu úsekov.
  Prvá zhoda sa vyberie po Hľadať; ponuka Výskyty, F3 a Shift+F3 cyklicky
  prechádzajú konkrétne zhody vrátane viacerých v jednom úseku a cez stránky.
  V aktívnom poli sú označené všetky zhody a výraznejšie aktuálna. Náhľady
  ostatných úsekov zostávajú obyčajné textové bloky. Zvuk sa tým nespúšťa.
- Filter, stránkovanie aj navigácia najprv zachytia úpravy. Index sa obnoví
  pri zmene dotazu/dát, nie pri každom ďalšom výskyte. Počas písania sa
  nezobrazujú staré rozsahy ako aktuálne; stav vyzýva na obnovu výsledkov.
  História, uloženie, pôvodný prepis a časovanie zostávajú zachované.
- EN/SK preklady a návod opisujú správanie. Počítadlo používa existujúcu
  ohraničenú informačnú plochu; nová ponuka nezaberá ďalší riadok editora.

Päť nových regresií pokrýva viac zhôd, oba smery/obalenie, diakritiku,
kombinované znaky, emoji, prázdny výsledok/dotaz, 10 000 úsekov, uloženie
rozpísaných zmien, F3/Shift+F3 a čistý stav pri samotnej navigácii.
Prvý cielený beh odhalil indexovanie Tk za emoji; opravené. Celý medzibeh
242 testov odhalil päť DPI zlyhaní pre ďalšie tlačidlo a dve chyby nastavenia
tagov po zničení textového poľa. Opravené ponukou a kontrolou existencie poľa.
Následný cielený beh 21 testov ponechal iba staré očakávanie prvého výberu;
test teraz overuje okamžité zobrazenie aj návrat, pôvodné dátové kontroly
ostali zachované (opakovanie 1 test, 0,889 s, OK). Klávesová regresia prešla
za 2,892 s. Finálna DPI matica s aktívnym hľadaním: 2 testy, 86,359 s, OK,
EN/SK, oba vzhľady, malé obrazovky a Tk mierky 100–200 %.

Samotný index 100 000 krátkych syntetických úsekov/200 000 výskytov trval
0,126 s; nie je to meranie celého editora ani dlhého reálneho korpusu.
Fyzické systémové DPI a Narrator sa neoverovali. Pred pushom je povinný
čistý klon presného kandidáta, nová `.venv`, celý beh 243 testov bez
preskočenia a nové overené Windows EXE. SHA a výsledky sa evidujú lokálne
mimo Gitu a v závere. Bez zmeny verzie, závislostí, tagu a vydania.

Dodatočná kontrola predchádzajúceho CI F22 našla zlyhanie obnovy zámku po
páde. Izolovaná Windows skúška potvrdila rozdiel PID `.venv` spúšťača a
skutočného interpretra. Test pôvodne zabíjal iba PID spúšťača, takže nevedel
zaručiť ukončenie vlastníka zámku. Teraz reálny interpreter vykoná
`os._exit(17)` bez finally/atexit a test vyžaduje tento návratový kód pred
opätovným získaním zámku. Produkčné zamykanie sa nemení a kontrola obnovy
ani zachovania odovzdaných súborov sa nevypína.
Opravená skúška prešla 30-krát z 30 za 3,830 s.

23. 10.: čistý klon commitu `930b453` prešiel 243 testami za 244,275 s
bez preskočenia a novým Windows EXE vrátane frozen diagnostiky (35 modulov).
Push bol potvrdený, ale následný GitHub beh 39901167888 skončil jednou
chybou z 243 testov: druhý test pádu stále ukončoval iba Windows spúšťač,
tentoraz pri zámku modelovej cache. Všetky nové regresie vyhľadávania prešli.
Rovnaké ukončenie skutočného interpretra cez `os._exit(17)` sa preto použilo
aj pre modelovú cache a zostávajúci test pádu editora. Kontroly vlastníctva,
zachovania textu a zákazu odstránenia používanej cache ostali nezmenené.
Cielené overenie všetkých ôsmich testov vlastníctva: 2,644 s, OK.
Tento opravný kandidát pred ďalším pushom opäť vyžaduje celý čistý test/build;
výsledky konkrétneho SHA sa evidujú v lokálnom potvrdení a závere.

Čistý opravný kandidát `45db861` dokončil všetkých 243 testov za 436,430 s,
bez preskočenia, s jedným zlyhaním: existujúci
`test_real_process_crash_checkpoint_and_repeat_resume` pri opätovnom otvorení
dokončeného projektu prekročil limit 20 s a obslužné vlákno sa neukončilo.
Diagnostika zachytila blokovanie v `child_stop.set()` vo finally ASR procesu
(`src/asr_process.py`); presný spúšťač zatiaľ nie je potvrdený. Všetky testy
vlastníctva aj nové testy vyhľadávania prešli. Po dokončení sady bol ukončený
iba identifikovaný zaseknutý testovací interpreter. Build sa zastavil pred
PyInstallerom; pre tento kandidát nové EXE nevzniklo. Commit `45db861` sa
nepushol. GitHub main zostáva `930b453`, ktorého lokálna zostava prešla,
ale GitHub CI 39901167888 má vyššie uvedené zlyhanie. Synchronizácia opravy
a úspešné celkové overenie teda nie sú dokončené; kontroly sa neoslabovali.


## F25 – prehrávanie, výstup a tempo (23. 10. 2026)

Východiskom je lokálny `45db861`; existujúci necommitnutý záznam F24 v STATUS
zostáva zachovaný oddelene. Posun myšou aj klávesmi zachová pauzu alebo chod
prehrávania a pokračuje do konca nahrávky. Zmena výstupu/tempa zachová miesto
aj limit vybraného úseku. Ponuka editora otvára lokalizovaný dialóg výstupu
(a obnoví zoznam zariadení) a rýchlostí 0,75/1/1,25/1,5×. Nastavenie platí
pre editor, nemení projekt ani export. Chýbajúci explicitný výstup sa potichu
nenahrádza; nečakané zastavenie streamu zobrazí postup obnovenia. Pravidlá
klávesových skratiek a ochrana písania zostali zachované.

Tempo používa existujúci PyAV atempo s blokovým čítaním PCM, bez novej
závislosti, zmeny výšky tónu či celkovej kópie nahrávky. Čas sa prepočítava
na pôvodnú časovú os. Frozen startup diagnostika navyše skúša skutočný filter.

Prvý celý beh: 249 testov za 233,592 s, šesť DPI subtestov neprešlo kvôli
pridanému riadku tlačidla. Tlačidlo nahradila položka existujúcej ponuky,
kontroly sa neoslabovali. Následných 14 cielených testov prešlo za 77,692 s:
prehrávanie, klávesnica, stará DPI matica a nový dialóg EN/SK, svetlý/tmavý,
Tk mierky 100/125/150/175/200 %. Osem nových regresií pokrýva oba seek stavy,
limity, zmenu výstupu/tempa, chybu štartu a odpojenie, časovanie, reálny tempo
filter, zachovanie frekvencie syntetického tónu a nezmenený stav projektu.

Pred pushom musí presný kandidát prejsť celou sadou 251 testov bez preskočenia
z čistého klonu a novým Windows EXE. Konkrétny výsledok a SHA sú v lokálnom
potvrdení a závere. Fyzické odpojenie zariadenia, posluch reálnej reči,
systémové DPI Windows ani Narrator sa neoverovali. Latencia audio výstupu
nie je presnosť časových značiek exportu; zobrazenie sleduje audio bloky.
Verzia, tagy a vydanie sa nemenia.


## Úloha 24 – editor a exporty, Pre-release (26. 10. 2026)

Editor umožňuje rozdeliť dokončený segment pri kurzore a zadanom čase,
zlúčiť susedné segmenty rovnakého hovoriaceho a upraviť hranice. Kontroluje
poradie, prekryvy, hranice zvuku a milisekundové intervaly. Operácie patria
do Undo/Redo; pôvodný ASR prepis zostáva nezmenený. Prvá štrukturálna zmena
vytvorí zálohu databázy a bezpečne zvýši formát úložiska na 2. Staršia
aplikácia tento formát odmietne. Neplatné časovanie slov sa odstráni;
ručne určené hranice export nepredlžuje kvôli mäkkému limitu titulkov.

Uloženie projektu už automaticky neexportuje. Samostatný dialóg vyberá
originál alebo uloženú revíziu, TXT/SRT/VTT/DOCX/JSON a zahrnutie časov či
hovoriacich. SRT/VTT vždy obsahujú časy. Export beží mimo UI a publikuje
celú generáciu až po zápise všetkých súborov; predchádzajúce exporty ostávajú.
DOCX vzniká zo štandardného OOXML bez novej závislosti. Program, Windows
textové metadata a aktuálne návody používajú označenie Pre-release;
interné číselné identifikátory a historické vydania sa nemenia.

Overenie pracovných zmien: celý beh 260 testov za 256,308 s bez preskočenia;
po posledných úpravách 27 cielených testov za 8,231 s. Deväť nových regresií
pokrýva revízie, zálohu, Undo/Redo, uloženie/otvorenie, Unicode, odmietnutie
neplatných časov, formáty, dialóg a zlyhanie publikovania. Povinné konečné
clean-clone testy a nové Windows EXE sa overujú na presnom commite pred
pushom; výsledok a SHA zaznamenáva lokálne potvrdenie a záverečná správa.

Obmedzenia: štrukturálne úpravy vyžadujú dokončený prepis a známu dĺžku
zvuku; zlúčenie rozdielnych hovoriacich vyžaduje najprv ručné zjednotenie.
Pri chýbajúcom časovaní slov sa presné časy slov neodhadujú. DOCX sa overil
ako ZIP/XML, nie vizuálne vo Worde. Testy Tk mierok nie sú fyzické systémové
DPI Windows. Nové meranie ASR/GPU, Narrator ani ručné vizuálne overenie
všetkých kombinácií DPI sa nevykonalo. Existujúci nesúvisiaci lokálny záznam
STATUS zostáva mimo commitu; staršie neúspechy nie sú výsledkom tohto kandidáta.


## Úloha 25 / F26 – dôveryhodné meranie kvality (26. 10. 2026)

Vyhodnocovanie používa produkčné načítanie presného offline snapshotu,
backendové efektívne nastavenia a transcribe_job vrátane diskového PCM,
VAD, checkpointov a exportu. Každá nahrávka/model má izolovaný proces a
časový limit. Voľba cpu/cuda je explicitná (predvolene CPU); zlyhanie GPU
sa nepreklasifikuje na CPU meranie. Ukladajú sa parametre, revízia modelu,
verzie balíkov, odtlačky zdrojov/referencie, hardware, čas načítania a fázy.

Schema=2 validuje oprávnenie, referenciu, SHA-256, jedinečnosť, časové hranice,
jazyky, slová a anotácie mien/čísel. Report rozlišuje WER/CER, anotované
výskyty mien/čísel, časové pokrytie jazyka, prechody, hranice zhodných slov,
RTF, peak working set a vzorkovanú per-process VRAM. Chýbajúce merania sú
null; chyby ostávajú v súhrnoch scenárov. Dokumentácia presne opisuje
normalizáciu, tolerancie a obmedzenia anotácií/zarovnania a WDDM.

Overené: 10 nových simulovaných regresií za 0,146 s bez preskočenia; reálne
čítanie Windows pamäte a hardvérových metadát prešlo. Sandbox jeden pokus
zablokoval pri dočasných súboroch; opakovanie s potrebným prístupom prešlo.
Presný kandidát pred pushom musí dokončiť celú sadu (270 testov) a nový
Windows EXE z čistého klonu; výsledky konkrétneho SHA sú v lokálnom potvrdení
a závere. Predošlá úloha 24 bola synchronizovaná ako b9ce8ea: čistý beh
260 testov za 206,836 s, EXE aj GitHub CI (260 testov, 344,149 s) prešli.

Reálny oprávnený referenčný korpus nie je v sledovaných zdrojoch k dispozícii.
Neboli merané reálne WER, mená, prechody, GPU výkon ani presnosť časovania;
neuvádzame vymyslené skóre. README vyhodnocovania obsahuje potrebné ukážky
a postup. Benchmark nemeria UI/frontu ani produkčný IPC watchdog; používa
rovnakú produkčnú úlohu v izolovanom procese s vlastným timeoutom. VRAM je
vzorkovaný dolný odhad špičky, na WDDM môže byť nedostupná. Práva a ručnú
správnosť referencie deklaruje autor korpusu. Verzia, tagy ani Release sa nemenia.

Prvý čistý kandidát 396f38d dokončil 270 testov za 246,568 s bez preskočenia,
ale kontrola balíka odmietla nepribalený eval_corpus (ani ďalšie dva nové
pomocné moduly neboli závislosťou UI). Do špecifikácie boli pridané explicitné
importy všetkých troch modulov; kontrola zdrojovej zhody sa neoslabovala.
Tento kandidát sa nepushol. Opravený kandidát vyžaduje nový celý test/build.

Opravené balenie f26ffe4 prešlo čistou sadou 270 testov za 242,118 s a novým
EXE (40 zhodných modulov, startup PASS); push bol potvrdený. GitHub CI
40312095610 však po 270 testoch za 287,030 s zistilo jednu chybu nového testu:
čítanie UTF-8 manifestu bez explicitného encoding použilo na runneri cp1252.
Produkčný čítač encoding/JSON bajty používa explicitne. Test bol opravený
na UTF-8 bez oslabenia kontroly duplicít; ďalší kandidát musí znova prejsť
celým čistým test/build a vzdialeným CI. Tento neúspech sa neskrýva opakovaním
rovnakého behu bez opravy.


## Úloha 26 / F27, F28 – uzamknuté zostavovanie (27. 10. 2026)

Existujúce runtime/speakers/build wheel locky s SHA-256 a Hub pin 0.36.2 boli
zachované; aplikačné závislosti sa neaktualizovali. Pribudol bootstrap.lock
pre už používaný pip 25.0.1. `.python-version` zjednocuje CPython 3.12.10 x64
v setup/test/build aj CI. Resolver odmieta iný Python/architektúru a konfliktné
reporty. Nová kontrola porovnáva vstupy, constraints, presný pin interného
Hub transportu a reálne nainštalovaný reťazec v projektovom .venv. Neznáme
verzie alebo balíky sa odmietajú bez automatického mazania prostredia.

Build na začiatku zneplatní staré potvrdenie (so zálohou), potom overí
prostredie, celú regresnú sadu, PyInstaller, zdrojovú zhodu a startup EXE.
Až po úspechu zapíše build-manifest.json s SHA-256 vstupov, zostavy a
interpretera, commitom a verziami. ZIP balenie vyžaduje platný manifest a
zhodu aktuálnych vstupov/súborov/prostredia. Manifest sa pribalí do ZIP.

Sedem nových regresií prešlo za 1,100 s: locky, drift, Hub nesúlad, blokovanie
balenia pri zlyhaní testov, neplatný/pozmenený manifest aj malý ZIP s checksum.
Prvý PowerShell pokus zastavila lokálna politika Windows PowerShellu pred
testovanou chybou; test používa dostupný PowerShell 7 bez zmeny politiky.
Lokálne overenie aktuálneho prostredia potvrdilo 43 uzamknutých distribúcií.
Pred pushom presný kandidát musí dokončiť čistú inštaláciu, celých 277 testov
(vrátane reálneho lokálneho HTTP transportu) a novú overenú Windows zostavu.
Konkrétne SHA a konečné výsledky sú v lokálnom potvrdení a závere.

Nejde o preukázanú bitovú identitu dvoch EXE na odlišných počítačoch.
Manifest je evidencia vstupov a ochrana pred náhodným zastaraným balíkom,
nie kryptografický podpis. Python inštalátor musí mať dôveryhodný pôvod;
manifest meria použitý interpreter. GPU lock ani reálne veľké modelové
sťahovanie neboli súčasťou tejto úpravy. Verzia/tag/Release sa nemenia.
Predošlá F26 bola dokončená commitom 9190a5f: čistých 270 testov za 215,958 s,
Windows EXE PASS a GitHub CI 40314089987 (270 testov za 203,125 s) PASS.

## Úloha 27 – oddelenie vrstiev a zdrojového balíka (28. 10. 2026)

Zdrojové moduly sú v `src/ndtranskripthor`: presentation, application,
projects, queueing, asr, models, audio, exports, core, evaluation a diagnostics.
Spúšťače, `src/version.py`, assets/locales, tests, scripts a packaging zostávajú
na existujúcich verejných miestach. Importy, worker procesy, eval CLI,
inštrumentovaný Hub pin a rekurzívny audit pribaleného kódu používajú nové cesty.
Pred presunom vznikla lokálna ignorovaná ZIP záloha; používateľské dáta,
modely a staršia nesúvisiaca rozpracovaná poznámka v tomto dokumente zostali zachované.

Ukladanie/export editora vykonáva dátová služba `perform_project_io`; udalosti
odlišujú commit od exportu. Tk dialógy a prekladané combo boxy už nie sú
v core. Priebeh je v application, atómový zápis v core a PCM časová os v audio.
Protokoly EventSink/Transcriber/ProfileStore/Playback/ExportProject dokumentujú
hranice. Editor ani exportér nepracujú priamo so SQLite: zoznam revízií,
nové ID a exportný stav poskytuje Project. Schémy, checkpointy, pôvodné texty,
revízie, nastavenia a ASR protokol sa nemenia; migrácia projektov nie je potrebná.

Päť nových regresií overuje smer importov, studený import bez Tk/modelových
runtime, zdrojové/frozen Unicode cesty, službu uloženia a opätovného otvorenia
s nezmeneným originálom a konkrétnu chybu zápisu bez falošného potvrdenia.
Úplný priebežný beh dokončil 282 testov za 366,779 s bez preskočenia;
jediná chyba bola starý import dialógu v teste. Po jeho oprave a dokončení
exportného rozhrania prešlo všetkých 21 cielených testov za 16,777 s.
Zdrojový `prepis.py --self-test-startup` PASS: Tk, tkdnd, assety, oba katalógy,
natívne importy, tempo audia, päť exportných formátov a nový lokálny proces.

Prvý prerušený vývojový beh zachytil aj blokovanie ASR stop udalosti;
samostatný procesový test aj nasledujúci celý beh procesových testov prešli.
Táto občasná staršia neistota sa nepovažuje za vyriešenú týmto refaktorom.
Pred pushom je povinný nový úplný beh bez chýb/preskočenia a Windows EXE
z čistého klonu presného kandidáta. Konkrétne SHA, finálne počty a výsledok
zostavy budú v lokálnom overovacom potvrdení a závere úlohy; priebežné výsledky
vyššie nenahrádzajú túto bránu. Testovacia matica používa Tk scaling 100–200 %,
nie prepínanie systémového Windows DPI. Skutočné modely/GPU, systémový drag
and drop a posluch na fyzických zariadeniach sa v tejto úlohe znovu nemerali.
Verzia, tag a GitHub Release sa nemenia.

## Úloha 28 – lokálne dáta a diagnostika (28. 10. 2026)

Nastavenia obsahujú prehľad umiestnení a logických veľkostí profilu, modelov,
výstupov, známych projektov a PCM cache. Meranie prebieha mimo UI, má limity,
nenasleduje reparse body a označuje čiastočné výsledky. Prekrývajúce sa
priečinky sa nesčítavajú. Prehľad nič nemaže; texty odlišujú odobratie z fronty,
odstránenie priečinka projektu a potvrdené odstránenie modelu. Vysvetľujú aj
čitateľné lokálne dáta a absenciu automatického šifrovania aplikáciou.

Diagnostický ZIP obsahuje iba allowlist technických údajov a počtov, bez
zvuku, prepisov, ciest, profilov, projektov a logov. Pred uložením sa zobrazia
oba celé súbory. Uloženie publikuje presne tento snapshot atómovo; nič sa
neodosiela. Obnovenie vyžaduje nový náhľad; zatvorenie počká na zápis.

Deväť nových regresií overuje súkromie, presnosť ZIP, chybu publikovania,
neúplné meranie, offline chýbajúci model, zachovanie súborov po odobratí,
náhľad a zatvorenie počas zápisu. Celá sada: 291 testov, 245,163 s, OK,
bez preskočenia. Reálne Tk okná overené v EN/SK, svetlom/tmavom vzhľade,
pri 640 × 480 a Tk scaling 100/125/150/175/200 %. Nejde o manuálne prepínanie
systémového Windows DPI ani o test čítačky obrazovky.

Skutočný Tiny CPU prepis vlastnej syntetickej SAPI nahrávky prešiel offline:
revízia d90ca5fe260221311c53c58e660288d3deb8d356, 2 úseky, 2,578 s,
0 Python sieťových pokusov, 42 TCP vzoriek, 0 pozorovaných spojení/chýb.
Rozsah je vlastný proces, nie úplný packet capture, UDP, KInIT alebo GPU.
Opakovateľný nástroj je scripts/verify_offline.py; lokálne dáta ostali mimo Gitu.
Pred synchronizáciou musí presný kandidát prejsť novou úplnou sadou a Windows
EXE v čistom klone; potvrdenie SHA/zostavy zostane v lokálnom overovacom zázname.
Verzia, tagy ani GitHub Release sa nemenia. Nesúvisiaca staršia poznámka
v tomto súbore zostáva unstaged.

## Úloha 29 – návody a informácie o verzii (28. 10. 2026, Pre-release)

README zostáva stručný; RELEASE-NOTES.md opisuje aktuálne funkcie a obmedzenia.
Návod dopĺňa obnovu prípravy, presnú revíziu modelu, originál a používateľské
revízie, otvorenie bez fronty/zvuku, exportné formáty, modelový inventár a offline.
Historické dokumenty označujú verziu a dátum evidencie; neznáme dátumy merania
sa nevymýšľajú. Historické počty a cesty nie sú predpisom pre aktuálny build.
Minimum 197 je oddelené od výsledku konkrétneho testovacieho behu.

Nastavenia obsahujú O aplikácii v EN/SK s autoritatívnym Pre-release a internou
verziou kompatibility. Presné autorstvo je zachované. Verzia sa nemení.
Dve nové regresie kontrolujú lokálne odkazy a informácie dialógu vrátane
formátov a autorstva. Prvý úplný beh: 293 testov za 331,583 s, jedna chyba
novej kontroly starej cesty v DEVELOPMENT; ostatných 292 prešlo. Po oprave
zálohovacieho pokynu prešli obe nové regresie za 0,013 s. Povinný čistý klon
musí pred pushom prejsť celou sadou aj novým Windows EXE; konkrétne potvrdenie
bude viazané na SHA v lokálnom overovacom zázname a závere úlohy.

Obsah natívneho informačného dialógu bol testovaný s nahradeným messagebox;
jeho skutočný vzhľad pri všetkých systémových DPI sa neoveroval. Existujúca
Tk matica hlavného rozhrania prešla. Táto dokumentačná úloha neopakuje reálny
ASR/GPU ani offline merania; uvádza dátum a rozsah už vykonaných skúšok.
Používateľské dáta a staršia nesúvisiaca unstaged poznámka zostávajú zachované.

Čistý kandidát `1b1b132` (28. 10. 2026, Pre-release) dokončil 293 testov
za 321,552 s bez preskočenia, s jedným zlyhaním:
`test_missing_ui_ack_has_deadline` prekročil 20 s a obslužné vlákno sa
neukončilo. Diagnostika zachytila blokovanie multiprocessing Event.set
v application/asr_process.py. Obe nové dokumentačné regresie prešli.
Ide o už zaznamenaný typ neistoty procesového zastavovania; táto úloha
algoritmus ASR nemení a príčinu nevyhlasuje za opravenú. Po úplnom súhrne
boli ukončené iba identifikované zaseknuté interpretery tohto testu.
Povinná brána zablokovala PyInstaller: nový EXE pre úlohu 29 nevznikol,
commit sa nepushol. Zmeny sú zachované lokálne; vzdialený stav sa musí
pred ďalšou synchronizáciou znova overiť. Kontroly sa nezoslabovali.

## F30 – overenie a oprava zastavovania ASR (29. 10. 2026, Pre-release)

Kontrola nad F29 (lokálne 1b1b132 + 62a0c9e) potvrdila v zachovanom trace
blokovanie rodiča v child_stop.set vo finally. Izolovaná reprodukcia s reálnym
spawn procesom ukázala, že po os._exit(19) počas držania podmienky Event jej
zámok nie je dostupný ani po ukončení procesu. Konkrétne časovanie pôvodného
preteku v F29 nie je spätne známe; opustený zámok a blokujúca cesta sú potvrdené.

Iba medziprocesový stop signál používa nový StopSignal: zdieľaný byte bez
zámku, monotónne 0 → 1, čerstvý pre každý beh. set/is_set nečakajú na zámok
ukončeného procesu. wait pre sťahovací backoff kontroluje príznak každých
najviac 50 ms (plánovanie OS môže pridať oneskorenie). Štartovacia brána,
protokol, GPU súhlas, checkpointy aj časové limity zostávajú nezmenené.

Dve nové regresie overujú timeout/oznámenie a skutočný spawn s pádom aj
násilným ukončením. Cielených 12 testov prešlo za 16,014 s; pôvodný test
nepotvrdeného UI prešiel všetkými 10 vopred stanovenými opakovaniami za
10,309 s. Žiadny limit ani kontrola sa nezoslabili. Tieto testy používajú
skutočné procesy, ale simulované ASR; nie sú meraním modelu alebo GPU.

Pred pushom musí čistý klon presného kandidáta dokončiť úplnú sadu bez skipov
aj nový Windows EXE. Finálne SHA a výsledok sú viazané na lokálny overovací
záznam a záver úlohy. F29 zmeny sa zachovávajú, rovnako staršia nesúvisiaca
unstaged poznámka. Verzia ani vydanie sa nemenia.

## F31 – oddelený QML prototyp a rozhodnutie (29. 10. 2026, Pre-release)

Práca je vo vetve `codex/testing-qml-f31`, nad jadrom F30 `fb69872`.
Pred začiatkom boli overené úspešný čistý F30 build (295 testov bez skipov,
nový Windows EXE) aj úspešné GitHub CI 40825052960. Nejde o tvrdenie, že
všetky reálne modely/GPU a systémové scenáre boli certifikované.

`src/prototype_qml` je samostatný adaptér nad StateStore, Project,
perform_project_io, Player a riadeným ASR procesom. Má vlastný profil,
otvára pracovné SQLite kópie, zachováva originál a používa existujúce revízie.
Stabilné Tk rozhranie a jeho funkcie sa nemigrujú. Qt Essentials/shiboken6
6.12.0 sú voliteľné, uzamknuté vrátane hashov; stabilný EXE ich vylučuje.
Samostatné setup/run/test/build skripty a QML audit sprístupňujú experiment.

Prvý úplný lokálny regresný beh dokončil 295 testov za 292,345 s bez
preskočenia, OK. Sedem prvých QML scenárov prešlo vrátane reálnych klávesov,
10 000 úsekov, zachovania originálu a chyby offline modelu cez skutočný
proces. Finálnych osem QML testov prešlo za 6,612 s; ôsma kontrola overuje
QAccessible rolu/názov editora. Pri kontrole rozloženia sa našla a opravila
cyklická väzba výšky ScrollView; kontrola QML upozornení zostala zachovaná.
Prakticky bol overený výstup prehrávača syntetickým tichom a pravidlá posunu
pri pauze/prehrávaní. Nešlo o reálnu ASR inferenciu ani posluch hlasu.

Merania na pevnom primárnom monitore: QML pracovná sada 184,60–234,54 MiB
pri skutočných pomeroch 100–200 %, oproti približne 48,5 MiB nečinného Tk.
Nečinná odozva bola podobná; malé teplé vzorky štartu nepreukazujú podstatné
zrýchlenie. Obe témy, malé/veľké okno a konkrétne snímky boli skontrolované;
nejde o úplné systémové prepínanie DPI ani potvrdenie Narratora.

Odporúčanie: zatiaľ nemigrovať. Rozsah, reprodukcia, presné metriky,
obmedzenia funkčnej parity/prístupnosti a ďalšia rozhodovacia brána sú v
[QML-EXPERIMENT.md](QML-EXPERIMENT.md). Verzia/tag/Release sa nemenia.
Pred pushom sa musí presný kandidát ešte overiť z čistého klonu celou sadou,
novým Tk aj QML Windows EXE a ich auditmi; výsledok je viazaný na SHA a
lokálny záznam. Samostatné QML testy nenahrádzajú povinnú bránu. Staršia
nesúvisiaca unstaged poznámka sa zachováva mimo tohto commitu.

Doplnenie 30. 10. 2026: prvé QML balenie prešlo auditom 68 Python modulov,
ale skutočný štart odhalil nekompatibilnú ICU DLL pribratú z cudzieho PATH.
Jej exporty mali príponu `_78`, kým Qt požadovalo Windows ICU symboly bez
prípony. Cesta v Analysis-00.toc a čítanie chybového dialógu potvrdili príčinu.
Po lokálnej zálohe a diagnostickom vyradení tejto jedinej DLL rovnaké EXE
prešlo QML/fronta/kópia/editácia/uloženie/posun/témy. Tento zásah nie je
náhradou čistého zostavenia ani dôkazom finálneho kandidáta.

Zostavovací wrapper teraz obmedzuje PATH na projektové .venv, používaný
Python a Windows; cudzie knižnice sa nemajú dostať do analýzy závislostí.
Regresia overuje kolíziu ICU v cudzom priečinku a zachováva kontrolu, že
neúspešné testy zastavia balenie. Osem build-contract testov prešlo za 0,843 s.
Celá sada po doplnení obsahuje 296 testov; jej úspech pre opravný kandidát
musí potvrdiť nový čistý beh. Push zostáva podmienený jeho výsledkom.

Čistý kandidát `819abd0` bol 30. 10. 2026 úspešne overený: 296 regresných
testov za 299,738 s a 8 QML scenárov za 5,358 s, bez preskočenia. Nový Tk
EXE prešiel auditom 65 modulov a štartom vrátane tkdnd/natívnych importov/
spawn; nový QML EXE auditom 68 modulov, zhodou QML/logo súborov a skutočnou
skúškou fronty, kópie projektu, editácie/uloženia, posunu a oboch tém.
Manifest Tk zostavy aj čistota klonu boli znovu overené. Cudzia ICU DLL sa
v novom QML balíku nenachádza; ručný zásah do nového balíka nebol potrebný.
Logická veľkosť celých priečinkov je 1 647 199 411 bajtov (Tk) a
1 795 612 084 bajtov (QML), rozdiel približne 142 MiB. Nejde o veľkosť ZIP.
Výsledky sú evidencia uvedeného SHA, nie automatické potvrdenie neskorších
zmien. Finálny dokumentačný commit musí pred pushom absolvovať rovnaké
čisté overenie. Odporúčanie nemigrovať sa na základe týchto výsledkov nemení.

## Distribučný kandidát (2. 11. 2026)

Pridané samostatné basic/extended Windows Tk zostavy. Predvolený extended
zachová KInIT/PyTorch; basic ho vylučuje bez zmeny ASR projektov a pri pokuse
o KInIT vysvetlí potrebu rozšíreného balíka. Oba buildy majú povinné celé testy,
audit zdrojov a EXE diagnostiku s odstráneným Pythonom z PATH.
Balenie nemení overený runtime strom, zbiera aj NOTICE, doplnkové pôvodné
licencie s URL/SHA-256 a vytvára samostatný manifest všetkých súborov ZIP.
Nepribaľuje modely ani používateľské dáta. Postup: DISTRIBUTION.md.

Prvý pracovný beh: 301 testov, OK, bez preskočenia. Nové regresie pokrývajú
NOTICE, chýbajúce oznámenie, bezpečné cesty, chybu KInIT v basic a build gate;
rozšírený test ZIP overuje hash každého súboru a nemennosť vstupnej zostavy.
Čistý kandidát `c354e72` následne prešiel oboma buildmi: extended 301 testov
za 227,340 s, basic 301 testov za 299,955 s, oba bez preskočenia. Oba nové EXE
prešli auditom 65 modulov a štartom Tk/tkdnd/exportov/audio filtra/spawn.
Basic neobsahuje torch/transformers adresáre. Oba ZIP prešli SHA-256 všetkých
súborov, kontrolou celého archívu a štartom skutočne rozbaleného EXE z dočasného
Unicode priečinka s izolovaným PATH. Licenčný inventár nemá chýbajúce texty
Python distribúcií; otvorené natívne/licenčné podmienky sa tým neuzatvárajú.

Meranie c354e72: basic ZIP 118 719 868 B, rozbalený 277 320 004 B; extended
ZIP 438 054 866 B, rozbalený 1 651 406 268 B (vrátane manifestov a oznámení).
Odporúčanie: samostatný basic ZIP a extended ZIP pre KInIT, nie ručné
kopírovanie runtime doplnkov. Kontrola `verify_distribution.py --startup`
je opakovateľná a odmieta chybné checksumy, duplicitné a nebezpečné ZIP cesty.
Tieto výsledky patria uvedenému SHA; finálny dokumentačný/overovací commit
musí pred pushom znovu prejsť celým čistým buildom.

Nenašiel sa Code Signing certifikát ani Windows Sandbox/SignTool v PATH.
Skúška na čistom Windows bez nainštalovaného Pythonu preto nie je potvrdená.
Aktuálna FFmpeg DLL hlási LGPL version 3 or later; potrebné presné zdroje
natívnej zostavy a distribučné podmienky aplikácie ostávajú otvorené pred
publikovaním. Kandidát sa nepovažuje za právne ani systémovo finálne overený.
Verzia/tag/Release sa nemenia, balíky sa nepublikujú.


## Záverečné prijímacie overenie – úloha 32 (5. 11. 2026)

Protokol: [ACCEPTANCE.md](ACCEPTANCE.md). Produkčný základ `52a4f5c`,
bez zmeny verzie alebo aplikačného kódu. Prvý úplný beh: 301 testov,
274,107 s, OK, bez preskočenia. Nová regresia skutočného SQLite SQLITE_FULL
prešla samostatne (1 test, 0,070 s): rollback zachová uloženú revíziu,
text aj originál; opakovanie po zvýšení kapacity a opätovné otvorenie uspeje.
Presný synchronizovaný kandidát vyžaduje nový čistý celý test/build;
staršie výsledky nie sú jeho potvrdením.

Reálny Tiny CPU offline prešiel (0 Python sieťových pokusov a 0 TCP spojení
v 30 vzorkách); oba existujúce EXE prešli opakovanou inferenciou/exportom.
Obnova reálneho prepisu zachovala checkpoint a dokončila 12 chunkov /
24 segmentov. Dvojhodinové dekódovanie: peak RSS 62,76 MiB s diskovou PCM
oproti 1 150,71 MiB pôvodne. Pri 100k syntetických segmentov odovzdanie
uloženia pod 1 ms, najväčšia medzera Tk heartbeat 101,91 ms.

Odporúčanie: zatiaľ NEVYDÁVAŤ finálny release. Čistý Windows bez Pythonu,
reálny systémový drop, systémové DPI/viac monitorov/Narrator, NVIDIA,
KInIT inferencia, referenčná kvalita a fyzické poruchové scenáre nie sú
úplne overené. Native licenčné podmienky zostávajú otvorené. Strom UIA
ukazuje prevažne nepomenované panely; to nie je úspešný test čítačky.
Automatické testy, simulácie a reálne skúšky sú v protokole oddelené.
Používateľské dáta, súkromné dôkazy a distribučné balíky sa nepublikujú.


## Príprava Pre-release 1 (5. 11. 2026)

Na výslovný pokyn autora je pripravené prvé GitHub pre-release s označením
`pre-release-1`. README je skrátené na opis, stiahnutie a spustenie.
Interná verzia a dátové formáty sa nemenia. Rozšírený Windows ZIP obsahuje
runtime KInIT/PyTorch bez modelových váh; nič z používateľských dát.
Základ cb8c237 prešiel 302 testami za 302,435 s bez preskočenia, novým EXE
a reálnym Tiny CPU prepisom dvakrát. Nový dokumentačný kandidát musí pred
publikovaním opäť prejsť čistým buildom. Otvorené body ACCEPTANCE.md ostávajú
platné; pre-release nie je potvrdenie finálnej pripravenosti ani podpisu EXE.
