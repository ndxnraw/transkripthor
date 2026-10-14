# Zjednotenie dizajnu a podpisu

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

Úloha 7, 9. október 2026. Verzia zostáva 2.1.3b; nič sa nepublikuje a vývojový bod návratu F02-20261009 sa nemení.

## Aktuálny stav a rozsah

Pred úpravou už boli implementované opravy F01–F06 vrátane rezervovaného ovládania a samostatnej karty nastavení. Presný podpis už existoval v `AUTHOR`; chýbalo jeho prispôsobenie šírke. Zachované sú rozpracované opravy, logo, farebná identita, lokálne spracovanie aj formáty dát.

- Jediným hlavným farebným tlačidlom na karte Nahrávky je **Spustiť prepis**. Pridať nahrávky je štandardná vedľajšia akcia. Editor si ponecháva hlavné Uložiť TXT/SRT.
- Duplicitné tlačidlo Editor bolo odstránené. Kontextová akcia zostáva Otvoriť prepis / Pokračovať / Skúsiť znova. Ponuka **Ďalšie možnosti** umožňuje nový prepis od začiatku a pri prerušenej/chybovej úlohe otvorenie rozpracovaného prepisu; počas práce je zablokovaná.
- Zoznam zobrazuje stav textom aj symbolom. Šípky poradia majú slovné označenie Nahor/Nadol. Ukazovatele postupu sú označené Nahrávka a Dávka.
- Nastavenia sú označené **Pre nové prepisy**. Výpočet hlasov sa volá **Zoskupiť podobné hlasy**, aby nenaznačoval rozpoznanie identity osoby.
- Segoe UI a existujúce veľkosti písma zostávajú zachované. Súvisiace riadky používajú spoločné štýly, mierne zaoblenie a odstupy; zalamovanie ovládania z F02 ostáva funkčné.
- Vstupy majú zvýraznený obrys pri fokuse; tlačidlá, karty, zaškrtávacie polia a texty používajú farbu fokusu z palety. Výber textu má v tmavom vzhľade tmavý text na svetlom akcente. Ponuka rešpektuje oba vzhľady.
- Krátke správy nezobrazujú zbytočný posuvník. Pri dlhých správach sa objaví a celý obsah zostane dostupný.
- Podpis **Created by Daniel Návojský (ndxnraw) using Codex | 2026** ostáva vpravo dole. Samostatný stĺpec vedľa verzie nastavuje zalomenie podľa dostupnej šírky, bez zmenšenia písma či zmeny textu. Päta aj hlavné akcie majú rezervované miesto.

## Overenie

Celá sada prešla: **127 testov, 80,321 s, bez zlyhania**. Kontrola 12. októbra 2026 potvrdila, že zdrojové súbory dizajnu neboli po tomto behu zmenené; `git diff --check` prešiel. Existujúce upozornenia Tcl `ThemeChanged` pri rušení testovacích okien zostávajú v protokole.

12. októbra sa podarilo vizuálne overiť kartu Nahrávky v spustenej zdrojovej aplikácii na aktuálnom monitore v tmavom aj svetlom vzhľade. Logo, podpis, pomenované ukazovatele a spodné akcie boli viditeľné. Skúška používala samostatný profil `work/visual-design-final`. Predchádzajúci pokus 9. októbra zablokovala chyba Computer Use; tento nový úspešný pokus sa vzťahuje na zdrojovú aplikáciu, nie prestavané EXE.

`test_design.py` overuje hierarchiu akcií, ponuku pri hotovom/prerušenom projekte, blokovanie počas práce, vyvolanie nového prepisu, fokus a kontrast výberu. Podpis skúša pri šírkach 480/800/1200 px, oboch vzhľadoch a piatich mierkach Tk. Úzke šírky tu izolovane skúšajú pätu, nie podporu celého pracovného rozhrania pod jeho minimom.

Matica `test_dpi_layout.py` naďalej kontroluje všetky karty na 1366 × 768 a 1536 × 864 pri 100/125/150/175/200 % v oboch vzhľadoch s dlhými správami a rozbaleným editorom. Navyše kontroluje aj ponuku a hranice podpisu. Pôvodný `StudioScalingTest` nebol oslabený. V teste fronty sa očakávaný text zmenil na nový stav so symbolom.

Ide o natívne testy Tk na Windows s nastavenou mierkou Tk. Prepínanie systémového DPI Windows, presun medzi monitormi, vysoký kontrast a Narrator nie sú týmto testom overené. Nebola zavedená nová história Undo, ďalšie exportné formáty ani migrácia frameworku; ide o dizajnovú úlohu, nie realizáciu všetkých ďalších funkčných návrhov analýzy.

Protokol celej sady: `work/tests-design-final.log`. Zdroj sa spúšťa príkazom `python src/prepis.py` v pripravenom prostredí projektu. Na oddelené skúšky použite parameter `--profile work/test-design-profile`. Existujúce EXE vrátane samostatnej F02 zostavy zostávajú nezmenené.
