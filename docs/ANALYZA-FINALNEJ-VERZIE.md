# ND TranskripThor analýza a návrh finálnej verzie

Historický záznam. Aktuálne cesty, spúšťanie a výsledky overenia sú v [DEVELOPMENT.md](DEVELOPMENT.md) a [STATUS.md](STATUS.md).

ND TranskripThor 2.1.3b má použiteľný základ lokálneho prepisu, obnovovania práce a editora. Za finálnu verziu ho zatiaľ neodporúčam označiť: aktuálny audit reprodukoval stratu rozpísanej úpravy, neúplný projekt po skorom zastavení a nedostupné hlavné tlačidlo pri 200 % zväčšení. Prioritou je ochrana práce používateľa, dostupné ovládanie a merateľná kvalita prepisu. Zmena programovacieho jazyka sama tieto chyby neodstráni.

Audit z 8. októbra 2026 sa vzťahuje na najnovší lokálny commit `64d52f1`, verziu v `src/ui.py` a miestnu zostavu `outputs/release213b`. Vstupný pracovný strom bol čistý. Verejnú najnovšiu verziu na GitHube sa nepodarilo nezávisle načítať; záver o aktuálnosti sa preto vzťahuje na tento pracovný priečinok. Následná zmena podpisu je opísaná samostatne.

## Rozsah a výsledky overenia

Preskúmané boli vstup aplikácie, fronta, SQLite projekty, oba ASR adaptéry, zmiešaný CZ/SK režim, modelová cache a sťahovanie, editor, prehrávanie, titulky, zoskupovanie hlasov, rozhranie, DPI, pretiahnutie súborov, testy a zostavovanie.

| Overenie | Výsledok a význam |
| --- | --- |
| Aktuálna existujúca sada | 89 testov za 59,369 s; 88 úspešných, 1 neúspešný. |
| Zväčšenie rozhrania | Test `StudioScalingTest.test_editor_settings_models_fit_both_themes_and_scales` zlyhal pri mierke 2 na karte Nahrávky: „Spustiť čakajúce“ nebolo zobrazené. |
| Úprava textu počas priraďovania hlasov | Simulované doručenie výsledku hlasov zahodilo práve rozpísaný text. |
| Zastavenie počas prvého dekódovania | Vznikla databáza bez `schema`, `source` a `settings`; otvorenie v editore skončilo `TypeError`. |
| Opätovný export dokončeného projektu | Po uložení opravy a volaní dokončeného projektu cez `resume=True` sa pôvodný `prepis.txt` zmenil na opravený text. |
| Nastavenia titulkov | Uloženie hodnoty 55 znakov nezapísalo profil titulkov do projektu; konštruktor editora používa opäť 42. |
| Krátky titulok | Úsek 0–0,1 s pri minimálnom čase 1 s zostal dlhý 0,1 s bez upozornenia. |

Reprodukcie používajú dočasné projekty a riadené náhrady dekodéra alebo výsledkov hlasov. Potvrdzujú správanie aplikácie, nie presnosť rozpoznávania reči. Tento audit nespúšťal nový reálny GPU prepis, meranie reálneho korpusu ani systémový drop z Prieskumníka. Staršie overenie Tiny CPU a načítania tkdnd je zaznamenané v `outputs/release213b/ND TranskripThor/OVERENIE.json`; nie je zamieňané s novým testom.

Aktuálny testovací výstup obsahuje aj upozornenia Tcl `ThemeChanged` po zničení okna. Nejde o ďalší neúspešný unittest, ale o dôvod upratať životný cyklus testovacích okien a časovačov.

## Čo zachovať

- Lokálne spracovanie, explicitný offline režim a oddelenie sťahovania modelov od práce so zvukom.
- SQLite ako zdroj pravdy a transakčný zápis až po dokončení celého úseku. Existujúce skúšky pokrývajú pád procesu aj pokračovanie bez zdvojenia úsekov.
- SHA-256 zdrojového súboru a kontrolu nastavení pri obnove projektu.
- Atómové nahradenie jednotlivých súborov nastavení a exportov cez dočasný súbor.
- Znovupoužitie načítaného modelu, vypnuté automatické prehrávanie a voliteľné rozlíšenie hlasov.
- Oddelený sťahovací proces, časové limity, obmedzené opakovanie pokusov, kontrolné súčty a bezpečné sieťové chybové hlásenia.
- Svetlý aj tmavý vzhľad, samostatné pracovné karty a stránkovanie dlhých prepisov.
- Zachovanie časov úseku a zneplatnenie časovania slov po ručnej oprave textu. Je správne nevydávať staré časovanie za presné.

## Chyby ktoré treba vyriešiť pred finálnym vydaním

