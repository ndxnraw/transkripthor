# F14/F15 – presná revízia a efektívne nastavenia modelu

Historický dokument pre 2.1.3b / vývojové opravy. Posledný evidovaný zápis pred zosúladením návodov: 2026-10-14 (f5377db); nejde o dodatočne určený dátum testovania. Počty testov, cesty a stav publikovania nižšie platia iba pre opísanú historickú zostavu, nie aktuálny pre-release. Aktuálny prehľad: [poznámky k pre-release](RELEASE-NOTES.md).

Verzia zostáva **2.1.3b**. Bez publikovania a bez prepisovania vývojového bodu návratu F12. Predchádzajúce rozpracované zmeny zostali zachované.

## Zistenie a oprava

Po F12 sa revízia stále vyberala z aktuálneho odkazu cache ešte pred spracovaním projektov. Načítanie modelu navyše používalo jeho názov (`main`, pri KInIT `v2.0`), nie uložený snapshot. KInIT mal deklarovaný `beam_size=5`, ale jeho generovanie preberalo implicitné parametre modelu.

Teraz sa nastavenia čítajú z každého pokračujúceho projektu osobitne, aj pri dávke s rôznymi modelmi, jazykmi a revíziami. `model_revision` určuje konkrétny lokálny adresár `snapshots/<commit>`. faster-whisper dostane tento adresár; KInIT z neho načíta procesor aj váhy. Identifikátor modelu v pamäti obsahuje revíziu. Zmena revízie uvoľní starý model pred načítaním nového, opakované použitie rovnakej revízie ho nenačíta znova.

Ak snapshot chýba:

- Offline režim vysvetlí presný model a commit a ponúkne postup: zapnúť online režim, obnoviť cache zo zálohy alebo spustiť nový samostatný prepis.
- Pri pokračovaní vybranej položky online aplikácia ponúkne stiahnutie presnej revízie. Odmietnutie nič nespustí. Dávka používa rovnaký mechanizmus sťahovania v povolenom online režime pre každú položku.
- Sťahovanie používa uložený commit a overí, že server vrátil práve tento commit. Nezmení aktuálny odkaz `main` ani `v2.0`. Zachováva existujúce overovanie súborov, časové limity a obnovu prenosu.
- Nedostupná revízia sa nenahradí najnovším modelom. Chyba obsahuje postup pre opakovanie alebo nový projekt. Starší projekt bez zaznamenanej revízie sa bezpečne odmietne namiesto predstierania reprodukovateľnosti.

## Uložené parametre

Nové projekty majú v `settings.decoding` kontrakt konkrétneho backendu:

- faster-whisper: serializované predvolené parametre nainštalovanej metódy `WhisperModel.transcribe`, doplnené skutočnými voľbami aplikácie: `beam_size=5`, `task=transcribe`, `word_timestamps=True`, `condition_on_previous_text=False`, `vad_filter=False` (VAD už vykonala príprava). Zahŕňa teploty, best-of, penalizácie, prahy, prompt, potláčané tokeny a ostatné dostupné voľby. Pri pokračovaní sa použijú uložené hodnoty, nie nové implicitné hodnoty knižnice. Rovnaký kontrakt používa aj CZ/SK double-pass.
- KInIT/Transformers: celý `generation_config` načítaného modelu a explicitné argumenty `language=sk`, `task=transcribe`, `num_beams=5`, `do_sample=False`, `condition_on_prev_tokens=False`, výstup časov slov. Uložený config sa pri inferencii obnoví; explicitné argumenty majú prednosť. Hodnota piatich lúčov je tak skutočne použitá. Algoritmy dvoch backendov nie sú považované za totožné.

Zariadenie, požadovaný typ výpočtu, dostupný skutočný compute type CTranslate2 a verzie relevantných knižníc sa zapisujú oddelene do `execution_history` s indexom nasledujúceho checkpointu. Zmena CPU/GPU ostáva povolená a GPU fallback vyžaduje potvrdenie. Zmena runtime sa zaznamená a vysvetlí v logu; neprepíše pôvodné nastavenia ani uložený text. História sa dopĺňa iba pri zmene runtime, nie pri každom segmente.

Staršie projekty s revíziou, ale bez úplného dekódovacieho kontraktu používajú historickú cestu aplikácie: faster-whisper pôvodné explicitné voľby a KInIT implicitné nastavenia daného snapshotu. Dostanú upozornenie a `legacy_decoding_unknown=True` v novom zázname runtime. Pôvodné `settings` sa spätne nedopĺňajú odhadmi; neznáme parametre minulého behu nemožno spoľahlivo obnoviť.

## Overenie

Nové testy pokrývajú výmenu aktuálneho odkazu A → B pri načítaní A, kľúč modelu v pamäti, obidva backendy, chýbajúci snapshot offline/online, potvrdenie a odmietnutie sťahovania, dávku projektov s vlastnými nastaveniami, skutočne odovzdané dekódovacie parametre, obnovenie po checkpointe a záznam zmeny zariadenia. Lokálny HTTP test s malými dátami overuje sťahovanie presného commitu oboch formátov bez prepísania aktuálneho odkazu.

Skutočný offline prepis syntetickej nahrávky cez samostatný ASR proces s Tiny/CPU vytvoril tri segmenty a uložený dekódovací kontrakt. Samostatná skúška načítala reálny snapshot Tiny `d90ca5fe260221311c53c58e660288d3deb8d356` z izolovanej kópie cache, ktorej `main` bol zmenený na iný commit. Opätovný export zachoval text aj nastavenia. Ide o prevádzkové overenie, nie meranie presnosti rozpoznávania. Protokoly sú v `work/tests-f14-*.log`, `work/source-F14/process-diagnostic.json` a `work/verify-f14-revision.json`.

Prvý úplný beh skončil predčasne počas existujúceho Tk testu editora bez súhrnu; samostatné opakovanie testov editora a nových scenárov prešlo (15 testov, 12,817 s). **Záverečná kompletná sada prešla: 196 testov za 166,176 s**, protokol `work/tests-f14-final.log`. Predbežná cielená sada mala 48 úspešných testov. `git diff --check` nehlási chyby bielych znakov.

## Rozsah a obmedzenia

Zmeny: `asr_batch.py`, `speech_models.py`, nový `decode_settings.py`, `model_catalog.py`, `download_transport.py`, `download_worker.py`, `jobs.py`, `mixed_language.py`, `prepis.py`, katalógy `locales/en.json` a `locales/sk.json`; nové `test_revision_settings.py` a doplnené testy prenosu a procesu.

Nie je potrebná nová externá závislosť. Existujúci PyInstaller postup zahrnie nový importovaný modul. V tejto úlohe sa nevytvára nové EXE; vývojová zostava F12 zostáva nedotknutá. Zmeny sa spúšťajú zo zdrojov cez existujúce Python prostredie (`src/prepis.py`).

Reálne GPU a plný KInIT model neboli spustené; odovzdanie ich nastavení sa overuje pomocou simulácií. Sťahovanie historického commitu z verejného servera nebolo potrebné ani overované; overený bol lokálny HTTP prenos. Revízia a parametre zlepšujú reprodukovateľnosť, nezaručujú však bitovo rovnaký text pri zmene hardvéru, knižníc alebo nedeterministických operáciách. Úplné parametre nezaznamenané starými verziami sa spätne nevymýšľajú.
