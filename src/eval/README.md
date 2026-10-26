# Dôveryhodné lokálne meranie kvality (F26)

V repozitári nie je oprávnená reálna nahrávka s ručne overenou referenciou.
Príklad nie je korpus. Testy používajú simulácie; syntetický Microsoft Filip
nie je dôkaz presnosti reálneho CZ/SK rozhovoru. Žiadne skóre modelov zatiaľ
neuvádzame. Referencie, projekty merania a výsledky patria mimo Gitu.

## Korpus

Použite vlastné nahrávky so súhlasom účastníkov alebo vhodnou licenciou.
Každý záznam schema=2 musí mať jedinečné `id`, relatívnu/absolútnu cestu
`audio`, `sha256` súboru, `duration` v sekundách, `kind: real`,
`authorized: true`, neprázdne `rights`, `reviewed_by`, `tags`, `language`
(cs/sk/en/hu/cs-sk) a ručne skontrolované `segments`. Prázdny zoznam segmentov
znamená referenčné ticho. Vyhlásenie oprávnenia je zodpovednosť autora korpusu;
nástroj nevie automaticky potvrdiť licenciu ani pravdivosť referencie.

Segmenty majú start/end/text/language; jazykové prechody označte aj uprostred
vety, bez prekladu. Časy musia byť konečné, kladné intervaly bez prekryvov
v hraniciach nahrávky. Prekrývajúce sa hlasy tento formát nehodnotí.
Voliteľné `words` obsahujú word/start/end a musia zodpovedať celému textu
segmentu. Bez ručne overených slov nie je možné merať presnosť časovania slov.
Voliteľné `entities` obsahujú kind (`name`/`number`), text/start/end. Napríklad
`{"kind":"name","text":"Novák","start":2.0,"end":3.0}`. Text musí byť
v referencii daného intervalu. Čísla zapisujte podľa vopred určenej doslovnej
konvencie; nástroj nezamieňa „dvanásť“ a „12“ ani automaticky nepozná mená.

Odtlačok získate pomocou `Get-FileHash -Algorithm SHA256`; do manifestu vložte
malé hexadecimálne znaky. Validácia odmieta duplicity ID aj rovnakých audiodát,
chýbajúce súbory, nesúhlas odtlačku, neplatné časy, entity a neúplné oprávnenie.
Pri inferencii sa referenčná dĺžka navyše porovná s presne dekódovaným PCM
(tolerancia 50 ms) a znovu sa overí odtlačok. Samostatná validácia neprehráva
a nedekóduje audio, takže nepreukazuje jeho počuteľnú kvalitu.

Potrebné sú aspoň dve nezávislé nahrávky pre každý scenár: čisté cs/sk/en/hu,
CZ→SK→CZ aj SK→CZ→SK, krátke odpovede v kontexte, hluk, vzdialený mikrofón,
ticho/hudba, mená, čísla/dátumy, dialekty a zmena jazyka uprostred vety.
Čisté ukážky 30–60 s, dialógy 1–3 minúty, aspoň 10 prechodov uprostred viet.
Prekryvy hlasov a diarizácia potrebujú vlastnú referenciu a inú metriku.

## Spustenie

Použite projektové `.venv` vytvorené `scripts/setup.ps1`. Nástroj nikdy
nesťahuje modely: najprv ich pripravte správcom modelov. Vyžaduje presný
40-znakový commit každého modelu, nie pohyblivé main/v2.0. KInIT možno merať
len pri slovenčine; zmiešaný režim vyžaduje viacjazyčný model.

```powershell
.\.venv\Scripts\python.exe src/evaluate_mixed.py work/manifest.json --validate-only
.\.venv\Scripts\python.exe src/evaluate_mixed.py work/manifest.json --cache "$env:LOCALAPPDATA/LokalnyPrepis/models" --models small --revision small=SEM_VLOZTE_PRESNY_40_ZNAKOVY_COMMIT --device cpu --output outputs/meranie-cpu-01
```