P1 znamená problém blokujúci odporúčanie finálneho vydania. P2 znamená dôležitú opravu spoľahlivosti alebo použiteľnosti. P3 je následné zlepšenie. Reprodukované chyby sú oddelené od rizík odvodených zo zdrojového kódu.

### F01 Strata rozpísanej opravy pri dokončení hlasov

**P1, reprodukované.** `editor.py:296`: vetva `speakers` prepíše priradenia, nastaví `current=None` a znovu vykreslí bloky bez `capture()`. Používateľ pritom môže ďalej písať. Text zostávajúci iba vo vstupnom poli sa zničí spolu s týmto poľom. Skúška očakávala „Práve píšem novú opravu.“, v dátach zostalo „Upravený text.“.

**Riešenie:** tesne pred aplikovaním výsledkov zachytiť aktívnu úpravu, výsledky viazať na stabilné ID segmentov a revíziu projektu, zachovať výber, kurzor a posun. Pracovné vlákno má dostať nemenný obraz segmentov. Súbežné ručné priradenie hovoriaceho buď dočasne zamknúť, alebo riešiť konflikt revízií.

**Podmienka opravy:** počas výpočtu písať, meniť bloky a vyhľadávať; po doručení hlasov, uložení a opätovnom otvorení musí zostať každá textová oprava.

### F02 Hlavné ovládanie zmizne pri veľkom zväčšení

**P1, reprodukované existujúcim testom.** `ui_layout.py:43`: karta Nahrávky ukladá veľa pevných riadkov za sebou a nemá posúvanie celej oblasti. Výška okna je zároveň obmedzená obrazovkou (`ui_layout.py:214`). Pri 200 % mierke už hlavné tlačidlo nedostane priestor. Samotné zväčšenie minimálnej výšky problém na malej obrazovke nevyrieši.

**Riešenie:** ovládanie spustenia a zastavenia rezervovať pri spodnom okraji; nastavenia dať do posúvateľnej alebo zbaliteľnej oblasti. Pri úzkom okne rozdeliť nastavenia do viacerých riadkov a vedľajšie akcie presunúť do ponuky. Zachovať bežnú veľkosť písma.

**Podmienka opravy:** všetky hlavné akcie sú dosiahnuteľné myšou aj klávesnicou na 1366 × 768 a 1536 × 864 pri 100–200 %, v oboch témach, aj s dlhým názvom súboru a chybovým hlásením. Otestovať tiež zmenu monitora a systémového DPI; dnešný test mení Tk mierku.

### F03 Skoré zastavenie zanechá neúplný projekt

**P1, reprodukované.** `jobs.py:56–80`: databáza sa vytvorí pred dekódovaním, no metadata sa inicializujú až po dekódovaní a VAD. Zastavenie po dekódovaní vráti `False` pred inicializáciou. Fronta už má cestu k projektu, preto ponúka Editor. `Editor.__init__` potom predpokladá neprázdny `source`.

**Riešenie:** zaviesť explicitné fázy `príprava`, `pripravené`, `prepis`, `dokončené`. Uložiť minimálne metadata skôr a transakčne označiť dokončenú prípravu. Editor sprístupniť iba platnému projektu; pri nulovom počte úsekov vysvetliť, že prepis ešte nezačal. Obnovovanie neúplnej prípravy musí bezpečne zopakovať prípravu.

**Podmienka opravy:** zastaviť aj simulovať pád pri hashovaní, dekódovaní, VAD a pred prvým checkpointom. Nevznikne neobslúžená chyba ani zavádzajúca ponuka Editora. Dnešné opakovanie vie pri chýbajúcej schéme prípravu zopakovať; problémom nie je preukázaná strata už uložených úsekov.

### F04 Pôvodný prepis nemá nemennú vrstvu dát

**P1, reprodukovaná cesta opätovného exportu.** `project.py:82`, `project.py:92`, `jobs.py:59`: opravy priamo menia jedinú tabuľku segmentov. Bežné uloženie vytvorí `.opravene`, ale neskoršie `project.export()` z tých istých dát regeneruje aj pôvodný export. Skúška zmenila obsah `prepis.txt` z pôvodného na opravený. V rozhraní je relevantná napríklad obnova po chybe exportu dokončeného projektu; bežné otvorenie hotového prepisu túto cestu samo nespúšťa.

**Riešenie:** oddeliť pôvodné výsledky modelu od upravenej revízie. Export musí explicitne zvoliť originál alebo konkrétnu revíziu. Pridať históriu úprav a zálohu pred migráciou databázy.

**Podmienka opravy:** uložiť opravu, znovu exportovať, simulovať zlyhanie SRT a zopakovať úlohu. Pôvodný text ostane identický; opravený export obsahuje poslednú uloženú revíziu.

