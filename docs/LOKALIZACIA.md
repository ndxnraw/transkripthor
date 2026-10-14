# Jazyk používateľského rozhrania

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Angličtina je predvolená bez ohľadu na jazyk systému. Na karte **Settings → Language** / **Nastavenia → Jazyk** vyberte **English** alebo **Slovenčina**. Voľba platí od ďalšieho spustenia; aplikácia sa sama nereštartuje. Počas prepisu ju možno uložiť bez zastavenia práce alebo zmeny otvoreného editora.

## Uloženie a oddelenie od dát

Používateľský `settings.json` obsahuje nezávislé `ui_language: "en" | "sk"`. Chýbajúca, neplatná alebo nesprávne typovaná hodnota znamená `en`. Platná explicitná hodnota zostáva zachovaná. Zápis zlúči nastavenia s existujúcim súborom, vrátane neznámych položiek; nepoužíva jazyk Windows na odhad predvoľby.

Jazyk nahrávky, model, zariadenie a dáta SQLite projektov sa pri voľbe jazyka rozhrania nemenia. Existujúce uložené hodnoty výberov ASR zostávajú kompatibilné; prekladový adaptér Comboboxu mení iba ich viditeľné popisy. Prepnutie neoznačuje editor ako upravený a neprepisuje TXT/SRT.

Fronta používa interné kódy `waiting`, `processing`, `completed`, `interrupted`, `failed`. Staré slovenské hodnoty sa bezpečne načítajú cez explicitnú kompatibilnú mapu; pri nasledujúcom uložení sa zapíšu nové kódy. Ostatné údaje položky sa zachovajú. Stav rozpracovaného projektu v SQLite je samostatný a táto zmena ho nemení. Staršie zostavy nepoznajú nové kódy fronty; zachovaný bod návratu F02 používajte s jeho oddeleným profilom.

## Spoločná prekladová vrstva

- `src/i18n.py`: `tr(key, **values)`, validácia jazyka, fallback, počty a preklad zobrazených výberov.
- `src/locales/en.json` a `sk.json`: UTF-8 katalógy s významovými kľúčmi. Nové funkcie pridávajú kľúče do oboch súborov. Pri úprave znenia sa kľúč nemení.
- `tr()` sa volá pri vytvorení textu, nie pri importe modulu; globálny inventár modelov preto uchováva kľúče popisov. Technické identifikátory a podmienky logiky nepoužívajú preložené texty.
- Parametre sa vkladajú až po výbere prekladu, nie skladaním textu prepisu. Katalógy musia používať rovnaké parametre, prevody a formátovacie špecifikácie. Chybný slovenský formát aj chýbajúci slovenský kľúč použijú angličtinu.
- Chýbajúce kľúče a chyby formátovania sa zaznamenávajú do `i18n.log` v profile. Log obsahuje iba jazyk, kľúč a dôvod, nie hodnoty parametrov ani obsah prepisu. Chýbajúci anglický kľúč sa zobrazí ako `[key]`; automatický test má takej chybe zabrániť.
- Počty nahrávok používajú formy `one/few/other`; angličtina má jednotné a množné číslo, slovenčina aj formu pre 2–4. Ostatné počítadlá používajú označenie a číselnú hodnotu/pomer.
- Aktívny jazyk sa počas relácie nemení. Samostatný proces sťahovania dostane jazyk aktuálnej relácie, nie novú voľbu čakajúcu na reštart.

Preložené sú hlavné karty, nastavenia, fronta a ponuky, editor a exportné hlásenia, správca modelov, nápovedy, priebeh, používateľské chyby a upozornenia. Logo a podpis **Created by Daniel Návojský (ndxnraw) using Codex | 2026** zostávajú v oboch jazykoch totožné.

## Čo sa zámerne neprekladá

