# Distribúcia Release v1

Hlavné vydanie je **Release v1 (1.0.0)**, QML/Qt Quick, Windows x64,
plný variant s faster-whisper aj podporou KInIT. Modelové váhy sa nepribaľujú.
[Stiahnutie](https://github.com/ndxnraw/TranskripThor/releases/tag/v1.0.0).
Súkromný repozitár vyžaduje prístup aj pri sťahovaní vydania.

Pred publikovaním sa zostaví presný commit z čistého klonu cez
`build.ps1 -OutputDirectory dist`. Všetky regresie a produkčné Qt scenáre
musia prejsť bez preskočenia. `package.py --release-tag v1.0.0` vyžaduje čistý
commit zhodný s overeným manifestom. `verify_distribution.py --startup`
overí SHA-256 každého člena ZIPu, rozbalí ho a spustí správny QML verifier.

Publikuje sa celý `ND-TranskripThor-v1-Windows-x64.zip` a jeho `.sha256`.
ZIP obsahuje úplný priečinok aplikácie vrátane `_internal`, licenčné texty,
verzie knižníc a build/distribution manifesty. Neobsahuje profil, nahrávky,
projekty, exporty, váhy, tokeny ani súkromné logy. Používateľovi stačí
rozbaliť celý archív a otvoriť EXE; Python sa neinštaluje.

Inventár licencií otvorene ponecháva nevykonané právne/čisté Windows
kontroly; zverejnenie Release v1 nie je tvrdenie o digitálnom podpise ani
úplnom právnom preverení. Binárka nie je digitálne podpísaná. Historické
odseky nižšie sa týkajú starších Tk kandidátov, nie aktuálneho rozhrania.

---

## Historický distribučný postup pred Release v1

# Windows distribučný kandidát – Pre-release

Tento postup nevytvára tag ani GitHub Release. Distribúcia používa stabilné
Tk rozhranie, nie experiment QML. Prenášajte celý rozbalený priečinok vrátane
`_internal`; Python sa používateľovi neinštaluje. Modelové váhy nie sú súčasťou
žiadneho variantu. Používateľský profil, projekty a nahrávky sa nepribaľujú.

## Dva samostatné varianty

V čistom klone s projektovým `.venv` pripraveným cez `scripts/setup.ps1 -Mode build`:

```powershell
.\scripts\build.ps1 -Variant extended
.\.venv\Scripts\python.exe scripts/package.py --app 'dist/ND TranskripThor' --output 'outputs/ND-TranskripThor-extended-candidate.zip'
.\scripts\build.ps1 -Variant basic
.\.venv\Scripts\python.exe scripts/package.py --app 'dist/basic/ND TranskripThor' --output 'outputs/ND-TranskripThor-basic-candidate.zip'
```

Oba buildy vykonajú celú povinnú sadu, audit pribalených zdrojov, skutočný
štart EXE a nový podproces. Extended zostáva predvolený a obsahuje PyTorch
a Transformers pre KInIT. Basic ich vylučuje; podporuje modely faster-whisper,
rovnaké projekty a exporty. KInIT v základnom balíku vyžiada rozšírený balík,
nenahrádza model potichu. Nainštalovanie samotného Pythonu tento balík nerozšíri.
Oba varianty zostávajú CPU zostavami; CUDA runtime/GPU inferencia nie sú týmto
overené. Nezamieňajte dostupnú voľbu GPU s pribalenou kompletnou CUDA distribúciou.

ZIP vzniká až po overení `build-manifest.json`; zmena zdrojov, prostredia alebo
runtime súborov vyžaduje nový build. Obsahuje tiež `distribution-manifest.json`
s veľkosťou a SHA-256 každého zabaleného súboru vrátane oznámení. Vedľa ZIP je
`.sha256` pre celý archív. Kontrola CRC ZIP nenahrádza overenie jeho pôvodu.
Balík je kandidát a manifest výslovne neprehlasuje podpis ani schválenie vydania.

Licencie sa zbierajú do dočasného priečinka, pôvodná overená zostava sa nemení.
`LICENCIE/inventory.json` je širší súpis runtime locku, nie presný binárny SBOM:
v basic môže uvádzať aj nepoužité závislosti KInIT. Qt sa do Tk balíkov nepribaľuje.
Skript zachová LICENSE, COPYING aj NOTICE, licenciu Pythonu a dostupné Tcl/Tk
oznámenia. Doplnkové pôvodné texty majú URL a SHA-256 v `sources.json`.

## Namerané kandidáty (2. 11. 2026, c354e72)

| Variant | ZIP | Rozbalený obsah vrátane oznámení |
|---|---:|---:|
| Basic | 118 719 868 B (113,22 MiB) | 277 320 004 B (264,47 MiB) |
| Extended | 438 054 866 B (417,76 MiB) | 1 651 406 268 B (1,54 GiB) |

Odporúčam dva úplné prenosné ZIP balíky: basic ako menšie stiahnutie a
extended pre používateľov KInIT. Vyhneme sa ručnej inštalácii Pythonu alebo
kopírovaniu DLL doplnku. Oba používajú rovnaký profil/projekty; nespúšťajte ich
s tým istým profilom súčasne. Predvolený vývojový build zostáva extended.
Modely a disková PCM cache potrebujú ďalšie miesto mimo uvedených veľkostí.

Pre tento SHA prešlo 301 testov v každom builde, audit 65 modulov a model-free
EXE smoke. Oba ZIP sa rozbalili do izolovaného Unicode priečinka a ich EXE
prešli štartom s PATH bez Pythonu. Nejde o reálny ASR/GPU test ani čistú VM.
Veľkosti a výsledky sú historické meranie konkrétneho kandidáta, nie garancia
každého budúceho zostavenia. Kontrolné súčty konkrétneho ZIP sú v jeho sidecare.

## Licenčné otvorené položky pred verejným vydaním

Kandidát nie je vyhlásením kompletného právneho preverenia. Aktuálny PyAV wheel
obsahuje FFmpeg: načítaná `avcodec_license()` hlási **LGPL version 3 or later**.
Pribalené LGPLv3/GPLv3 texty nenahrádzajú presný zodpovedajúci zdroj, zostavovací
predpis a oznámenia jeho natívnych závislostí. Pred publikovaním zabezpečte
zodpovedajúce zdroje a overte podmienky konkrétnej binárnej zostavy podľa
[FFmpeg](https://ffmpeg.org/legal.html). Nepredpokladajte, že licencia PyAV
pokrýva všetky DLL. Inventár tieto otvorené povinnosti nezakrýva.

Repozitár neurčuje samostatnú distribučnú licenciu aplikácie; jej podmienky musí
určiť autor. Licencie modelov sa týkajú osobitne stiahnutých váh a nie sú právom
na ich automatické pribalenie. Tento kandidát žiadne váhy neobsahuje.

## Skúška bez Pythonu

Automatický `verify_exe.py` spúšťa EXE z cudzieho pracovného priečinka, s PATH
obmedzeným na Windows/System32 a Windows, bez PYTHONHOME/PYTHONPATH a user-site.
Overuje vlastný pribalený runtime, Tk/tkdnd, exporty, audio filter a spawn.
Toto je izolácia vyhľadávania, **nie test na počítači bez nainštalovaného Pythonu**.

Na čistom Windows x64 VM bez Pythonu rozbaľte ZIP, overte SHA-256 a spustite EXE
ako bežný používateľ. Overte prvé otvorenie, Unicode súbory, prepis po stiahnutí
Tiny, export, zatvorenie a opätovné offline otvorenie. Extended navyše potrebuje
reálny KInIT test. Uchovajte verziu OS, checksum a výsledky. Ak chýba Microsoft
VC++ runtime, inštalujte oficiálny redistribučný balík; nekopírujte náhodné DLL.
Nenahrávajte profil ani testovací zvuk do zdrojového repozitára.

## Podpisovanie

Dňa 2. 11. 2026 sa v CurrentUser/My ani LocalMachine/My nenašiel dostupný
Code Signing certifikát. Nič sa nepodpisovalo a nevytvára sa náhradný self-signed
certifikát. Na stroji nebol nájdený ani SignTool v PATH.

Po získaní skutočného certifikátu použite jeho presný thumbprint a timestamp URL
poskytovateľa cez Windows SDK SignTool, podľa
[Microsoft dokumentácie](https://learn.microsoft.com/windows/win32/seccrypto/signtool):

```powershell
signtool sign /sha1 CERTIFICATE_THUMBPRINT /s My /fd SHA256 /tr TIMESTAMP_URL /td SHA256 'ND TranskripThor.exe'
signtool verify /pa /all /v 'ND TranskripThor.exe'
```

Nepíšte heslo PFX do skriptu ani Gitu. Podpis mení EXE, preto existujúci manifest
a ZIP po podpísaní nie sú platné. Táto unsigned kandidátska cesta podpisovanie
neautomatizuje: pre podpísané vydanie zaraďte podpis po freeze a pred audit/štart
a vytvorením build manifestu, zaznamenajte overený thumbprint/timestamp do
distribučného manifestu a až potom vytvorte nové checksumy. Nevypínajte kontrolu
manifestu ani neoznačujte starý kandidát ako podpísaný.

Kontrola hotového ZIP vrátane rozbalenia do dočasného priečinka a štartu EXE:

```powershell
.\.venv\Scripts\python.exe scripts/verify_distribution.py 'outputs/ND-TranskripThor-basic-candidate.zip' --startup
```

Kontrola overí SHA-256 archívu, presný zoznam položiek, veľkosť a SHA-256
každého súboru. Odmietne duplicitné/nebezpečné cesty pred rozbalením.

Created by Daniel Návojský (ndxnraw) using Codex | 2026