### F05 Projekt a export sa ukladajú v oddelených krokoch

**P2, potvrdené poradím operácií.** `editor.py:229`: `project.edit()` sa potvrdí pred vytvorením exportov. Ak export zlyhá, dialóg hovorí o chybe uloženia, hoci databáza už obsahuje zmeny. TXT a SRT sú atómové jednotlivo, nie ako dvojica (`project.py:92`).

**Riešenie:** samostatne zobrazovať „Projekt uložený“ a „Export zlyhal“. Exportovať do novej revízie, dokončenú dvojicu publikovať až po úspechu oboch súborov a umožniť opakovanie bez prepisovania zvuku. Databáza má zostať autoritatívna.

**Podmienka opravy:** nasimulovať plný disk alebo zamknutý SRT; rozhranie presne ukáže, čo je uložené, a používateľ opraví export bez straty editácie.

### F06 Dve inštancie nemajú koordinované vlastníctvo fronty

**P1, riziko zo zdrojového kódu, nie nový test dvoch EXE.** `state.py:46`, `prepis.py:149`: atómový JSON zabraňuje polovičnému zápisu, ale nezabraňuje tomu, aby druhá inštancia prepísala novšiu frontu svojou staršou kópiou. Zámok sťahovania chráni sťahovanie, nie vlastníctvo fronty a všetky operácie s projektom.

**Riešenie:** pre osobnú desktopovú verziu jedna inštancia na profil; druhé spustenie odovzdá súbory prvej. Pre vedomú podporu viacerých inštancií zaviesť zamykanie projektov a transakčnú frontu s kontrolou revízie. Zdieľaný model nesmie byť súbežne odstránený inou inštanciou.

**Podmienka opravy:** otvoriť dve kópie, pridať rôzne súbory, upravovať rovnaký projekt a skúsiť odstrániť používaný model. Žiadne tiché prepísanie práce.

## Ďalšie technické a funkčné zistenia

