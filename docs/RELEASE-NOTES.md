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
Historické občasné blokovanie ASR stop udalosti je zaznamenané v STATUS;
úprava dokumentácie ho neopravuje ani nevyhlasuje za vyriešené.

Created by Daniel Návojský (ndxnraw) using Codex | 2026
