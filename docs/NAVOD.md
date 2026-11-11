# ND TranskripThor – používateľský návod

Tento návod opisuje **Release v1 (1.0.0)** s hlavným rozhraním QML/Qt Quick.
[Stiahnuť vydanie](https://github.com/ndxnraw/TranskripThor/releases/tag/v1).
Staršie Tk/Pre-release zostavy majú odlišné ovládanie.

Hlavná obrazovka nemá karty. Pridanie nahrávok, jazyk, kvalita a spustenie
sú na jednom mieste. Doplnkové nástroje nájdete v ponuke **⋯ Možnosti**.
Svetlý/tmavý vzhľad a vysoký kontrast Windows zachovávajú dostupné ovládanie.

Windows aplikácia na **lokálny prepis zvuku do textu a titulkov**, bez minútových
kvót. Nahrávky ani prepisy sa neposielajú na externé služby. Internet slúži iba
na stiahnutie vybraných modelov. Po stiahnutí je dostupný režim Iba offline.

## Spustenie

Rozbaľte celý Windows ZIP a spustite **ND TranskripThor.exe**. Priečinok
`_internal` musí zostať vedľa EXE. Python netreba inštalovať. Modely nie sú
pribalené. Nová zdrojová zostava vznikne v `dist/ND TranskripThor`.
[Aktuálne stiahnutie a archív](https://github.com/ndxnraw/TranskripThor/releases).
Pri súkromnom repozitári sa prihláste účtom s prístupom k nemu.

## Funkcie

- Slovenčina, čeština, angličtina, maďarčina, automatický jazyk a zmiešané CZ/SK.
- Pôvodný faster-whisper: Tiny, Small, Medium, Large v3; voliteľný slovenský
  KInIT Large v3 cez Transformers. CPU/GPU a cache zostávajú zachované.
- Trvalá fronta, pretiahnutie súborov, zmena poradia čakajúcich položiek,
  samostatné stavy, opakovanie chýb a pokračovanie po prerušení.
- Editor celého prepisu s časmi, vyhľadávaním, úpravou textu, lokálnym prehrávaním,
  pauzou a posunom. Text sa upravuje priamo vo vybranom bloku. Výber úseku
  nespúšťa zvuk; automatické prehrávanie možno zapnúť v Nastaveniach.
- TXT/SRT/VTT/DOCX/JSON, nastaviteľné titulky, samostatné prevádzkové správy.
- Zapamätanie nastavení, svetlý/tmavý vzhľad a vysoký kontrast Windows.
- Správca modelov: dostupnosť, miesto, sťahovanie a potvrdené odstránenie.
- Voliteľné lokálne zoskupenie hlasov a ručná oprava/priradenie mien.

## Bežný postup

1. Kliknite na **Pridať nahrávky** alebo pretiahnite zvuk/video do hlavnej plochy.
   Vyberte jazyk a kvalitu a stlačte **Spustiť prepis**. Správcu modelov
   netreba otvárať vopred: potrebné súbory sa pripravia pri prvom použití.
   V režime iba offline sa internet zapne až po vašom výslovnom súhlase.
2. Front zobrazuje stav každej nahrávky. Ponuka **⋯** pri položke obsahuje
   pokračovanie/opakovanie, nový prepis od začiatku, poradie, odobratie
   z frontu a podrobnosti. Odobratie nemaže nahrávku ani projekt.
   **Stop** zastaví prácu; uložené checkpointy zostávajú dostupné.
3. Pri hotovej položke stlačte **Otvoriť prepis**. V editore vyberte úsek
   v zozname a upravte jeho text vpravo (v úzkom okne pod zoznamom).
   Výber sám nespustí zvuk, pokiaľ nemáte zapnuté automatické prehrávanie.
   **▶ Úsek** prehrá interval; posuvník pracuje s časom pôvodnej nahrávky.
4. **Hľadať** prehľadá celý prepis. Šípky prechádzajú jednotlivé zhody,
   **Ctrl+F** zameria hľadanie, **F3/Shift+F3** prejde ďalšiu/predošlú zhodu.
   **Ctrl+Z/Ctrl+Y** v texte vracia/opakuje úpravy. Hovoriaci, delenie,
   spájanie, časy a titulky sú pod **Úsek, hlasy a titulky**.
5. **Uložiť projekt / Ctrl+S** uloží zmeny. **Možnosti exportu** vytvoria
   vybrané TXT/SRT/VTT/DOCX/JSON z originálu alebo uloženej revízie.
   Neuložené zmeny označuje hviezdička; zatvorenie alebo otvorenie iného
   projektu vyžiada Uložiť/Zahodiť/Zrušiť. Úpravy počas ukladania zostanú
   neuložené a možno ich uložiť nasledujúcim príkazom.

**Späť** v hlavičke vráti nahrávky bez straty rozpracovaného textu.
Do otvoreného editora sa vrátite cez **⋯ → Vrátiť sa do editora**.
Ponuka obsahuje aj otvorenie existujúceho `projekt.sqlite3` (**Ctrl+O**),
pokročilé nastavenia CPU/CUDA, offline, výstupného priečinka, modely,
lokálne dáta/diagnostiku, prevádzkové správy a vzhľad. Zoznam úsekov
sa zobrazuje priebežne podľa potreby; neprepína sa cez stránky ani karty.

## Ukladanie a pokračovanie

Každá úloha má `projekt.sqlite3`: zdroj a SHA-256 obsahu, nastavenia a revíziu
modelu, plán úsekov, dokončené úseky, časy slov, jazyk a bod pokračovania.
Checkpoint sa zapíše transakčne až po dokončení celého rečového úseku. Pri páde
alebo zastavení sa rozpracovaný úsek zopakuje celý. Bezpečne uložené úseky sa
nespracujú znova. Overuje sa obsah nahrávky aj zhoda nastavení; pri nezhode treba
obnoviť nastavenia alebo spustiť nový prepis.

SQLite projekt je autoritatívny zdroj. TXT/SRT/VTT/DOCX/JSON sú exporty, ktoré možno znovu
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
odmietnu. Mená hovoriacich sa uchovávajú v projekte; export ich pridá iba pri zapnutej voľbe hovoriacich.

## Voliteľné hlasy

V Správcovi modelov stiahnite **WeSpeaker ResNet34-LM**, potom v editore použite
**Zoskupiť podobné hlasy** (English: **Group similar voices**). Funkcia je
štandardne vypnutá; bežný prepis model nenačítava. Editor pred spustením
akcie kontroluje lokálny model aj načítanie voliteľných knižníc. Dôvod
nedostupnosti zobrazí v stavovej správe. Zdrojová inštalácia doplní
knižnice cez `scripts/setup.ps1 -Speakers`; v plnej zostave sú pribalené.
Opätovné spustenie akcie zopakuje kontrolu.
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
manuálnu skúšku; automatické geometrické skúšky ich nenahrádzajú.

## Vývoj a zostavenie

Presné príkazy pre Windows x64/Python 3.12, uzamknuté závislosti, modely,
nový počítač a pracovný cyklus sú v [DEVELOPMENT.md](DEVELOPMENT.md).
Používajte `scripts/setup.ps1`, `run.ps1`, `test.ps1` a `build.ps1`.
Cieľ určíte cez `build.ps1 -OutputDirectory dist`; váhy modelov sa nepribaľujú.

Debug CZ/SK: pred spustením nastavte `$env:ND_TRANSKRIPTHOR_DEBUG='1'`.
Rotovaný log je `%LOCALAPPDATA%\LokalnyPrepis\asr-debug.log`; neobsahuje zvuk ani text prepisu.

Created by Daniel Návojský (ndxnraw) using Codex | 2026


## Úprava úsekov a export

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

## Lokálne dáta a diagnostika

V **⋯ → Local data & diagnostics** / **⋯ → Lokálne dáta a diagnostika**
sa zobrazujú umiestnenia a logické veľkosti profilu, modelov, výstupného priečinka,
známych projektov a PCM cache. Známymi projektmi sú položky fronty a otvorené
editory; aplikácia nehľadá projekty po celom disku. Priečinky sa môžu prekrývať,
preto veľkosti nesčítavajte. Výstupný priečinok môže obsahovať aj cudzie súbory.
Čiastočný výsledok je dolná hranica, nie potvrdenie prázdneho priečinka.

- **Odobrať z fronty** odstráni iba položku zo zoznamu. Súbory a projekty ostávajú.
- **Odstránenie projektu** znamená stratu databázy s prepisom, opravami, revíziami
  a postupom aj exportov vo vymazanom priečinku. Prehľad projekty nemaže.
  Pred samostatnou správou priečinka v Prieskumníkovi vytvorte zálohu a zatvorte
  editor aj spracovanie. Zdrojový zvuk uchovávajte samostatne.
- **Odstrániť model** v správcovi Modely po potvrdení odstráni jeho lokálne váhy.
  Nahrávky ani prepisy nemaže. Bez váh nebude daný model fungovať offline.

Lokálne spracovanie nie je šifrovanie: aplikácia súbory automaticky nešifruje.
SQLite a exporty obsahujú čitateľné prepisy, fronta cesty a PCM cache dekódovaný
zvuk. Zabezpečenie účtu, disku a záloh je samostatná vec. Aktívnu cache nemažte.

**Náhľad diagnostiky** ukazuje celý obsah oboch súborov budúceho ZIP. Až potom
sa sprístupní uloženie. Balík obsahuje povolené verzie knižníc, Python, platformu,
počty stavov fronty, offline voľbu a anonymné veľkosti úložísk. Neobsahuje zvuk,
text prepisu, názvy nahrávok, cesty, logy, databázy, tokeny ani súbory nastavení.
Ukladá sa presne zobrazený stav; Obnoviť vyžaduje nový náhľad. ZIP ostáva lokálny,
aplikácia ho nikam neposiela. Pred vlastným zdieľaním skontrolujte jeho obsah.

## Obnova, originál a revízie

**Otvoriť projekt / Open project** umožní vybrať existujúci projekt aj po
odobratí nahrávky z fronty. Ak zvuk chýba, text sa dá upravovať a exportovať;
prehrávanie je nedostupné. Vyberte náhradný zvuk: program porovná SHA-256
obsahu s uloženým odtlačkom a odlišnú nahrávku odmietne.

Po zastavení počas hashovania, dekódovania alebo VAD sa príprava bezpečne
zopakuje. Pred prvými uloženými úsekmi ešte nie je čo zobraziť v editore.
Pokračovanie používa pôvodný model, jeho presnú revíziu a dekódovacie nastavenia.
Chýbajúcu revíziu treba online stiahnuť; offline je potrebné obnoviť jej cache
alebo zvoliť nový prepis. Zariadenie CPU/GPU možno pri obnove zmeniť.

Pôvodný výsledok modelu a používateľské revízie sa ukladajú oddelene.
Starší projekt sa migruje so zálohou; ak pôvodný text už nemal, aplikácia
ho nevymýšľa a originál nie je dostupný na export. Uloženie projektu nie je
potvrdenie úspechu exportu. Po chybe export zopakujte bez prepisovania zvuku.
Titulkový profil patrí projektu; jeho samotná zmena je neuloženou úpravou.
Undo/Redo funguje nad úpravami aj po zmene stránky alebo vyhľadávania.

## Modely, zariadenie a jazyk rozhrania

Predvolené zariadenie je CPU. GPU vyžaduje podporovanú NVIDIA CUDA a jej
knižnice; pri chybe sa CPU použije až po potvrdení používateľom. Model sa
nenačítava po samotnej zmene výberu. KInIT je voliteľný iba pre slovenčinu,
nie pre CZ/SK režim. Modely nie sú súčasťou distribúcie.

Správca rozlišuje nájdenú cache, neúplný model a overenú integritu. Staršiu
cache bez potvrdenia možno explicitne overiť; nájdený súbor nie je dôkazom
integrity. Offline režim zakazuje sťahovanie; nepripravený model alebo chýbajúca
presná revízia potrebuje najprv online stiahnutie/obnovu. Zastavené sťahovanie
možno zopakovať s využitím bezpečnej čiastočnej cache.

Rozhranie pri prvom spustení používa English. Voľba Language → Slovenčina
v Nastaveniach sa uplatní po ďalšom spustení. Nemení jazyk nahrávky, text
ani nastavenia modelu. **O aplikácii / About ND TranskripThor** vysvetľuje
Pre-release a internú verziu kompatibility; nejde o číslo nového vydania.
Prehrávač ponúka výstupné zariadenie a 0,75×/1×/1,25×/1,5×. Posun počas
pauzy zachová pauzu; počas prehrávania pokračuje od novej pozície.
