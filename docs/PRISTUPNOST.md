# Klávesnica a prístupnosť

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Zmena nadväzuje na opravy F01–F06, responzívne rozloženie a lokalizáciu. Verzia ostáva 2.1.3b; nejde o publikované vydanie. Používateľské profily a projekty sa nemigrujú.

## Ovládanie

| Kontext | Klávesy | Výsledok |
| --- | --- | --- |
| Rozhranie | Tab / Shift+Tab | Ďalší / predchádzajúci dostupný prvok. Textové polia prepisu a správ nepohltia Tab. |
| Pracovné karty | Ctrl+Tab / Ctrl+Shift+Tab | Ďalšia / predchádzajúca karta; funguje aj z textu. |
| Editor | Ctrl+S | Existujúce uloženie projektu a export TXT/SRT; pôvodné ošetrenie chýb ostáva zachované. |
| Editor | Ctrl+F, potom Enter | Fokus do vyhľadávania, výber dotazu; Enter filtruje úseky. |
| Editor | F3 / Shift+F3 | Ďalší / predchádzajúci zodpovedajúci úsek (nie jednotlivé výskyty v jednom úseku). |
| Editor | Alt+Down / Alt+Up | Prechod medzi úsekmi aktuálneho filtra, vrátane hranice stránok; rozpísaný text sa zachytí. |
| Editor | F6 | Fokus do aktívneho textu, prípadne otvorenie prvého úseku. |
| Blok prepisu | Enter | Otvorenie textu na úpravu. Fokusovaný blok má kontrastné zvýraznenie a automaticky sa posunie do zobrazenia. |
| Editor mimo vstupných polí | F7 / F8 | Prehrať vybraný úsek / pokračovať alebo pozastaviť. V Text, Entry, Combobox a Spinbox sa ignorujú. |
| Posuvník zvuku | Left / Right | Posun o 5 sekúnd, ohraničený dĺžkou nahrávky; zachováva pauzu. |

Medzera nemá globálnu väzbu na prehrávanie. V texte píše medzeru, na tlačidle zachováva štandardnú aktiváciu. Skratky editora sú viazané iba na jeho vlastné prvky; uloženie zo skrytej karty sa nespustí. Bežné šípky zostávajú dostupné pre pohyb kurzora. Nápoveda je dostupná v Settings/Nastavenia → Keyboard shortcuts/Klávesové skratky, v oboch jazykoch.

Tlačidlá prehrávania a presúvania už mali textové názvy vedľa ikon; zachovali sa. Vyhľadávanie má navyše viditeľný popis. Názov viditeľný v Tk nie je dôkazom dostupného názvu v UI Automation.

## Kontrast

Bežné témy ostávajú zachované. Pri zapnutom vysokom kontraste aplikácia číta `SPI_GETHIGHCONTRAST` a `GetSysColor`, použije systémové farby a namiesto obrázkových pozadí obnoví natívne rozloženie ttk ovládania. Stav sa kontroluje pri použití témy a návrate fokusu do hlavného okna. Nastavenia Windows sa nemenia. Postup vychádza z [dokumentácie Microsoft](https://learn.microsoft.com/en-us/windows/win32/winauto/high-contrast-parameter).

Test kontrastu kontroluje minimálne 4,5 : 1 pre text na ploche a paneloch, vedľajší text a text hlavného tlačidla v oboch témach. Nejde o úplný audit WCAG všetkých stavov ani o overenie individuálnej systémovej kontrastnej témy.

## Rozsah overenia

Celá regresná sada: **140 testov, OK, 135,248 s** (`work/tests-accessibility-final.log`). Posledné drobné úpravy kontrastu fokusu hlavného tlačidla a obnovenia titulkového pruhu navyše overilo **7 cielených testov, OK, 12,404 s** (`work/tests-accessibility-last.log`). Existujúca matica oboch jazykov, vzhľadov a Tk mierok 100/125/150/175/200 % zostala zachovaná. `git diff --check` prešiel. Pri rušení testovacích Tk okien sa naďalej objavujú pôvodné diagnostické hlásenia `ThemeChanged`; nie sú zlyhaním testu.

Nový `test_accessibility.py` používa skutočné Tk okná s oddelenými profilmi a synteticky doručené klávesové udalosti. Kontroluje navigáciu cez hranicu stránky so zachovaním textu, uloženie, vyhľadávanie, izoláciu skrytého editora, Tab v oboch smeroch, Ctrl+Tab, bežné písanie medzery, blokovanie prehrávania v poliach, posun zvuku počas pauzy, fokus bloku, farebné pomery a návrat zo simulovanej systémovej palety do bežnej témy. Zvukový výstup je v týchto testoch nahradený; nejde o posluchovú skúšku.

Praktická kontrola 12. 10. 2026 cez vstupy Windows a snímky zdrojovej aplikácie: Ctrl+F presunul kurzor do hľadania, F6 ho vrátil do textu, Tab zvýraznil nasledujúci úsek, Enter ho otvoril, Ctrl+S skončil hlásením úspešného TXT/SRT exportu. Editor bol vizuálne prezretý v tmavom aj svetlom vzhľade v angličtine pri aktuálnom systémovom DPI; ďalšie jazykové/DPI kombinácie pokrýva automatická matica, nie táto vizuálna skúška. Použitý bol iba profil `work/accessibility-visual/profile` a kópia testovacieho projektu. Existujúce EXE nebolo nahradené; nová zostava nebola vytvorená ani publikovaná.

Kontrola dostupného stromu UI Automation ukázala hlavnú časť editora prevažne ako nepomenované panely bez textu úsekov a názvov ovládania. Toto je **potvrdené obmedzenie tohto Tk runtime**, nie dôkaz úspešného čítania Narratorom. Narrator samotný nebol spustený ani posluchovo overený. Zlepšenie klávesnice túto bariéru čítačky samo neodstraňuje; jej plné riešenie vyžaduje ďalšiu prácu na dostupnom poskytovateľovi ovládacích prvkov.

Zmenené časti: nový `accessibility.py`, väzby a posun v `editor.py`, fokus blokov v `transcript_blocks.py`, témy v `ui.py`, navigácia/nápoveda v `ui_layout.py`, textové správy v `responsive.py`, systémová paleta v `model_dialog.py`, oba katalógy `locales`, nové testy a tento dokument. Nová externá závislosť nie je potrebná.

### Zostávajúce limity

- Canvas/ttk/Tk editor nemá vlastného poskytovateľa UI Automation. Úplnú kompatibilitu s Narratorom nemožno odvodiť z úspešných klávesových testov.
- Čítanie názvov, textu, kurzora, výberu a oznamovanie dynamických stavov Narratorom vyžaduje manuálnu skúšku na konkrétnom Windows/Tk. Nie je deklarovaná certifikovaná podpora čítačky.
- Skutočné systémové kontrastné témy a zmeny DPI medzi monitormi neboli zapínané. Simulácia systémovej palety a matica mierok Tk tieto skúšky nenahrádzajú.

Manuálny postup: na oddelenom profile otvoriť kópiu testovacieho projektu, prejsť karty a editor iba Tab/Shift+Tab, otvoriť úsek Enterom, napísať text s medzerami, vyhľadať, zmeniť úsek, uložiť a overiť export. S používateľom zapnutým Narratorom overiť ohlasovanie názvov, časových značiek a editovaného textu. V každej systémovej kontrastnej téme skontrolovať text, výber, fokus, vypnuté tlačidlá, ponuky a dialógy; zopakovať v EN/SK a pri 100–200 % systémového DPI.
