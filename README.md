# ND TranskripThor

**ND TranskripThor** je aplikácia pre Windows na lokálny prepis zvukových nahrávok do textu a titulkov. Nahrávky ani prepisy neposiela na externé služby a nemá minútové kvóty.

Podporuje slovenčinu, češtinu, angličtinu, maďarčinu aj zmiešané československé nahrávky. Ponúka dávkové spracovanie, editor s prehrávaním zvuku a export do TXT a SRT. Aktuálny vývojový kód ponúka anglické a slovenské rozhranie so svetlým aj tmavým vzhľadom.

## Stiahnutie a spustenie

**[Stiahnuť ND TranskripThor 2.1.3b pre Windows](https://github.com/ndxnraw/TranskripThor/releases/download/v2.1.3b/ND-TranskripThor-2.1.3b-Windows.zip)**

1. Rozbaľte celý ZIP.
2. Spustite **ND TranskripThor.exe**. Priečinok `_internal` ponechajte vedľa neho; Python netreba inštalovať.
3. Pridajte nahrávku, vyberte jazyk a model a spustite prepis.

Modely nie sú pribalené. Pri prvom použití sa vybraný model stiahne; následne môžete pracovať offline. Rýchlosť a presnosť závisia od modelu, počítača a kvality nahrávky. Výsledný text odporúčame skontrolovať.

[Prehľad vydaní](https://github.com/ndxnraw/TranskripThor/releases) · [Používateľský návod](docs/NAVOD.md) · [Vývoj na ďalšom počítači](docs/DEVELOPMENT.md)

Vývojový zdroj obsahuje novšie opravy než publikované EXE, pri zachovaní verzie 2.1.3b. [Aktuálny stav a hranice overenia](docs/STATUS.md).

Zo zdrojov na Windows x64 s Python 3.12: `scripts/setup.ps1`, potom `scripts/run.ps1`.

Created by Daniel Návojský (ndxnraw) using Codex | 2026
