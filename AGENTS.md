# ND TranskripThor – pravidlá práce

- Podporovaná platforma je Windows x64, Python 3.12 s Tk. Neobnovovať Linux
  ani odstránené ASR backendy. Zachovať faster-whisper a slovenský KInIT.
- `src/` je jediný zdroj aplikácie; `src/assets/` a `src/locales/` patria
  do EXE. `tests/` obsahuje všetky regresie; `packaging/` balenie;
  `scripts/` opakovateľné nástroje; `requirements/` vstupy, constraints a locky.
- Používať projektové `.venv`: `scripts/setup.ps1`, `run.ps1`, `test.ps1`,
  `build.ps1`. Testovanie musí objaviť aspoň 197 testov, dokončiť celý beh
  a nemať preskočené testy. Mock ASR nie je skutočný test modelu/GPU.
- Cesty odvodzovať od súboru, projektu alebo používateľského profilu.
  Žiadne hardcoded mená počítačov, používateľov, runtime asistenta, `work/`
  ani balíky mimo `.venv`. Podporovať medzery a Unicode v cestách.
- Autoritatívna verzia je `src/version.py`; Windows metadata sa generujú
  z nej. V SYNC nemeníme verziu, nevytvárame tag ani GitHub Release.
- Závislosti meniť cielene. Locky obsahujú celý deklarovaný reťazec a SHA-256
  Windows wheelov, nie export z cudzieho prostredia. Postup je v DEVELOPMENT.
- Pred presunmi/mazaním uložiť lokálnu zálohu mimo Gitu; zachovať staged
  a unstaged rozlíšenie. Nahrávky, projekty, profily a modely fyzicky nemažeme.
- `outputs/`, `work/`, `cache/`, `.venv/`, `build/`, `dist/` sú lokálne.
  Nepublikovať tokeny, nastavenia, nahrávky, exporty, váhy ani súkromné logy.
- Pred commitom skontrolovať celý diff a `git diff --check`, stage konkrétne
  cesty. Pred pushom overiť remote `ndxnraw/TranskripThor`, vzdialený HEAD
  a presný kandidát z čistého klonu, vrátane nového Windows EXE.
- Povinné testy/build blokujú push do main. Rešpektovať ochranu vetiev;
  bez force push, reset --hard, hromadného clean, prepisu histórie/tagov.
- Aktuálny stav udržiavať v `docs/STATUS.md`. Staršie opravy sú historické
  záznamy, nie dôkaz úspechu aktuálneho commitu. Nevytvárať duplicitné audity.
