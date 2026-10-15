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

Pracovný regresný beh: **211 testov, OK, 196,910 s, bez preskočenia**.
Pribudlo 15 testov: stavy cache a chýbajúce potvrdenie, digest, poškodenie
rovnakej veľkosti, zmena metadát/ref/súboru, zrušenie a opakovanie, presná
revízia a UI obnova vrátane výberu, posunu, chyby a starej cesty.
Malé HTTP fixtures preverili faster-whisper, delený KInIT aj WeSpeaker cez
skutočný lokálny prenos a procesový worker; explicitná kontrola nepoužila
ďalšie prenosy váh. Nie je to stiahnutie veľkých modelov z verejného Hubu
ani test inferencie/GPU. Existujúca Tk matica EN/SK, oba vzhľady a mierky
100–200 % prešla; fyzické systémové DPI sa v tejto úlohe nemenilo.

Čistý kandidát `573aa4e` prešiel 211 testmi (242,332 s), novým Windows
buildom, zhodou 33 pribalených modulov a diagnostikou Tk/tkdnd, prekladov,
ikon, natívnych importov a nového procesu. Následná kontrola doplnila
automatické dokončenie obnovy odloženej počas rozlišovania hlasov: nie je
potrebný ďalší odchod a návrat na kartu. Všetky 4 cielené UI regresie prešli;
finálna sada má 212 testov. Tento posledný doplnok vyžaduje nový čistý build.

Pred synchronizáciou je povinný ešte build presného kandidátskeho commitu
z čistého klonu s novou `.venv`, opakovaním celej sady a diagnostikou nového
Windows EXE. Jeho SHA, logy a výsledok synchronizácie sa evidujú lokálne
mimo Gitu a v závere úlohy; historické buildy nie sú dôkazom pre tento strom.
Rýchla kontrola metadát nenahrádza explicitný hash pri podozrení na zmenu
bajtov so zachovanými metadátami ani ochranu pred úpravou samotného potvrdenia.
