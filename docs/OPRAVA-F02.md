# F02 – dostupné ovládanie pri vysokom DPI

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Vývojový bod návratu: `F02-20261009`, verzia aplikácie zostáva **2.1.3b**.
Nejde o publikované vydanie. Zostava obsahuje aj predchádzajúce rozpracované opravy F01/F03/F04/F05/F06.

## Príčina a zmena

Karta Nahrávky pôvodne prideľovala výšku pevným riadkom pred tlačidlami spustenia a zastavenia. Pri veľkom písme a výške obmedzenej obrazovkou nezostal ovládaniu priestor. Dlhé stavové hlásenia problém zväčšovali; rozbalené voľby editora navyše prekračovali dostupnú šírku.

- Spustenie, zastavenie a otvorenie výsledkov majú rezervovaný spodný riadok karty Nahrávky.
- Nastavenia čakajúcich nahrávok sú na karte Nastavenia. Pri pridávaní je priamy odkaz „Nastavenia prepisu“. Hodnoty, ukladanie a blokovanie počas práce zostávajú zachované.
- Dlhé hlásenia a názvy sú v ohraničených textových oblastiach s posúvaním; úplný text sa nestráca a nevytlačí akcie mimo okna.
- Vedľajšie akcie fronty a rozbalené riadky editora sa zalamujú podľa šírky. Editor uvoľní úvodnú prázdnu plochu a používa kompaktnejšie medzery bez zmenšovania písma.
- Správca modelov rezervuje spodný riadok akcií pred zoznamom a dlhými správami. Oba vzhľady farbia aj nové textové oblasti.

Zmenené časti: `ui_layout.py`, `responsive.py`, `editor.py`, `model_dialog.py`, `ui.py`; regresná matica `test_dpi_layout.py`.

## Overovanie

Pôvodný `StudioScalingTest` zostal nezmenený. Nový test kontroluje päť kariet, oba vzhľady, rozbalené voľby editora, dlhý názov a viacriadkové chyby na virtuálnych obrazovkách 1366 × 768 a 1536 × 864 pri 100, 125, 150, 175 a 200 % mierke Tk. Kontroluje dostupnosť a hranice tlačidiel, vstupov a výberových polí aj zachovanie a posúvanie úplnej správy. Ide o simuláciu rozmerov a mierky Tk v natívnom Windows procese, **nie o zmenu systémového DPI Windows**.

Konečné počty testov, kontrola EXE a skutočne overené systémové scenáre sú v `OVERENIE.json` pri vývojovej zostave. Prenos okna medzi monitormi a všetkých päť fyzických nastavení systémového DPI vyžaduje osobitné manuálne overenie; automatická matica ich nedokazuje.

## Vývojová zostava a návrat

Priečinok `outputs/dev-F02-20261009` je oddelený od existujúcich vydaní. Použite `Spustit-vyvojovu-zostavu.cmd`: aplikácia dostane samostatný profil a neprevezme používateľskú frontu. Existujúce projekty otvárajte na skúšku z kópie. Pôvodné vydania ostávajú na svojich miestach.

Zdrojový archív zachováva aktuálne zdroje vrátane predošlých opráv. Kontrolné súčty a protokoly sú uložené pri zostave. Modely nie sú pribalené.
