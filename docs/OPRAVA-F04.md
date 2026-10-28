# F04 – originál, pracovný text a uložené revízie

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Oprava z 8. októbra 2026; bez zmeny verzie, zostavenia EXE alebo publikovania.

## Ukladanie a export

`project.py` ponecháva tabuľku `segments` ako pracovný text editora. Nová tabuľka
`original_segments` dostáva výsledok modelu v rovnakej transakcii ako checkpoint.
Uloženie opravy ju nemení. `transcript_revisions` uchováva celé snímky uložených
úprav s ID a časom uloženia. Databázové triggery blokujú aktualizáciu a mazanie
originálnych segmentov a revízií. Pokračovanie pridáva nové výsledky modelu do
originálu aj pracovného textu; skoršie opravy a revízie zostávajú zachované.

Produkčné volania exportu sú explicitné:

- `jobs.py`: `export(view='original')` pri dokončení, prerušení aj opakovaní exportu.
- `editor.py`: `edit(...)` vráti ID uloženej revízie; následne
  `export(options, view='revision', revision=id)` vytvorí opravené TXT/SRT.
- Čítanie konkrétnej revízie: `segments('revision', id)`. Čítanie originálu:
  `segments('original')`. Predvolené `segments()` vracia pracovný text.

Pôvodné názvy súborov zostávajú: `prepis.txt`, `titulky.srt`, ich `.partial`
varianty a opravené `.opravene` exporty. Staré volanie `export()` bezpečne znamená
originál; kompatibilné `corrected=True` vyberá poslednú uloženú revíziu. Nové
volanie s `view='revision'` vyžaduje konkrétne ID. História revízií zostáva v
databáze aj po prepísaní opravených exportov exportom inej zvolenej revízie.

## Migrácia a záloha

Pri prvom otvorení existujúceho projektu sa vytvorí jedinečný priečinok
`zaloha-pred-reviziami-<id>` v jeho priečinku. Obsahuje konzistentnú SQLite zálohu
(vrátane potvrdených dát vo WAL) a kópie existujúcich `prepis*.txt` a `titulky*.srt`.
Záloha databázy prejde `quick_check`. Súbor `ZALOHA-DOKONCENA.txt` vznikne až po
úspešnom zálohovaní. Zlyhanie zálohy zabráni migrácii; neúplný záložný priečinok
sa automaticky nemaže. Zálohy sa neprepisujú.

Migrácia prebehne v jednej transakcii pod zámkom zápisu. Pri chybe alebo páde
procesu zostáva staré úložisko a ďalšie otvorenie môže migráciu zopakovať. Nové
úložisko má vlastnú verziu, pôvodná schéma checkpointov ostáva kompatibilná.

Staré projekty neukladajú dôkaz, či ich segmenty už niekto opravil. Ich existujúci
text preto prejde do pracovných dát a prvej revízie, **nie do falošného originálu**.
Stav `original_unknown` sa zachová aj po pokračovaní a uložení nových úsekov.
Editor ho viditeľne uvádza. Export originálu v tomto stave vráti upozornenie
do podrobností spracovania a existujúce pôvodné TXT/SRT ponechá nedotknuté.
Prázdny starý projekt bez checkpointov možno bezpečne začať plniť novými výsledkami.

Na manuálne obnovenie najprv zatvorte aplikáciu, zachovajte celý aktuálny projekt
a vytvorte samostatný priečinok z dokončenej zálohy. Záloha predstavuje stav pred
migráciou, preto ju nová aplikácia pri otvorení znovu migruje. Neprepisujte živú
databázu pri spustenej aplikácii. Pôvodná nahrávka sa do zálohy nekopíruje.

## Overenie

Osem nových testov v `test_originals.py` prešlo: oddelené revízie a originál,
opakovaný export dokončenej úlohy, chyba SRT a opakovanie, pokračovanie po oprave,
záloha a idempotentná migrácia, zlyhanie zálohy, rollback transakcie, násilné
ukončenie podprocesu pri migrácii a záloha potvrdených WAL dát.

Celá sada pred doplnením posledných dvoch scenárov: **109 testov, 108 úspešných**;
jediné zlyhanie je známe F02 pri 200 % škálovaní. Finálne cielené overenie:
**21/21 úspešných** (F04, F03 a F01). `git diff --check` bez chýb.

S projektovými závislosťami a `src` na PYTHONPATH:

```text
python -m unittest test_originals test_preparation test_editor_speakers -v
powershell -NoProfile -File scripts/test.ps1 -v
```

Testy používajú dočasné projekty. Databázy, exporty, zálohy a pád podprocesu sú
skutočné, ASR pri pokračovaní je simulované. Existujúce používateľské projekty
neboli hromadne migrované ani použité na testovanie.

## Zostávajúce obmedzenia

- Stratený starý originál nemožno spätne spoľahlivo odvodiť z upraveného textu
  alebo starých TXT/SRT. Ich obsah sa uchová, ale jeho pôvod sa nepredstiera.
- Revízie sú celé snímky a zaberajú miesto podľa veľkosti prepisu a počtu uložení.
  UI zatiaľ nemá prehliadač histórie; konkrétnu revíziu možno vybrať programovým API.
- Dvojica TXT/SRT sa stále zapisuje atómovo iba po jednotlivých súboroch (F05).
  Pri chybe exportu je uložená revízia bezpečná a originál nedotknutý, ale dvojica
  opravených exportov môže byť do opakovania neúplná.
- Súbežný zápis zo staršej aplikácie alebo externého procesu nie je vyriešením F06.
  Staršiu aplikáciu nepoužívajte na úpravy už migrovaného projektu.
