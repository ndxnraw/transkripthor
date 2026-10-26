# ND TranskripThor – používateľský návod

Tento návod opisuje aktuálny **pre-release**. Archívne EXE mu nemusí funkčne zodpovedať; výsledky overenia sú v [STATUS.md](STATUS.md). Číselné údaje v starších záznamoch sú historické.

Aktualizácia rozhrania podľa návrhu Studio, pri zachovaní lokálneho prepisu.
Samostatné karty **Nahrávky, Editor, Modely, Nastavenia a Podrobnosti spracovania**
udržujú ovládanie dostupné aj v minimálnom okne. Tmavý aj svetlý vzhľad používajú
pokojnejšie farby a jednotné písmo; značka a logo zostávajú zachované.
Okno sa naďalej spúšťa v minimálnej veľkosti podľa mierky rozhrania.

Windows aplikácia na **lokálny prepis zvuku do textu a titulkov**, bez minútových
kvót. Nahrávky ani prepisy sa neposielajú na externé služby. Internet slúži iba
na stiahnutie vybraných modelov. Po stiahnutí je dostupný režim Iba offline.

## Spustenie

Rozbaľte celý Windows ZIP a spustite **ND TranskripThor.exe**. Priečinok
`_internal` musí zostať vedľa EXE. Python netreba inštalovať. Modely nie sú
pribalené. Nová zdrojová zostava vznikne v `dist/ND TranskripThor`.
[Archív starších zostáv](https://github.com/ndxnraw/TranskripThor/releases) — aktuálny pre-release zostavte podľa DEVELOPMENT.md.

## Funkcie

- Slovenčina, čeština, angličtina, maďarčina, automatický jazyk a zmiešané CZ/SK.
- Pôvodný faster-whisper: Tiny, Small, Medium, Large v3; voliteľný slovenský
  KInIT Large v3 cez Transformers. CPU/GPU a cache zostávajú zachované.
- Trvalá fronta, pretiahnutie súborov, zmena poradia čakajúcich položiek,
  samostatné stavy, opakovanie chýb a pokračovanie po prerušení.
- Editor celého prepisu s časmi, vyhľadávaním, úpravou textu, lokálnym prehrávaním,
  pauzou a posunom. Text sa upravuje priamo vo vybranom bloku. Výber úseku
  nespúšťa zvuk; automatické prehrávanie možno zapnúť v Nastaveniach.
- TXT/SRT, nastaviteľné titulky, samostatné prevádzkové správy.
- Zapamätanie nastavení, svetlý/tmavý vzhľad a obnova predvolených hodnôt.
- Správca modelov: dostupnosť, miesto, sťahovanie a potvrdené odstránenie.
- Voliteľné lokálne zoskupenie hlasov a ručná oprava/priradenie mien.

## Bežný postup

1. Pridajte alebo pretiahnite nahrávky, vyberte jazyk, model a výstupný priečinok.
2. **Spustiť čakajúce** spracuje čakajúce položky. Vyberte prerušenú/chybnú
   nahrávku a zvoľte **Pokračovať / Skúsiť znova**. Platný projekt obnoví svoj
   uložený model, jazyk a nastavenia bez zmeny nastavení pre nové nahrávky.
3. **Nový prepis** vyžaduje výber položiek a vytvorí nové priečinky.
   Predchádzajúce výsledky neprepíše. **Podrobnosti** zobrazia zdroj, chybu
   a uložené nastavenia; čakajúce položky možno presúvať šípkami.
4. **Otvoriť prepis / Editor** otvorí výsledok na karte Editor. Kliknutím vyberte
   blok a upravte text priamo v ňom. **▶ Úsek** prehrá vybraný interval.
   **Hľadať** prehľadáva celý prepis; **Ďalší výskyt** prejde na ďalší zhodný úsek.
   Hovoriaci a nastavenia titulkov sú pod tlačidlom **Úsek, hovoriaci a titulky**.
5. **Uložiť** uloží projekt; samostatná ponuka **Možnosti exportu** vytvorí vybrané formáty.
   Pôvodný dokončený export zostáva zachovaný. Neuložené úpravy sú viditeľne
   označené; pri zatvorení editor upozorní na ich uloženie.

Karta Podrobnosti spracovania oddeľuje náhľad od prevádzkových správ. Náhľad má
obmedzenú históriu; editor používa všetky uložené úseky. Zobrazuje najviac 40
blokov na stránku, aby dlhé prepisy zbytočne nespomaľovali rozhranie.
Karta Modely oddeľuje modely prepisu od voliteľného rozlíšenia hlasov. Chýbajúci
model sa v režime offline oznámi ešte pred spustením prepisu.

## Ukladanie a pokračovanie

Každá úloha má `projekt.sqlite3`: zdroj a SHA-256 obsahu, nastavenia a revíziu
modelu, plán úsekov, dokončené úseky, časy slov, jazyk a bod pokračovania.
Checkpoint sa zapíše transakčne až po dokončení celého rečového úseku. Pri páde
alebo zastavení sa rozpracovaný úsek zopakuje celý. Bezpečne uložené úseky sa
nespracujú znova. Overuje sa obsah nahrávky aj zhoda nastavení; pri nezhode treba
obnoviť nastavenia alebo spustiť nový prepis.

SQLite projekt je autoritatívny zdroj. TXT/SRT sú exporty, ktoré možno znovu
vytvoriť; pri páde počas exportu otvorte projekt a zopakujte export bez prepisovania zvuku.
Staré samotné TXT/SRT z verzie 1.x nemajú checkpoint a nemožno z nich bezpečne
pokračovať. Zachovajte celý výstupný priečinok aj pôvodnú nahrávku.

Nastavenia sú atómový JSON a fronta je transakčná SQLite; uložené sú v `%LOCALAPPDATA%\LokalnyPrepis`.
Poškodený JSON sa podľa možnosti odloží s príponou `.damaged-*`; aplikácia
sa spustí s predvolenými hodnotami. Stav „spracúva sa“ sa po reštarte obnoví
ako „prerušené“. Modelová cache zostáva v podpriečinku `models`.

## CZ/SK a titulky

Režim **Čeština + slovenčina** používa Silero VAD a samostatné porovnanie `cs`
a `sk` pre každý úsek. Typicky 5–25 s, krátke susedné úseky sa spájajú, dlhé
delia. Confidence pod 0,60 alebo rozdiel pod 0,15 spustí dvojitý prepis; výber
porovná tokenovo vážené `avg_logprob`. Prah remízy je 0,03. Model sa nenačítava
znova a úseky sa explicitne transkribujú, neprekladajú. KInIT je iba pre SK.

Titulky používajú vety a časové značky slov; predvolene 42 znakov, dva riadky,
1–7 sekúnd. Po ručnej zmene textu sa staré zarovnanie slov zneplatní. Bez časov
slov zostane úsek v pôvodnom intervale; limity sú vtedy mäkké a zobrazí sa
upozornenie. Slová sa nevynechávajú ani neduplikujú. Neplatné intervaly sa
odmietnu. Mená hovoriacich sa uchovávajú v projekte; čistý TXT/SRT ich nepridáva.

## Voliteľné hlasy

V Správcovi modelov stiahnite **WeSpeaker ResNet34-LM**, potom v editore použite
**Zoskupiť podobné hlasy** (English: **Group similar voices**). Funkcia je
štandardne vypnutá; bežný prepis model nenačítava. Editor pred sprístupnením
akcie kontroluje lokálny model aj načítanie voliteľných knižníc. Dôvod
nedostupnosti zobrazí v podrobnostiach úseku. Zdrojová inštalácia doplní
knižnice cez `scripts/setup.ps1 -Speakers`; v plnej zostave sú pribalené.
Návrat k podrobnostiam alebo **Pomoc k hlasom** zopakuje kontrolu.
V poli **Hlas úseku** vyberte existujúce označenie alebo napíšte vlastné;
prázdne pole priradenie odstráni. **Premenovať hlas** zmení všetky výskyty
označenia, aj mimo aktuálnej stránky či vyhľadávania. Tieto opravy fungujú
bez modelu, podporujú Späť/Znova a zachovajú sa po uložení projektu.
Model [WeSpeaker](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM)
má licenciu **CC BY 4.0**, autorstvo tím WeSpeaker; používa sa pôvodný ONNX súbor
bez úpravy váh, revízia `f0c48c298fd835726c27956a5d617bad7115627e`.
Nie je gated a nevyžaduje token ani samostatné prijatie podmienok na portáli.
[Licencia CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Výpočet beží na CPU cez ONNX Runtime a voliteľný kaldi-native-fbank (Apache 2.0).
Váhy majú približne 27 MB; ďalšiu RAM potrebuje runtime a dekódovaný zvuk.
Hlasy sa zoskupujú podľa podobnosti zvuku úsekov, nezávisle od jazyka. Nie je to
identifikácia osoby ani presná diarizácia prekrývajúcich sa hlasov. Podsekundové
úseky zostanú neurčené, viac hlasov v jednom ASR úseku môže byť zlúčených.
Priradenia skontrolujte a ručne opravte; názov možno zmeniť aj v celom prepise.

## Overenie a obmedzenia

Aktuálne výsledky testov, čistého klonu a nového EXE sú v [STATUS.md](STATUS.md).
Historické výsledky vydaní sú v samostatných poznámkach k opravám. Modely a GPU
sa za overené označujú iba po skutočnej inferencii, nie na základe mockov.

Chýba oprávnený reálny CZ/SK korpus s ručne skontrolovanou referenciou.
[Vyhodnocovací nástroj a zoznam ukážok](../src/eval/README.md) oddeľujú
syntetický zvuk, mocky a skutočné meranie. Zmena jazyka bez pauzy môže zostať
v jednom úseku nerozpoznaná. Rozlíšenie hlasov nie je identifikácia osôb.

Dlhý zvuk používa diskovú PCM cache a blokové čítanie; large/KInIT stále
vyžadujú dostatok RAM/VRAM. ASR beží v samostatnom riadenom procese.
Bezpečne potvrdené checkpointy zostávajú po prerušení dostupné. ETA je hrubý
odhad, nie sľúbený čas. Fyzické DPI, Explorer drop a screen reader vyžadujú
manuálnu skúšku; automatická Tk matica ich nenahrádza.

## Vývoj a zostavenie

Presné príkazy pre Windows x64/Python 3.12, uzamknuté závislosti, modely,
nový počítač a pracovný cyklus sú v [DEVELOPMENT.md](DEVELOPMENT.md).
Používajte `scripts/setup.ps1`, `run.ps1`, `test.ps1` a `build.ps1`.
Výsledok je `dist/ND TranskripThor`; váhy modelov sa nepribaľujú.

Debug CZ/SK: pred spustením nastavte `$env:ND_TRANSKRIPTHOR_DEBUG='1'`.
Rotovaný log je `%LOCALAPPDATA%\LokalnyPrepis\asr-debug.log`; neobsahuje zvuk ani text prepisu.

Created by Daniel Návojský (ndxnraw) using Codex | 2026


## Úprava úsekov a export v pre-release

V ponuke editora môžete dokončený prepis rozdeliť pri kurzore v texte,
zlúčiť s nasledujúcim úsekom alebo ručne upraviť jeho začiatok a koniec.
Pri rozdelení zadáte čas v sekundách pôvodnej nahrávky; program nepredstiera
presné automatické zarovnanie upravených slov. Časy musia zostať v poradí,
bez prekryvov a v hraniciach nahrávky. Zlučované úseky musia mať rovnakého
hovoriaceho. Všetky operácie podporujú Undo/Redo. Pôvodný prepis zostáva
nedotknutý. Pred prvou štrukturálnou úpravou sa uloží záloha databázy;
staršie aplikácie nemusia nový projekt otvoriť, záloha zostáva použiteľná.

**Uložiť** uloží projekt bez vytvorenia exportu. **Možnosti exportu** umožnia
vybrať originál alebo uloženú revíziu a formáty TXT, SRT, VTT, DOCX a JSON.
Časy a hovoriaci v textových formátoch sú explicitné voľby; SRT/VTT majú
časy vždy. Pred exportom neuložených opráv najprv uložte projekt.
Každý export vytvorí samostatný balík v priečinku projektu `exporty`.
Otvoriť export zobrazí posledný úspešne publikovaný balík. Neúspešný export
nenaruší uložený projekt ani predchádzajúce exporty. Pôvodné tlačidlo opakovania
bez zvolených možností naďalej exportuje poslednú uloženú revíziu do TXT/SRT.
