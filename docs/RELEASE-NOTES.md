# ND TranskripThor — Release v1

**1.0.0 · Windows x64 · QML/Qt Quick · tag `v1.0.0`**

[Stiahnuť vydanie](https://github.com/ndxnraw/TranskripThor/releases/tag/v1.0.0)

QML je od tohto vydania hlavnou aplikáciou. Pridanie nahrávok, jazyk,
kvalita a spustenie sú na jednej obrazovke bez kariet. Chýbajúce súbory
modelu sa pripravia automaticky; správcu modelov netreba navštíviť vopred.
Offline režim vyžaduje výslovný súhlas pred povolením sťahovania.

Zachované sú faster-whisper aj slovenský KInIT, pôvodné profily a projekty,
checkpointy a obnovenie prepisu. Editor ponúka prehrávanie, Unicode hľadanie,
Undo/Redo, hovoriacich, delenie/spájanie a časy úsekov, titulky a export
TXT/SRT/VTT/DOCX/JSON. Neuložené zmeny chráni pri zatvorení aj zmene projektu;
novšie úpravy počas ukladania zostanú neuložené. Originál zostáva nemenný.

Svetlá/tmavá téma, vysoký kontrast Windows, správa modelov a diagnostika
majú QML rozhranie. Tk a staršie prototypy zostávajú v zdrojoch pre historické
regresie a výslovné experimenty; bežné spustenie a zostavenie používajú QML.

Rozbaľte celý ZIP vrátane `_internal` a spustite **ND TranskripThor.exe**.
Python sa neinštaluje. Modelové váhy, nastavenia, nahrávky a projekty nie sú
pribalené. Overte priložený `.sha256`; balík nie je digitálne podpísaný.
Súkromný repozitár vyžaduje prihlásenie a oprávnenie aj pre stiahnutie.

Aktuálne výsledky presného vydania a kontrolný súčet sú pri GitHub Release.
Predchádzajúca QML implementácia prešla 338 regresiami a 20 Qt scenármi;
large-v3 na CPU reálne prepísal vlastný syntetický zvuk a uložil opravu bez
zmeny originálu. Tieto predchádzajúce dôkazy nenahrádzajú finálny release build.
Reálna KInIT/CUDA inferencia, čistý Windows bez Pythonu, čítačka obrazovky,
fyzické DPI a presnosť na referenčnom CZ/SK korpuse nie sú týmto potvrdené.

[Návod](NAVOD.md) · [Stav a overenie](STATUS.md) · [Vývoj](DEVELOPMENT.md)

---

## Historické poznámky pred Release v1

# ND TranskripThor — poznámky k pre-release

Stav dokumentácie: **28. 10. 2026**, vývojová línia **Pre-release**.
Interná verzia kompatibility `2.1.3b` a Windows `2.1.3.1` ostávajú nezmenené.
Tieto poznámky nie sú oznámenie nového GitHub Release ani nového ZIP na stiahnutie.
Archívne vydania môžu mať menej funkcií než aktuálne zdroje.

## Implementovaný stav

- Windows x64, lokálny faster-whisper (Tiny/Small/Medium/Large v3) a voliteľný
  slovenský KInIT. SK, CS, EN, HU, automatická detekcia a osobitný CZ/SK režim.
  Predvolené CPU; CUDA sa vyberá manuálne a fallback vyžaduje súhlas.
- Trvalá fronta, izolovaný ASR proces, bezpečné checkpointy a opakovanie
  prípravy po skorom prerušení. Obnova rešpektuje obsah zvuku, presnú revíziu
  modelu a efektívne nastavenia. Nový prepis neprepisuje predchádzajúci projekt.
- Projekt možno otvoriť mimo fronty a text upravovať bez zvuku. Náhradná
  nahrávka musí zodpovedať uloženému odtlačku. Originál je oddelený od revízií;
  pri migrácii sa nevytvára falošný originál.
- Editor: vyhľadávanie jednotlivých výskytov, Undo/Redo, hlasy, delenie,
  spájanie a časy úsekov; prehrávanie so zariadením a rýchlosťami.
- Uloženie projektu a export sú oddelené. Export originálu alebo uloženej
  revízie do TXT/SRT/VTT/DOCX/JSON tvorí konzistentný samostatný balík.
  Titulkový profil sa uchováva; nepresné časovanie sa neskrýva.
- Modelový inventár, explicitná integrita, obnoviteľné sťahovanie a offline
  chyby. Modely nie sú pribalené. Zoskupovanie hlasov je voliteľné.
- EN predvolene, SK po reštarte, svetlý/tmavý vzhľad. Prehľad dát a náhľad
  diagnostického ZIP bez zvuku/prepisov. Lokálne súbory nie sú automaticky šifrované.

Podrobné postupy: [návod](NAVOD.md). Zostavenie a presné závislosti:
[DEVELOPMENT.md](DEVELOPMENT.md). Chronologické overenia: [STATUS.md](STATUS.md).

## Overené merania a ich hranice

| Dátum / stav zdrojov | Overenie |
| --- | --- |
| 28. 10. 2026, Pre-release, commit `29b327e` (úloha 28) | Čistý klon: 291 testov, 251,418 s, bez chýb/preskočenia. Nové Windows EXE, zhoda 65 modulov, izolovaný frozen štart PASS. Toto nie je výsledok každého budúceho commitu. |
| 28. 10. 2026, Pre-release, úloha 28 | Skutočný Tiny CPU, vlastná syntetická SAPI nahrávka: 2 úseky, 2,578 s. Žiadne Python sieťové pokusy; 42 TCP vzoriek vlastného procesu bez spojenia. Nie packet capture, UDP ani test KInIT/GPU. |

Minimum 197 testov je povinná dolná hranica zostavovania, nie údaj o počte
aktuálnych testov. Konkrétny beh musí dokončiť všetky objavené testy bez skipov.
Historické poznámky OPRAVA/VERZIA a audit sa týkajú svojho vtedajšieho stavu;
staré cesty a tvrdenia „nepublikované“ nie sú dnešný návod ani stav vydania.

## Známe obmedzenia

Chýba oprávnený reálny referenčný korpus pre úplné meranie kvality. CZ/SK zmena
uprostred úseku môže zostať nerozpoznaná. Zoskupovanie podobných hlasov nie je
identifikácia osôb ani presné oddelenie prekryvov. Veľké modely potrebujú RAM/VRAM;
PCM cache potrebuje miesto na disku. Pri ručných opravách nemožno predstierať
presné časy slov. ETA je iba odhad. Starší projekt môže mať nenávratne stratený
originál. Staršie aplikácie nemusia otvoriť novú schému; uchovajte migračnú zálohu.

Automatická Tk matica nie je plné overenie Windows DPI, Narratora, systémového
pretiahnutia z Prieskumníka ani fyzického odpojenia zvukového zariadenia.
F30 (29. 10. 2026) nahrádza zámkový ASR stop signál jednosmerným zdieľaným
príznakom, aby pád procesu nezablokoval jeho zastavenie. Rozsah regresií
a výsledky konkrétneho kandidáta sú v STATUS; nejde o meranie presnosti ASR.

Created by Daniel Návojský (ndxnraw) using Codex | 2026