Pre GPU použite `--device cuda` a nový priečinok. CPU je predvolené; pri
GPU chybe sa nikdy potichu neprejde na CPU. `--timeout` ohraničuje každý
podproces (predvolene 7200 s). Výstupný priečinok musí byť nový. Po chybe
ostáva report s chybou a hotovými výsledkami; návratový kód je nenulový.
Lokálne worker.log/request.json/projekt môžu obsahovať súkromné údaje.
Nepublikujte ich bez kontroly. Každé opakovanie spustite do nového priečinka.

Každá dvojica model/nahrávka beží v novom lokálnom procese cez produkčné
`ensure_model`, `ModelManager.get`, `effective_settings`, `job_settings` a
`transcribe_job`: diskové PCM, VAD, delenie, jazykové rozhodovanie, checkpointy
aj export originálu. GUI/fronta a IPC watchdog aplikácie sa nemerajú;
benchmark má vlastný pevný timeout. Neexistuje paralelná ASR implementácia.
Samostatný proces znamená nové načítanie modelu; OS disková cache sa nemaže.
Načítanie sa vykazuje osobitne od prípravy/prepisu/exportu. Aspoň tri behy
na tom istom hardvéri umožnia vidieť variabilitu, nie iba najlepší výsledok.

## Význam výsledkov

`report.json` obsahuje odtlačok manifestu, výsledky a scenáre oddelene pre
model/revíziu/zariadenie. Ukladá presný snapshot, všetky dostupné verzie
balíkov, Python/OS/CPU/RAM/GPU/driver, odtlačky zdrojov, efektívne dekódovacie
parametre, segmentačné nastavenia, runtime/compute type a fázy spracovania.
Nie je to reprodukovateľnosť bit po bite medzi odlišnými GPU/ovládačmi.

- WER je Levenshtein nad NFC/casefold Unicode slovami bez interpunkcie.
  CER je nad rovnakým normalizovaným textom so zjednotenými medzerami.
  Prázdna referencia má WER/CER null a samostatný počet vložených slov.
- Mená/čísla: podiel anotovaných výskytov, ktorých doslovná tokenová sekvencia
  chýba v hypotéze prekrývajúcej referenčné okno. Nie je to NER ani sémantická
  ekvivalencia; nepočíta neanotované falošné entity. Dlhé hypotetické segmenty
  môžu tolerovať nesprávne umiestnený výskyt, preto používajte úzke anotácie
  a kontrolujte uložený doslovný výstup. Bez anotácií je výsledok null.
- Jazyk: časovo vážené správne pokrytie referenčných úsekov. Prechody porovnávajú
  smer jazyka a čas s toleranciou 0,5 s; každý nájdený prechod sa použije najviac
  raz, v časovom poradí. Uvádza sa precision/recall a absolútna časová odchýlka.
- Časovanie slov: MAE začiatkov/koncov iba presne zhodných tokenov zarovnaných
  SequenceMatcherom; zároveň počet zhodných a všetkých referenčných slov.
  Chybne rozpoznané slová sa nesmú skrývať iba nízkym MAE. Opakované slová
  môžu mať nejednoznačné zarovnanie; nejde o nútené fonetické zarovnanie.
- RTF je čas produkčnej úlohy vrátane prípravy a exportu/dĺžka zvuku, bez
  načítania modelu. RAM je OS peak working set izolovaného procesu do konca
  produkčného exportu, pred skórovaním. Zahŕňa importy a model; nejde o VRAM.
- VRAM je vzorkovaná per-process hodnota NVIDIA raz za sekundu (dolný odhad
  špičky, nie zaručené maximum). WDDM alebo chýbajúce nvidia-smi ju nemusia
  sprístupniť: potom je null/unavailable. Nezamieňa sa s celkovou obsadenosťou GPU.

Scenáre uvádzajú úspechy aj chyby, vážený WER/CER, entity, prechody, časovanie,
RTF a pamäť. Jeden záznam s viacerými tags patrí do viacerých scenárov; ich
počty nesčítavajte ako nezávislé nahrávky. Chyby nemajú falošné nulové skóre.
Prahy kvality stanovte a zmrazte až po získaní skutočného východiskového korpusu.
