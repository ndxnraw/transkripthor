# F08 — kontrola výsledných titulkov

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

## Potvrdený stav pred opravou

Export neodovzdával dĺžku zvuku do titulkového modulu. Krátky posledný titulok zostával bez upozornenia, čiastočné prekryvy sa potichu skracovali a chýbala kontrola výsledného počtu riadkov a trvania. Zalamovanie podľa spojovníkov navyše mohlo vložiť medzeru do pôvodného slova pri opätovnom spojení riadkov.

## Správanie po oprave

- `Project.export()` odovzdáva dĺžku z uloženého počtu dekódovaných vzoriek a existujúcej frekvencie 16 kHz. Nie je potrebné znova dekódovať zvuk. Profil F07 zostáva zachovaný.
- `cues()` a `render_srt()` majú voliteľný pomenovaný parameter `audio_duration`. Staršie priame volania zostávajú platné, ale bez dĺžky dostanú upozornenie, že koniec zvuku nemožno overiť; posledný titulok sa vtedy nepredlžuje.
- Výsledné intervaly sa najprv prevedú na milisekundy. Koniec zvuku sa zaokrúhli nadol, aby publikovaný čas nikdy neprekročil známy koniec. Nulové intervaly po zaokrúhlení sa odmietnu. Minimálna dĺžka sa pri možnom predĺžení zaokrúhli nahor na celú milisekundu.
- Krátky titulok možno predĺžiť iba do začiatku ďalšieho alebo do známeho konca zvuku. Ak priestor nestačí, upozornenie obsahuje číslo titulku, skutočné trvanie a požadované minimum.
- Prekryvy a nesprávne poradie výsledných milisekundových intervalov sa odmietnu bez skracovania reči. Úsek za koncom zvuku sa tiež odmietne. Chyba nastane pred publikovaním novej dvojice TXT/SRT; existujúce exporty a uložený projekt ostávajú zachované.
- Mäkké limity maximum trvania, počet riadkov a dĺžka riadku sa kontrolujú na konečnom výstupe. Každé upozornenie uvádza konkrétny titulok, nameranú hodnotu a limit.
- Delenie na viac titulkov používa iba použiteľné a textovo zhodné časy slov. Pri chýbajúcich, chybných alebo po úprave neplatných časoch zostáva celý text v pôvodnom úseku; neodhadujú sa časy nových slov. Príliš dlhé nedeliteľné slovo zostáva celé vrátane spojovníkov. Zalomenie mení iba biele znaky, nie slová.
- Nové hlásenia sú v anglickom aj slovenskom katalógu. Pri dávkovom prepise idú existujúcou cestou do podrobností spracovania, v editore do stavovej správy po exporte. Chyby používa existujúci exportný dialóg.

## Overenie a rozsah

`test_subtitle_validation.py` pridáva desať skúšok: krátky posledný titulok aj voľný priestor na predĺženie, hranica ďalšieho titulku, chýbajúce/neplatné/staré časy slov, dlhé spojovníkové slovo, delenie podľa platných slov, čiastočný aj úplný prekryv a poradie, hranice zvuku, milisekundové zaokrúhlenie, neznáma dĺžka a oba jazyky, projektový export a zachovanie predchádzajúceho exportu pri chybe.

Cielená sada titulkov, existujúcich funkcií a katalógov: **34 testov, OK (2,204 s)**. Existujúci test v `test_v2.py` mal úsek 1–3 s, ale iba 100 vzoriek zvuku; jeho deklarovaná nahrávka a plán boli opravené na 48 000 vzoriek. Kontroly textu, originálu a časov zostali zachované.

Testy F03 v `test_preparation.py` očakávajú pri 0,9-sekundovom poslednom titulku v šesťsekundovej nahrávke nové bezpečné predĺženie zobrazenia na jednu sekundu. Navyše explicitne kontrolujú, že pôvodný koniec ASR úseku v databáze zostal 1,0 s; iba koniec zobrazenia SRT je 1,1 s. Prvé spustenie celej sady odhalilo 11 zlyhaní tejto jednej spoločnej starej kontroly, nie stratu úsekov pri obnove.

Diagnostika ďalšieho behu odhalila čakanie na natívny chybový dialóg v teste editora: `test_ui_v2.py` obsahoval 1 501 úsekov do 3 001 s pri deklarovaných 500 000 vzorkách (31,25 s). Dĺžka jeho syntetickej nahrávky je teraz správne 3 001 × 16 000 vzoriek. Test navyše odmietne neočakávaný exportný dialóg výnimkou a overuje dokončený export, takže sa na ňom už nemôže neobmedzene čakať. Samostatná skúška prešla (0,684 s). Skorý pomocný diagnostický spúšťač bol tiež opravený o ochranu vstupného bodu potrebnú pre Windows multiprocessing; ide iba o súbor vo `work`, nie zmenu aplikácie.

Skúšky používajú malé syntetické segmenty a dočasné projekty. Nejde o meranie ASR ani manuálnu kontrolu čitateľnosti titulkov pri prehrávaní. Bez spoľahlivých časov slov nemožno zaručiť všetky mäkké limity súčasne; aplikácia to teraz oznamuje. Pri odmietnutom prekryve je potrebné opraviť časové dáta, nie automaticky zahodiť text.

Záverečná kompletná sada 13. 10. 2026: **156 testov, OK (111,688 s)**, záznam `work/tests-f08-complete.log`. Zahŕňa existujúce obnovovanie projektov, ochranu originálu, exporty, F07, lokalizáciu, klávesnicu a rozloženie. `git diff --check` prešiel. Log obsahuje aj diagnostický výpis zásobníka po 60 sekundách (priebežná diagnostika dlhého behu, nie zlyhanie) a pôvodné hlásenia Tk `ThemeChanged` pri rušení testovacích okien.

Zmenené: `subtitles.py`, `project.py`, oba jazykové katalógy, regresné testy a tento dokument. Bez novej závislosti, zvýšenia verzie, prestavby EXE alebo publikovania vydania.
