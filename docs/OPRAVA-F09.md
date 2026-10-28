# F09 — história úprav a hlavička

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Pôvodná história patrila dočasnému textovému poľu Tk, ktoré sa pri zmene segmentu zničilo. Nový `EditHistory` uchováva nemenné rozdiely polí nad stabilnými identifikátormi segmentov. Navigácia, stránkovanie ani vyhľadávanie ju nemažú.

## Hranice operácií

- Jedna operácia zahŕňa rozpísaný text a ručne zmeneného hovoriaceho aktívneho segmentu od posledného zachytenia. Zachytí sa pred odchodom zo segmentu, stránkovaním, vyhľadávaním, uložením, Undo/Redo alebo dávkovou zmenou hovoriacich. Nejde o Undo po jednotlivých znakoch.
- Hromadné premenovanie hovoriaceho je jedna operácia. Prijatie výsledkov rozlíšenia hlasov je samostatná operácia až po zachytení rozpracovaného textu. Zachováva ochranu súbežných ručných zmien z F01; Undo/Redo tiež zvyšuje revízie priradení.
- Ctrl+Z vráti operáciu; Ctrl+Y alebo Ctrl+Shift+Z ju zopakuje. Dostupné sú aj pomenované tlačidlá. Obnoví sa dotknutý segment a stránka bez automatického prehrávania. Filter sa zruší len vtedy, ak by skryl obnovený segment.
- Zmena textu zneplatní časy slov. Undo obnoví pôvodné časy spolu s presne zodpovedajúcim textom; Redo ich opäť zneplatní. Časy celého segmentu sa nemenia.
- Uloženie históriu nemaže. Po úspešnom zápise projektu sa zapamätá uložený bod. Návrat naň zruší označenie neuložených zmien; Undo zaň označenie obnoví. Zlyhaný export nemení úspech uloženia projektu. Undo samo nemení už publikované exporty; treba opäť uložiť/exportovať.
- Nastavenia titulkov nie sú súčasťou textovej histórie; ich samostatné neuložené zmeny sa nestratia pri Undo textu. Pôvodný prepis modelu zostáva nedotknutý.

## Pamäť a životnosť

História patrí jednej otvorenej relácii editora. Po zatvorení sa znovu otvára uložená revízia bez starého Undo zásobníka. Uchováva najviac 200 operácií a 16 MiB serializovaných rozdielov (plus malá réžia objektov). Najstaršie operácie sa odstraňujú. Jedna operácia presahujúca limit vyčistí zásobník, ostane vykonaná a neuložená; aplikácia má lokalizované upozornenie. Zvuk ani celý projekt sa do histórie nekopírujú.

## Hlavička

Z `ui_layout.py` bol odstránený samotný widget podnadpisu. Obal značky má teraz iba názov a prirodzenú výšku jedného riadka, bez vyhradeného prázdneho miesta. Logo, farebná identita, názov a autorský podpis sa nemenia. Ostatné informácie o súkromí ostávajú zachované.

## Overenie

Nové testy pokrývajú prechody medzi segmentmi a stránkami, vyhľadávanie, text a časy slov, ručné a dávkové zmeny hovoriacich, prijatie asynchrónnych výsledkov, uloženie a opätovné otvorenie, klávesové skratky, novú vetvu histórie, uložený bod, nezávislý titulkový profil a pamäťové limity.

Test hlavičky kontroluje oba vzhľady, rozmery 1040 a 1366 bodov, aplikačné škálovanie 100/125/150/175/200 %, absenciu prázdneho riadka, zachovanie loga a podpisu aj opätovné spustenie s rovnakým izolovaným profilom. Toto nie je fyzické prepínanie systémového DPI Windows medzi monitormi.

Verzia ani publikované vydanie sa nemenia. Používateľské projekty a profil sa pri testoch nepoužívajú.

Výsledok 13. 10. 2026: celá regresná sada **165 testov, OK (126,566 s)**, log `work/tests-f09-final.log`. Prvý beh odhalil chýbajúce spracovanie udalostí fokusu pred syntetickou skratkou Ctrl+Shift+Z v novom teste. Test teraz čaká na udalosti a navyše kontroluje fokus nového textového poľa; jeho pôvodná kontrola obnoveného textu zostala zachovaná. Samostatná sada histórie: **7 testov, OK**. `git diff --check` bez chýb whitespace.

Prakticky cez Computer Use na zdrojovej aplikácii s oddeleným profilom a kópiou skúšobného projektu: napísanie textu, Ctrl+Z, Ctrl+Y, návrat na čistý stav, oba vzhľady, maximalizácia a obnovenie veľkosti. Hlavička zostala bez podnadpisu, názov/logo/podpis boli viditeľné, tlačidlá Undo/Redo dostupné. Reštart a päť úrovní škálovania kontrolovali automatické testy; fyzické prepínanie systémového DPI ani nové zostavené EXE sa v tejto úlohe neoverovalo.

Súbory tejto úlohy: `edit_history.py`, `editor.py`, `transcript_blocks.py`, `ui_layout.py`, `locales/en.json`, `locales/sk.json`, `test_edit_history.py`, `test_design.py` v `src`, tento dokument a lokálny vizuálny harness `work/f09_visual.py`.
