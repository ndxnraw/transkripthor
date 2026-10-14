# F07 — titulkový profil projektu

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

## Zistenie a oprava

Pred opravou editor vždy zobrazil 42 znakov, 2 riadky a časy 1–7 s. Predchádzajúca oprava exportu už zapisovala zvolený profil do `editor_export.options`, ale editor ho neobnovoval a zmeny polí neoznačoval ako neuložené.

`Project.subtitle_options()` teraz načíta projektové `subtitle_options`. Pri starších projektoch bez tejto položky použije existujúce `editor_export.options`; až ak nie je uložené ani jedno, použije predvolené `SubtitleOptions()` (42 / 2 / 1–7 s). Otvorenie staršieho projektu samo neprepisuje metadata. Pri najbližšom uložení sa profil zapíše spolu s opravami a požiadavkou exportu v jednej databázovej transakcii. Chybné uložené hodnoty sa neticho nenahrádzajú iným profilom; validácia odmietne ich použitie.

Nový projekt si pri inicializácii uloží vlastnú kópiu predvolených hodnôt. Zmena profilu jedného projektu nemení predvoľby ani iné projekty. Volanie `Project.edit()` bez explicitného profilu zachová existujúci profil. Dokončené exportné revízie ani pôvodné výsledky modelu sa touto zmenou neupravujú.

Editor obnoví všetky štyri polia a až potom zapne sledovanie zmien. Úprava ktoréhokoľvek poľa nastaví stav neuložených zmien aj bez vybraného úseku. Validácia prebieha pri uložení, aby bolo možné dočasne vymazať číslo pri písaní. Neplatná hodnota zabráni uloženiu a pri voľbe „uložiť pred zatvorením“ aj zatvoreniu. Možnosti zrušiť zatvorenie a zahodiť neuložené úpravy zostávajú zachované. Návrat na pôvodnú hodnotu nemusí sám zrušiť príznak neuložených zmien; je konzervatívny rovnako ako pri texte.

Po úspešnom zápise databázy je profil uložený aj pri zlyhaní exportu. Opakovanie exportu používa profil uloženej revízie, nie práve rozpísané hodnoty polí.

## Overenie

Nový `test_subtitle_profile.py` obsahuje šesť regresných testov: zmena každého poľa bez výberu úseku, uloženie pri zatvorení a opätovné otvorenie, nezávislé predvoľby nového projektu, zrušenie/zahodenie/neplatný vstup, kompatibilita staršieho projektu s profilom aj bez neho, zlyhanie exportu a návrat transakcie pri chybe. Testy používajú dočasné profily a projekty, nie používateľské dáta.

Cielená sada spolu s testami exportu a ochrany originálu: **18 testov, OK (6,405 s)**. Testy editora bežia v natívnom Tk na Windowse s nahradeným načítaním zvuku a odpoveďami dialógov; nejde o manuálnu vizuálnu skúšku ani nový ASR test.

Celá regresná sada 13. 10. 2026: **146 testov, OK (99,482 s)**, záznam `work/tests-f07-full.log`. Zahŕňa existujúce testy obnovy, exportov, lokalizácie, klávesnice a DPI rozloženia. `git diff --check` prešiel. Pôvodné upozornenia Tcl `ThemeChanged` pri rušení testovacích okien zostávajú; nejde o neúspešné testy.

Zmenené sú `project.py`, `editor.py`, nový test a tento dokument. Bez nových závislostí, bez zvýšenia verzie, bez prestavby EXE a bez publikovania. Oprava nemení algoritmus delenia titulkov ani jeho časové obmedzenia F08.