| ID a priorita | Zistenie a dôkaz | Riešenie a overenie |
| --- | --- | --- |
| F07 P2 | Profil titulkov sa neukladá; hodnoty v `editor.py:101` sú pevné a nemajú sledovanie zmien. Reprodukované. | Uložiť profil do metadát projektu, obnoviť ho pri otvorení a označiť zmenu profilu ako neuloženú. Overiť zavretie bez explicitného exportu. |
| F08 P2 | Minimum titulku nie je zaručené a chýba upozornenie. Reprodukcia: posledný titulok 0,1 s pri minime 1 s. | Overovať všetky výsledné titulky, vysvetliť mäkké limity, nepredlžovať za koniec zvuku. Testovať krátke posledné titulky, prekryvy aj jedno dlhé slovo. |
| F09 P2 | `TranscriptBlocks.edit()` ničí a vytvára textové pole pri výbere bloku, čím sa stráca jeho lokálna história Undo. | Udržiavať históriu zmien nad dátami segmentov; Ctrl+Z musí fungovať aj po prechode na iný blok a späť. |
| F10 P2 | `Editor.save()` zapisuje všetky segmenty a exportuje oba súbory na UI vlákne. Stránkovanie rieši vykreslenie, nie veľké uloženie. | Ukladať len zmenené segmenty; exportovať nemennú revíziu mimo UI vlákna. Zmerať odozvu pri 10 000 a 100 000 úsekoch. Súčasný rozsah údajov sám nedokazuje konkrétnu dobu zamrznutia. |
| F11 P2 | V `jobs.py:63` a `playback.py:17` sa celý zvuk dekóduje do RAM. Model zostáva načítaný aj pri otvorení editora. | Disková PCM cache alebo mapovaný súbor, prehrávanie po blokoch, kontrola diskového priestoru a možnosť uvoľniť model. Jedna hodina mono 16 kHz float32 má približne 230,4 MB, desať hodín 2,304 GB iba na finálne vzorky; dekodér a model pridávajú ďalšiu pamäť. |
| F12 P2 | ASR beží v daemon vlákne; zastavenie čaká na návrat natívneho dekodéra či inferencie. `work.update()` čaká na `ack.wait()` bez limitu. | Samostatný lokálny ASR proces, potvrdenia s časovým limitom a identifikátorom úlohy, riadené zastavenie a bezpečné ukončenie neodpovedajúceho procesu. Obnovu oprieť o existujúce checkpointy. |
| F13 P2 | Fronta sa zapisuje pri každom prechode a aj pri ukladaní nastavení. `save_state()` spája dva samostatné JSON zápisy. | Oddeliť ukladanie nastavení od fronty; pri veľkej fronte použiť SQLite. Zjednotiť rollback pri chybe zápisu aj pre Odobrať a presun poradia, nielen pre pridanie. |
| F14 P2 | Revízia modelu sa porovnáva, ale načítava sa cez aktuálny názov/ref. `prepis.py:516` dosadí aktuálnu cache revíziu; projekt so staršou môže byť odmietnutý. | Na pokračovanie načítať presný uložený snapshot, ak existuje. Chýbajúcu revíziu pomenovať a ponúknuť jej stiahnutie alebo nový prepis. Automaticky nemiešať verzie. |
| F15 P2 | `job_settings()` deklaruje `beam_size=5`, ale slovenský adaptér pri `generate_kwargs` explicitne neurčuje rovnaký parameter. | Ukladať skutočné efektívne nastavenia osobitne pre backend; overiť ich v načítanom modeli. Nepredpokladať rovnaký algoritmus dvoch knižníc. |
| F16 P2 | `complete_snapshot()` dovolí aj cache bez verifikačného potvrdenia. Kontroluje súbory a JSON, nie vtedy hash všetkých váh. | Rozlíšiť „nájdený“ a „overený“, pridať kontrolu integrity starej cache. Pri každom štarte netreba znovu hashovať gigabajty; použiť overený manifest a kontrolu zmien. |
| F17 P2 | Správca modelov sa pri návrate na existujúcu kartu automaticky neobnoví; `manage_models()` vráti existujúci widget. | Obnoviť inventár po stiahnutí z hlavného prepisu, odstránení či zmene cache. Zachovať výber a posun zoznamu. |
| F18 P2 | Ovládač hlasov môže byť na zdrojovej inštalácii dostupný aj bez voliteľného `kaldi-native-fbank`; chýbanie sa prejaví až pri spustení. | Pred aktiváciou overiť runtime aj model, ukázať presný dôvod nedostupnosti. Bežný prepis musí fungovať bez hlasov. |
| F19 P2 | Dávkové percentá vážia rovnako krátky aj dlhý súbor; chybový súbor tiež dostane dokončenie postupu. ETA pri stagnácii odpočítava čas až k nule (`state.py:100`). | Rozlíšiť vybavenie položiek a prepis sekúnd; po dostupnom zistení dĺžok používať časovú váhu. Pri dlhom kroku zobraziť neistý odhad, nie nulu pri nedokončenej práci. |
| F20 P2 | Chybový dialóg v `work()` všeobecne odporúča internet alebo menší model aj pri iných príčinách. | Roztriediť chyby na vstup, disk, pamäť, model, GPU, sieť a konflikt projektu. Ku každej dať jednu konkrétnu akciu a rozbaliteľné podrobnosti. |
| F21 P2 | Pri tichu alebo nerečovom zvuku nový pipeline môže dokončiť prázdny projekt; starší `transcribe_file()` má explicitnú správu o nerozpoznanej reči. | Zaviesť výsledok „Reč sa nenašla“, počet úsekov a odporúčanie skontrolovať zdroj. Neoznačiť prázdny výsledok ako bežný úspešný prepis bez vysvetlenia. |
| F22 P2 | Editor nemá všeobecné otvorenie existujúceho projektu mimo fronty ani opravu presunutej cesty ku zvuku. | Pridať „Otvoriť projekt“ a „Nájsť pôvodnú nahrávku“ s kontrolou SHA-256. Odobratie položky z fronty tak nestratí praktický prístup k výsledku. |
| F23 P2 | `App.editors` sa dopĺňa, ale uzavreté editory sa z neho neodstraňujú. Ostávajú referencie aj na ich segmenty. | Po zavretí odstrániť editor z registra alebo spravovať jediný aktívny editor. Skúška opakovaného otvorenia veľkých prepisov musí sledovať spotrebu pamäte. |
| F24 P3 | Vyhľadávanie filtruje bloky, ale „Ďalší výskyt“ prechádza bloky, nie všetky jednotlivé zhody v texte. | Zvýrazniť zhody, zobraziť počet a podporiť prechod medzi konkrétnymi výskytmi. Názvy akcií musia zodpovedať správaniu. |
| F25 P3 | Pri seeku prehrávanie automaticky začne; chýba rýchlosť a výber výstupného zariadenia. | Explicitné pravidlo seeku počas pauzy, rýchlosti 0,75/1/1,25/1,5×, výber zariadenia a ošetrenie odpojenia slúchadiel. Klávesové ovládanie nesmie zachytiť medzeru počas písania. |

## Presnosť prepisu a rozlíšenia hlasov

