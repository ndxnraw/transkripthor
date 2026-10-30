# F31 – oddelený PySide6/QML experiment

Stav: **testing prototyp, nie náhrada stabilnej aplikácie**. Dátum meraní:
29. 10. 2026, Pre-release, základ jadra `fb69872` (F30). Pracovná vetva:
`codex/testing-qml-f31`. Verzia ani GitHub Release sa nemenia.

## Rozhodnutie

**Zatiaľ nemigrovať stabilné rozhranie.** QML dokáže použiť existujúce služby
bez prepisovania ASR a projektového formátu. V tomto malom prototype však
nepreukázalo zásadné zrýchlenie štartu ani odozvy a má vyššiu pamäťovú réžiu.
Chýba potvrdenie Narratorom, vysokým kontrastom a úplná funkčná parita editora.
To nestačí na výber cieľovej technológie pre stabilnú aplikáciu.

Ďalšia rozhodovacia brána: meranie na rovnakom monitore a hardvéri aspoň
10 studených štartov každého EXE; dostupnosť všetkých akcií cez Narrator;
prenos medzi monitormi; veľký editor pri ukladaní; porovnanie podpísaných
balíkov na čistom Windows. Až potom rozhodnúť o migrácii. Tento experiment
nezavádza druhý programovací jazyk pre jadro ani nový ASR backend.

## Spustenie a oddelenie dát

```powershell
.\scripts\setup-qml.ps1
.\scripts\run-qml.ps1
.\scripts\test-qml.ps1
.\scripts\build-qml.ps1
```

Setup používa projektové `.venv`, presný Python z `.python-version` a
voliteľný `requirements/qml.lock` s SHA-256 Windows wheelov. PySide6-Essentials
6.12.0 a shiboken6 6.12.0 sa nepridávajú do povinného runtime locku.

Výsledok QML balenia: `dist/ND TranskripThor QML Testing/ND TranskripThor QML Testing.exe`.
Celý priečinok musí zostať spolu. Skript najprv vykoná povinný stabilný build
s celou regresnou sadou a samostatne otestuje QML; chyba zastaví ďalší krok.
Nasleduje audit pribaleného Python kódu a reálny štart QML EXE s projektom.
Stabilný Tk balík výslovne vylučuje PySide6, shiboken6 a prototype_qml.

Predvolený profil je `%LOCALAPPDATA%/NDTranskripThor-QML-Testing`. Voliteľný
`run-qml.ps1 -Profile 'C:\vlastny testing profil'` musí smerovať na samostatné
miesto. Predvolený profil stabilnej aplikácie sa odmietne. Pridané nahrávky
sa nekopírujú ani nemažú; odobratie sa týka len fronty. Projekt sa otvára
cez SQLite backup do novej pracovnej kópie v testing profile. Ukladanie
mení iba túto kópiu cez existujúcu službu revízií. Originál zostáva zachovaný.
Testovací profil a kópie nie sú automaticky šifrované.

## Funkčný rozsah

- Trvalá fronta, pridanie/odobratie, otvorenie výsledku aj samostatného projektu.
- Virtualizovaný zoznam úsekov, editácia Unicode textu, Ctrl+S, ochrana pred
  zatvorením alebo otvorením iného projektu s neuloženým textom.
- Existujúci prehrávač a PCM cache; pauza, prehrávanie a posun po pôvodnej osi.
- Existujúci riadený ASR proces, CPU, jazyky/modely stabilného jadra, offline
  prepínač, stav a priebeh, potvrdenie zápisu stavu fronty, zastavenie.
- Svetlý/tmavý Material vzhľad, pomenované ovládanie, prístupný textový editor;
  spustenie/zastavenie/uloženie zostávajú v päte, nastavenia sa posúvajú.

Zámerne nejde o plnú paritu: chýbajú exportné dialógy, Undo/Redo, vyhľadávanie,
správa modelov, voľba GPU, zoskupovanie hlasov a podrobné dávkové odhady.
Prototyp UI je slovenský; stabilný EN/SK katalóg sa nemení. Bez zvuku sa dá
upravovať text, ale nie prehrávať. Úpravy sa ukladajú ako celá snímka vstupov
služby; veľké pracovné zoznamy a kopírovanie na hlavnom vlákne treba pred
migráciou optimalizovať. Prototyp nie je odporúčaný na jedinú kópiu práce.

## Merania a hranice dôkazov

Nástroj `scripts/benchmark_qml.py tk|qml --output outputs/vlastne-meranie`
meria čas od štartu Python skriptu po prvé spracovanie udalostí, pracovnú
sadu/private bytes cez Windows API a medzery obsluhy nečinného okna. Merania
sú bez modelov a bez používateľských dát; nejde o rýchlosť ASR ani záruku
latencie pod záťažou. Pamäť bola odčítaná po prepnutí tém/veľkostí v QML;
Tk meranie je nečinné hlavné okno, nie rovnocenný záťažový test celého editora.