- Samotné prepisy, exportovaný obsah, používateľské názvy a uložené mená hovoriacich vrátane historických označení „Hovoriaci N“ a „Neurčený hovoriaci“. Ide o dáta projektu, nie texty rozhrania.
- Názvy modelov/repozitárov, cesty a názvy súborov, identifikátory, pôvodné technické podrobnosti výnimiek, technické debug logy a historické uložené chyby fronty. Nové okolité vysvetlenia sú lokalizované.
- Existujúci sprievodný text v migračnej zálohe `ZALOHA-DOKONCENA.txt` zostáva slovenský; jazyk rozhrania nesmie prepisovať zachované zálohy.

Windows spravuje vlastný výber súborov/priečinkov a natívne messageboxy. Aplikácia prekladá ich zadané nadpisy, správy a filtre; systémové tlačidlá a navigácia môžu zostať v jazyku Windows/Tk. `simpledialog` pre premenovanie hlasu používa štandardné tlačidlá Tk OK/Cancel. Tieto štandardné dialógy neboli nahradené vlastnými implementáciami. Nastavenie jazyka aplikácie nemení systémový jazyk.

## Overovanie a zostavenie

`test_i18n.py` kontroluje predvoľby, neplatné hodnoty, oba katalógy, parametre, fallback a diagnostiku, plurály, zachovanie starých nastavení, normalizáciu fronty, obnovenie voľby po reštarte a nezmenené bajty SQLite/TXT/SRT pri voľbe jazyka s otvoreným editorom. Test existencie kľúčov pokrýva aj hlásenia menej bežných chybových vetiev.

`test_dpi_layout.py` skúša oba jazyky × oba vzhľady × mierky Tk 100/125/150/175/200 % na virtuálnych rozmeroch 1366 × 768 a 1536 × 864, vrátane rozbaleného editora, dlhých hlásení a podpisu. Ide o natívny Windows/Tk proces, nie zmenu systémového DPI alebo presun medzi monitormi.

`TranskripTHOR.spec` explicitne pribaľuje celý priečinok `locales`. Nová závislosť nie je potrebná. Bežné zostavenie cez `zostavit.cmd` naďalej najprv vyžaduje úspešné testy. Verzia sa nemení a nič sa automaticky nepublikuje. Izolovaná overovacia zostava používa `outputs/dev-i18n-20261012`; pôvodné vydania a bod návratu F02 zostávajú zachované.

### Výsledok overenia 12. 10. 2026

- Celá regresná sada: **136 testov, OK**, 107,303 s (`work/tests-i18n-final.log`). Zahŕňa lokalizáciu, ukladanie/obnovu, exporty a existujúce opravy F01–F06.
- Automatické kontroly rozloženia prešli pre oba jazyky, oba vzhľady a mierky Tk 100/125/150/175/200 % na uvedených rozmeroch obrazovky. Nejde o manuálne vizuálne overenie ani zmenu systémového DPI Windows.
- PyInstaller úspešne vytvoril samostatné EXE v `outputs/dev-i18n-20261012/ND TranskripThor/`. Oba pribalené katalógy sa SHA-256 zhodujú so zdrojmi.
- Zostavené EXE úspešne vykonalo `--self-test-v2` s lokálnym modelom Tiny na CPU a nahrávkou `work/slovensky-test.wav`: návratový kód 0, `OK: True`, projekt a exporty v oddelenom `work/exe-i18n-dev`. Nešlo o sieťové sťahovanie ani GPU skúšku.
- EXE sa spustilo s oddeleným profilom `work/visual-i18n-en`. Nástroj na vizuálnu kontrolu Windows však pri snímaní hlásil `window id 67334 was not found` aj po obnovení výberu okna. **Skutočná vizuálna kontrola novej zostavy v EN/SK nebola dokončená.** Presuny medzi monitormi a jednotlivé systémové DPI neboli overené.

Na manuálne dokončenie vizuálnej kontroly spustite `SPUSTIT-TEST.cmd` v priečinku vývojovej zostavy. Používa samostatný profil. Prezrite všetky karty v tmavom aj svetlom vzhľade, zvoľte Settings → Language → Slovenčina, aplikáciu zatvorte a znovu spustite rovnakým súborom. Overte preložené hlásenia, podpis a dostupnosť ovládania aj pri systémovom zväčšení 100–200 %. Jazyk systému môže naďalej určovať tlačidlá natívnych dialógov.