V zmiešanom CZ/SK režime je premyslené porovnanie jazykov a tokenovo vážené skóre kandidátov. Prahy 0,60, 0,15 a 0,03 sú však nastavenia algoritmu, nie dokázaná úspešnosť. Úsek s dvoma jazykmi bez pauzy môže stále dostať jediný jazyk. Prípadné prekrývajúce sa okná treba zavádzať spolu s odstránením duplicitných slov a presným zachovaním časovej osi.

Finálne vydanie potrebuje reálny referenčný korpus podľa `eval/README.md`, doplnený o angličtinu a maďarčinu. Vyhodnotiť čistú reč, hluk, vzdialený mikrofón, ticho/hudbu, čísla, dátumy, mená, dialekty, krátke odpovede a zmenu jazyka vnútri vety. Výsledky publikovať po scenároch, nie iba jedným priemerom.

Merať WER/CER, správnosť mien a čísel, časovanie slov, jazykové prechody, reálny čas spracovania, špičkovú RAM/VRAM a čas načítania modelu. Zníženie WER môže zhoršiť mená alebo jazykové prechody; preto sledovať viac metrík. Prahy prijatia určiť po získaní východiskového merania a zmraziť pred ladením. Konkrétnu percentuálnu presnosť dnes nemožno poctivo sľúbiť.

**F26 P2:** `evaluate_mixed.py:62` nemá voľbu zariadenia a využije predvolené CPU. Návod síce hovorí o CPU/GPU, tento nástroj ich aktuálne nevie explicitne porovnať. Doplniť `--device`, verzie knižníc, commit modelu, parametre a hardware do výsledku. Navyše nástroj volá priamo `transcribe_mixed`, kým aplikácia má obal `transcribe_job`; pre finálne meranie pridať aj cestu identickú s produkčným spracovaním.

WeSpeaker v tejto aplikácii zoskupuje už existujúce ASR úseky. Nie je to presné rozdelenie hovoriacich pri ich striedaní uprostred úseku alebo prekryve. Zachovať označenie „Zoskupiť podobné hlasy“ a umožniť ručné rozdelenie/zlúčenie segmentov. `speakers.cluster()` postupne aktualizuje normalizované centrá; prípadnú zmenu na presný priebežný súčet embeddingov a prah treba hodnotiť na reálnych hlasoch, nie podľa estetickej čistoty vzorca.

Voliteľný slovník mien a odborných výrazov má pomáhať rozpoznaniu. Automatické „vylepšovanie“ výrokov generatívnym modelom nesmie potichu nahradiť doslovný prepis. Prípadné zhrnutie alebo štylistická úprava patrí do oddeleného výstupu s viditeľným pôvodom.

## Návrh dizajnu finálnej verzie

Zachovať názov ND TranskripThor a existujúce logo. Súčasná tmavomodrá identita je vhodný základ. Najväčší vizuálny prínos prinesie stabilné rozloženie, čitateľný stav a menej rovnocenných tlačidiel.

### Nahrávky a priebeh práce

V hornej lište má zostať logo, názov a prepínač vzhľadu. Hlavná plocha patrí zoznamu nahrávok. Jeden riadok ukazuje názov, dĺžku po jej zistení, stav, postup a dostupnú kontextovú akciu. Rovnaké názvy z rôznych priečinkov odlíši doplnková cesta. Stavy používajú text aj symbol, nie iba farbu.

Pred spustením nastavenia jasne hovoria „Pre nové prepisy“. Pri vybranej prerušenej úlohe samostatne zobraziť jej uložený model, jazyk a dostupnosť revízie. Používateľ tak nemusí z dialógu chyby zisťovať, prečo sa jeho nový výber nepoužil.

V spodnej stále dostupnej oblasti ponechať jednu hlavnú akciu „Spustiť prepis“ a počas práce „Zastaviť“. Ostatné akcie ako Nový prepis, Odobrať a Podrobnosti patria do kontextovej ponuky alebo vedľajšej skupiny. Súčasná dvojica „Otvoriť prepis“ a „Editor“ robí v bežnom prípade podobnú vec; zlúčiť ju.

Priebeh označovať podľa fázy: „Kontrolujem súbor“, „Pripravujem zvuk“, „Načítavam model“, „Prepisujem“, „Ukladám“. Pri sťahovaní zobrazovať MB a súbor x/y; pri prepise sekundy/minúty zvuku a zostávajúci odhad. Dve neoznačené podobné lišty nahradiť jasne pomenovanou aktuálnou nahrávkou a súhrnom dávky.

### Editor

Hlavný text musí mať najväčšiu časť okna. Názov projektu, stav uloženia a Uložiť sú stále viditeľné. Prehrávanie zostáva dole, nastavovanie titulkov a hovoriacich v bočnom alebo zbaliteľnom paneli. Kliknutie do textu má plynulo prejsť do úpravy bez rušivého skoku výšky bloku.