| Meranie zo zdrojov | Tk | QML |
| --- | --- | --- |
| Štart, 2 následné behy Tk / 5 behov QML rôznych mierok | 0,876–0,994 s | 0,673–0,745 s |
| Pracovná sada | 48,45–48,46 MiB | 184,60–234,54 MiB |
| Private bytes | 27,09–27,11 MiB | 167,94–217,39 MiB |
| 95. percentil medzier nečinnej obsluhy (spánok 10 ms) | 10,93–11,13 ms | 10,80–11,04 ms |

Tieto malé teplé vzorky nie sú štatistický dôkaz rýchlejšieho štartu QML.
Výsledky závisia aj od vykresľovacieho backendu a DPI; prvé meranie pamäte
vrátilo neplatnú nulu pre chybný typ Windows handle a bolo vyradené. Nástroj
teraz kontroluje úspech API. Pri nekontrolovanom umiestnení okna sa menil
monitor a tým výsledný pomer DPI; finálny nástroj fixuje primárny monitor a
zaznamenáva `device_pixel_ratio`.

Na tomto Windows bol primárny monitor 125 %, druhý 100 %. QML faktory
0,8 / 1 / 1,2 / 1,4 / 1,6 na primárnom monitore dali skutočné pomery
1 / 1,25 / 1,5 / 1,75 / 2. Overené boli obe témy a malé/veľké okno,
vrátane snímok. Veľké okno pri vysokom DPI Windows obmedzil dostupnou
výškou monitora; nepredstierame fyzicky nedostupnú výšku 720 logických bodov.
Nešlo o zmenu systémového DPI ani úplný test presúvania medzi monitormi.

Automatické QML scenáre pokrývajú frontu a busy, kópiu projektu,
editáciu/uloženie/opätovné otvorenie/nezmenený originál, 10 000 úsekov bez
zvuku, obe témy/veľkosti, pauzu a posun, reálne klávesy vrátane medzery a
Ctrl+S, offline chybu v reálnom ASR procese a prístupnú rolu/názov editora.
To posledné potvrdzuje QAccessible EditableText, **nie funkčnosť Narratora**.
Samostatná praktická skúška prehrala syntetické ticho cez skutočný Windows
výstup: callback posúval čas, posun v pauze zachoval pauzu a počas prehrávania
pokračoval. Nešlo o posluchovú skúšku hlasu. V tejto úlohe nebola spustená
inferencia reálneho modelu/GPU ani sťahovanie váh.

Výsledok úplných povinných testov, auditov a balenia je viazaný na konkrétny
kandidátny commit; lokálne záznamy a build receipt zostávajú mimo Gitu.
Zlyhanie brány blokuje push, aj keď samostatné QML scenáre prejdú.

## Prístupnosť a balenie

Qt poskytuje explicitné Accessible.name a textovú rolu, klávesové ovládanie
používa štandardné Controls. Tk má oproti prototypu existujúce a širšie
regresné pokrytie prístupnosti. Praktické čítanie Narratorom, Windows vysoký
kontrast a IME nie sú v tomto experimente potvrdené. QML automaticky neznamená
prístupnejšiu aplikáciu.

Oba balíky používajú ten istý predpis jadra/ASR; QML pridáva Qt runtime a QML
pluginy. Nie je to optimalizované minimálne balenie. Veľkosť treba porovnať
súčtom súborov nových distribúcií, nie veľkosťou samotného EXE. Verejné vydanie
vyžaduje audit licencií presného balíka a dodanie príslušných oznámení.
PySide6 je dostupné pod LGPLv3/GPLv3/komerčnou licenciou; výber a povinnosti
konkrétnej distribúcie sa nesmú odvodzovať len z licencie vlastného kódu.

Primárne zdroje: [PySide6 Essentials](https://github.com/pyside/pyside-setup/blob/dev/README.pyside6_essentials.md),
[Qt for Python deployment](https://doc.qt.io/qtforpython-6/deployment/index.html).

Created by Daniel Návojský (ndxnraw) using Codex | 2026

### Zistenie pri prvom balení (30. 10. 2026)

Prvý QML EXE zlyhal pri importe QtWidgets. Potvrdenou príčinou bola nesprávna
ICU DLL získaná z cudzieho PATH, nie chýbajúci Python modul. `scripts/freeze.py`
pre obe zostavy obmedzuje vyhľadávanie na projektové prostredie, použitý
Python a systém Windows. Finálne overenie musí použiť celý nový build;
ručné vyradenie DLL bolo iba diagnostickým potvrdením príčiny. Setup QML
podporuje rovnaký voliteľný parameter `-Python` ako stabilný setup.

### Úspešná čistá zostava (30. 10. 2026, `819abd0`)

296 regresných testov / 299,738 s a 8 QML testov / 5,358 s: OK, bez skipov.
Tk aj QML EXE prešli kontrolou pribaleného kódu a reálnym spustením.
Nový balík už neobsahuje cudziu ICU DLL. Logické veľkosti celých priečinkov:
Tk **1 647 199 411 B**, QML **1 795 612 084 B**; QML pridáva približne
**142 MiB (9 %)**. Obe distribúcie obsahujú rovnaké veľké ASR runtime;
nejde o porovnanie komprimovaných archívov ani optimalizovaných balíkov.
