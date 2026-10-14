# F05 – samostatný stav projektu a exportu

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Oprava z 9. októbra 2026. Verzia, používateľské dáta a nesúvisiace zmeny zostávajú
zachované; EXE ani vydanie sa nevytvárajú.

## Správanie editora

Uloženie vytvorí databázovú revíziu a v rovnakej transakcii zapíše požiadavku na
export vrátane profilu titulkov. Po úspešnom commite už editor nepovažuje text za
neuložený. Stav exportu zobrazuje samostatne. Chyba exportu nepredstiera chybu
zápisu projektu: dialóg vysvetlí, že uložené dáta zostali zachované, ukáže príčinu
a odporučí zatvoriť súbory, skontrolovať oprávnenia a voľné miesto.

**Zopakovať export** použije uloženú revíziu a jej nastavenia, nevytvorí novú
revíziu a nespúšťa zvuk ani ASR. Rozpísané neskoršie zmeny do opakovania nevstupujú;
tie treba najprv uložiť. Nedokončená požiadavka prežije zatvorenie a otvorenie
projektu. Po úspechu sa jej stav zmení na dokončený. Pri zlyhaní databázy zostávajú
úpravy neuložené a export sa nespustí.

## Konzistentná dvojica

`export_pair.py` pripraví oba súbory v novom jedinečnom priečinku
`exporty/<id>/`. Až po úspešnom zápise TXT aj SRT sa atómovo vymení súbor
`exporty/aktualny.opravene.json` (pre originál `aktualny.json`, pre priebežný
originál `aktualny.partial.json`). Tento manifest určuje publikovanú dvojicu.
Chyba pred jeho výmenou ponechá predchádzajúcu kompletnú dvojicu aktívnu.
Staršie generácie sa neprepisujú ani automaticky nemažú.

**Otvoriť export** načíta manifest a otvorí priečinok obsahujúci obe publikované
časti. To je odporúčaný spôsob prevzatia kompletnej dvojice po tejto oprave.

Kvôli kompatibilite sa naďalej aktualizujú aj súbory v hlavnom priečinku projektu.
Tieto kópie **nie sú atómová dvojica**. Ak je napríklad koreňový SRT zamknutý,
kompletná dvojica v `exporty/<id>/` je už dostupná, ale hlásenie jasne uvedie
neúspešnú aktualizáciu kópií a jej dôvod. Export zostáva označený ako nedokončený
a možno ho zopakovať. Nepoužívajte tieto kompatibilné kópie ako zdroj garantovanej
dvojice pri súbežnom čítaní alebo po chybe exportu.

## Súbory a overenie

- `project.py`: transakčná požiadavka na export, opakovanie a oddelený stav.
- `editor.py`: samostatné indikátory, presné chybové správy, opakovanie a otvorenie.
- `export_pair.py`: generácie a atómová publikácia cez manifest.
- `test_export_pair.py`: štyri testy vrátane viacerých chybových scenárov.

Overené sú odmietnutie zápisu (simulované EACCES), nedostatok miesta (simulované
ENOSPC), zamknutý manifest, skutočný Windows zámok SRT cez CreateFileW, zachovanie
predchádzajúcej dvojice, obnovenie požiadavky po otvorení projektu, opakovanie bez
novej revízie, otvorenie kompletnej dvojice a rozlíšenie chyby databázy od exportu.
Použité boli iba dočasné projekty. Žiadny reálny disk nebol zaplnený ani menené ACL
používateľských priečinkov. Testy F01 po oprave regresie dlhého stavového hlásenia
znovu prešli v oboch vzhľadoch.

Finálna celá sada: **115 testov, 114 úspešných**. Jediné zlyhanie zostáva známe
F02 pri 200 % mierke na karte Nahrávky. Cielená sada exportu a F01: **10/10**.
`git diff --check` bez chýb; existujúce upozornenia Tcl ThemeChanged pri rušení
testovacích okien zostávajú.

Spustenie s projektovými závislosťami a `src` na PYTHONPATH:

```text
python -m unittest test_export_pair test_editor_speakers -v
powershell -NoProfile -File scripts/test.ps1 -q
```

## Obmedzenia

Generácie a nepublikované priečinky po chybách zaberajú miesto; automatické čistenie
sa nepridávalo. Publikácia cez manifest garantuje výber kompletnej dvojice, nie
transakčnú výmenu dvoch samostatných kompatibilných názvov. Koordinácia viacerých
inštancií editora zostáva F06. Nešlo o nové overenie reálneho ASR ani zostaveného EXE.