Pridať Ctrl+S, Ctrl+F, Ctrl+Z/Ctrl+Y, jasný fokus a príslušné popisy. Označenie aktuálne prehrávaného úseku má byť odlišné od označenia editovaného úseku. Automatické sledovanie prehrávania musí ísť vypnúť, aby neodťahovalo používateľa od korektúry.

Nastavenia exportu oddeliť od uloženia projektu. Ponúknuť TXT a SRT ako základ, následne VTT, DOCX a JSON. Mená hovoriacich či časové značky v TXT musia byť explicitné voľby. Ručné úpravy časov vyžadujú kontrolu poradia, hraníc a prekryvov.

### Vizuálne pravidlá

| Prvok | Navrhované pravidlo |
| --- | --- |
| Tmavý vzhľad | Zachovať pozadie `#11151D`, panely `#191F2A`, text `#EEF2FA`, sekundárny text `#B0BACB`, akcent `#92B5FF`. |
| Svetlý vzhľad | Zachovať pozadie `#F4F6FA`, biele panely, text `#202838`, akcent `#245BDB`. |
| Písmo | Segoe UI, základ približne 10–11 pt, prepis 11–12 pt s možnosťou zväčšenia. Nepoužívať zmenšenie textu ako opravu preplneného okna. |
| Odstupy | Jednotná stupnica 4/8/12/16/24 logických jednotiek. Vstupy a tlačidlá zjednotiť na približne 36–40 logických bodov výšky. |
| Tvary | Jeden mierny polomer rohov; nepreháňať tiene, priehľadnosť a dekorácie. |
| Stav | Hotovo, Čaká, Spracúva sa, Prerušené, Chyba a Reč sa nenašla, vždy s textom. |
| Fokus | Výrazný obrys aktívneho prvku, logické poradie Tab, slovné popisy šípok a tlačidiel prehrávania. |
| Prispôsobenie šírke | Na širokom okne zoznam a nastavenia vedľa seba; na úzkom okne pod sebou, nastavenia zbaliteľné. |
| Chyby | Krátka zrozumiteľná veta pri konkrétnej úlohe, tlačidlo riešenia a voliteľné technické podrobnosti. |

Pri kontrole farieb preveriť aj hover, disabled, fokus, výber textu, vysoký kontrast a čítačku obrazovky. Audit zdrojových farieb sám nepotvrdzuje prístupnosť. Súčasný editor vytvára vlastné bloky v Canvas; ich dostupnosť cez Narrator treba prakticky vyskúšať.

### Podpis vpravo dole

Požadované znenie je presne:

**Created by Daniel Návojský (ndxnraw) using Codex | 2026**

Je zapísané v centrálnej konštante `AUTHOR` v `src/ui.py:9`. Existujúce rozloženie v `ui_layout.py:62` ho umiestňuje vpravo dole. Zjednotený je aj podpis v README a návode.

Pre finálny dizajn má zostať diskrétny, čitateľný, približne 9 pt, s odstupom od okraja. Vľavo môže byť číslo verzie. Pri nedostatku šírky sa má zalomiť na dva riadky so zarovnaním doprava; nesmie vytlačiť hlavné ovládanie. Automaticky nemeníme rok, pretože požiadavka výslovne uvádza 2026. Autorstvo aplikácie patrí do rozhrania a informácií O aplikácii, nie do používateľových exportovaných prepisov.

Zmena je v zdrojových súboroch. Existujúce EXE a publikovaný ZIP neboli v rámci analytickej úlohy prestavané ani nahradené.

## Architektúra a programovacie jazyky

