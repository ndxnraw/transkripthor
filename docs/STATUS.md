# Stav projektu

Aktuálny zdroj je `src/`, verzia **2.1.3b** z `src/version.py`.
Posledné publikované EXE je GitHub Release `v2.1.3b`; novšie zdrojové opravy
nie sú novým vydaním. SYNC nezvyšuje verziu ani nevytvára tag.

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
