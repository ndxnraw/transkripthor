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

Reálne CUDA a plná KInIT inferencia, presnosť na oprávnenom CZ/SK korpuse,
všetky fyzické systémové DPI/prepínanie monitorov, Explorer OLE drop
a manuálny screen reader vyžadujú osobitné overenie. Automatické Tk/mock
testy ich nenahrádzajú. GPU lock zatiaľ nie je overený. Historický audit
F16–F21 zostáva podkladom na cielený funkčný audit (integrita starej cache,
obnova inventára, dostupnosť voliteľných hlasov, váženie postupu/ETA,
klasifikácia chýb a ticho). Upratanie nesľubuje opravu týchto tém.