Odporúčam dve etapy: stabilizovať existujúci Python/Tk produkt a potom rozhodnúť o modernizácii rozhrania na základe jedného funkčného prototypu. ASR výkon už využíva natívne knižnice; faster-whisper je postavený nad CTranslate2. Prepis bežného riadiaceho kódu do C++ preto automaticky nezrýchli inferenciu. [Dokumentácia faster-whisper](https://github.com/SYSTRAN/faster-whisper).

| Varianta | Prínos pre TranskripThor | Cena a odporúčanie |
| --- | --- | --- |
| Python + Tk/ttk | Zachovanie všetkých existujúcich tokov a najmenší rozsah migrácie. | Najvhodnejšie pre najbližšie stabilné vydanie. Opraviť rozloženie, procesy a dáta; dizajn nemusí čakať na nový framework. |
| Python + PySide6, prípadne QML | Oficiálne Python väzby na Qt; QML umožňuje oddeliť deklaratívne rozhranie od Python služieb. | Odporúčaná možnosť pre väčšiu modernizáciu. Vyžaduje nové UI testy, balenie a posúdenie licenčných podmienok konkrétnych modulov. Najprv prototyp editora a DPI. |
| C# + XAML/WinUI 3 + Python proces | Natívne Windows rozhranie, samostatné ASR jadro. WinUI 3 podporuje desktopový vývoj v C# aj C++. | Dobrá alternatíva pri dlhodobej Windows špecializácii a skúsenosti s .NET. Pribudne distribúcia dvoch runtime prostredí a komunikačné rozhranie. |
| TypeScript + webové rozhranie + lokálny backend | Vhodné pri skutočnom cieli zdieľať rozhranie s webovou aplikáciou. | Pre súčasný čisto desktopový produkt zatiaľ neodporúčam; migrácia a balenie pribudnú bez preukázanej potreby. |
| Rust alebo C++ pre vlastné jadro | Cielené nízkoúrovňové optimalizácie, ak profilovanie nájde konkrétny problém. | Až po meraní; nezačínať paralelnou implementáciou fungujúceho ASR. |

Technické možnosti Qt a WinUI sú overené v oficiálnych zdrojoch; voľba pre tento projekt je architektonické odporúčanie, nie výsledok výkonového porovnania: [Qt for Python](https://doc.qt.io/qtforpython-6/), [Microsoft WinUI 3](https://learn.microsoft.com/en-us/windows/apps/winui/winui3/).

Navrhované hranice systému: rozhranie → aplikačné služby → úlohy a projekty → samostatný ASR proces. Sťahovanie ostáva v oddelenom procese. SQLite vlastní jasne určená služba; editor zapisuje revízie a export číta nemenný snapshot.

Ak sa pridá druhý jazyk, použiť verziovaný lokálny protokol cez štandardné vstupy/výstupy alebo pomenované kanály. Každá správa má ID úlohy, typ, verziu a dáta; logy idú oddelene. Zvuk neposielať ako veľké JSON dáta, odovzdať cestu k lokálnemu súboru a jeho overenú identitu. Pre lokálnu aplikáciu nie je potrebné otvárať sieťový server.

Presun Python modulov zo `src` do bežnej štruktúry `src`, testov do `tests` a zostavovacích postupov do `packaging` uľahčí údržbu. Najskôr však oddeliť dátové rozhrania; hromadné premenovanie a súčasná zmena frameworku by sťažili hľadanie regresií.

## Distribúcia súkromie a údržba

**F27 P2:** závislosti nie sú úplne uzamknuté vstupným inštalačným súborom. `verzie-zostavenia.txt` je inventár konkrétneho prostredia, nie automaticky používaný lock so všetkými hashmi. Finálna zostava má vzniknúť v čistom prostredí z pevne určeného Pythonu, balíkov a modelových revízií. Sťahovanie zasahuje do interných API Hugging Face Hub, preto aktualizáciu jeho presne viazanej verzie musí sprevádzať integračný test transportu.

**F28 P2:** `zostavit.cmd` pri zlyhaní testov správne zastaví zostavenie. Súčasná sada však stále obsahuje známe zlyhanie rozloženia. Pred finálnym vydaním ho opraviť; neznižovať kontrolu odstránením testu. Historický balík s 88/89 testmi nepovažovať za úplne zelený referenčný výsledok.

**F29 P2:** verejný návod mieša staršie informácie o 58 testoch a verzii 2.1.0 s aktuálnou verziou a uvádza starý lokálny priečinok `release210`. Poznámky 2.1.3b obsahujú aj historické „Vydanie nebolo publikované“, hoci README už odkazuje na vydanie. Pri finálnom balení vytvoriť jeden aktuálny prehľad funkcií, obmedzení a overenia a historické poznámky označiť ako stav v čase ich vzniku.

**F30 P2:** overiť pribalené oznamy a licencie knižníc aj modelov, vytvoriť súpis závislostí, SHA-256 archívu a reprodukovateľný manifest zostavy. Toto je návrh distribučného postupu; audit neurčuje kompletné právne podmienky každého balíka. Zvážiť podpis finálneho EXE dôveryhodným podpisovacím certifikátom a overiť výslednú distribúciu na čistom Windows.

Zvážiť ľahší základný balík a samostatný rozšírený balík s KInIT/PyTorch. Súčasný zostavovací predpis zbiera oba veľké modelové runtime systémy. Presnú úsporu veľkosti treba zmerať zostavením; nesľubovať ju odhadom. Používateľ musí vopred rozumieť, ktorý balík potrebuje, bez ručnej inštalácie Pythonu.

Lokálne spracovanie neznamená šifrovanie. SQLite a TXT obsahujú čitateľné prepisy, fronta obsahuje cesty. Nastavenia majú vysvetliť umiestnenie dát a rozlišovať „Odobrať z fronty“, „Odstrániť projekt“ a „Odstrániť model“. Automatický diagnostický balík nemá obsahovať text ani audio; používateľ musí vidieť, aké cesty a technické údaje zdieľa. Offline režim overiť aj sieťovým meraním po stiahnutí modelu, nie iba kontrolou nastaveného prepínača.

## Poradie realizácie

| Etapa | Výstup | Kritérium dokončenia |
| --- | --- | --- |
| A Ochrana práce | Opravy F01, F03, F04, F05, F06; regresné testy. | Žiadna strata rozpísaného textu, bezpečné prerušenie vo všetkých fázach, nemenný originál a presný stav uloženia/exportu. |
| B Dostupné ovládanie | Oprava F02, responzívne nastavenia, dostupné akcie, podpis, klávesnica. | Celá existujúca aj nová sada prejde; praktické skúšky všetkých kariet v oboch témach a pri 100–200 %. |
| C Editor a dlhé nahrávky | Ukladanie profilu titulkov, história úprav, pamäťové limity, uvoľňovanie editorov/modelu, riadený worker. | Dlhý prepis sa otvorí, upraví, uloží a obnoví bez straty dát; nameraná pamäť a odozva. |
| D Presnosť a hardware | Referenčný korpus, merania modelov, reálne GPU testy, systémový drop. | Zverejnené výsledky so scenármi a hardvérom; známe obmedzenia majú konkrétne podmienky. |
| E Kandidát na vydanie | Čisté zostavenie, balík, návody, kontrolné súčty, licenčné oznamy. | Nový používateľ bez Pythonu zvládne celý tok; offline prepis funguje po získaní modelov. |
| F Väčšia modernizácia | Funkčný prototyp PySide6/QML alebo WinUI nad stabilným jadrom. | Porovnanie DPI, dostupnosti, práce s textom, pamäte, času štartu a balenia; výber až podľa výsledku. |

Časový odhad bez rozhodnutia o migrácii rozhrania a bez nameraného korpusu by bol nepresný. Každá etapa má preto konkrétny prijateľný výstup. Väčšiu migráciu oddeliť od opráv ohrozujúcich dáta.

## Skúšky finálneho kandidáta

1. Čistý Windows bez Pythonu, bežné používateľské oprávnenia, prvé stiahnutie modelu a opätovné spustenie bez internetu.
2. Jeden aj viac súborov cez dialóg a Prieskumník: prázdna aj naplnená fronta, Unicode, dlhé cesty, duplicity, priečinky a nepodporovaný obsah.
3. Zastavenie a pád pri každej fáze, vrátane inicializácie, exportu a sťahovania; po obnove žiadne zdvojené ani vynechané uložené úseky.
4. Chýbajúci alebo presunutý zdroj, zmenený obsah, stará revízia modelu, poškodená databáza, cache a nastavenia.
5. Plný disk, zápis bez oprávnenia, zamknutý výstup a krátke prerušenie siete. Overiť pravdivý stav uloženia.
6. CPU, reálne NVIDIA GPU, nedostatok VRAM, zlyhanie počas inferencie a explicitne potvrdený prechod na CPU. Osobitne oba ASR backendy.
7. Editor počas rozlíšenia hlasov, viacstranový prepis, vyhľadávanie, Undo/Redo, zmena tém, prehrávanie, odpojenie zvukového zariadenia a zatvorenie.
8. TXT/SRT zachovajú všetky slová a Unicode; časová os je platná, originál ostane zachovaný a každý porušený mäkký limit je vysvetlený.
9. Viac monitorov, vysoké DPI, minimalizovanie/obnovenie, klávesnica, Narrator a vysoký kontrast. Podpis aj hlavné akcie zostanú dostupné.
10. Reálne merania korpusu oddelene od mockov a syntetického zvuku; záznam presných verzií a opakovanie na rovnakom hardvéri.

## Stav vykonaných zmien

V tejto úlohe je implementovaná zmena podpisu v `src/ui.py`, README a návode. Ostatné zásahy sú konkrétny návrh realizácie, nie deklarované opravy. Existujúca zostava 2.1.3b nebola prestavaná, verzia nebola zvýšená a nič nebolo publikované.

Pracovné dôkazy: `work/audit-20261008-tests.log`, `work/audit-20261008-repro.json` a reprodukčný postup `work/audit_repro.py`. Ide o lokálne pomocné súbory v ignorovanom priečinku; podstatné výsledky sú uvedené vyššie a zostávajú súčasťou tejto dokumentácie.
