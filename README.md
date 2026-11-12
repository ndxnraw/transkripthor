# ND TranskripThor — Release v1

Lokálny prepis zvuku a videa pre Windows x64. Nahrávky zostávajú vo vašom počítači, bez odosielania na server a bez minútových kvót.

**[Stiahnuť Release v1](https://github.com/ndxnraw/TranskripThor/releases/tag/v1.0.0)** · [ZIP pre Windows x64](https://github.com/ndxnraw/TranskripThor/releases/download/v1.0.0/ND-TranskripThor-v1-Windows-x64.zip)

Rozbaľte celý ZIP a spustite **ND TranskripThor.exe**. Priečinok `_internal` nechajte vedľa programu; Python netreba inštalovať. Kontrolný súčet SHA-256 je priložený k vydaniu. Súkromný repozitár vyžaduje prihlásenie a prístup aj pri sťahovaní.

Hlavná aplikácia používa **QML/Qt Quick**. Bežný postup je jednoduchý: pridať nahrávku → vybrať jazyk a kvalitu → spustiť prepis → upraviť výsledok. Bez prepínania kariet a povinnej návštevy správcu modelov.

- Slovenčina, čeština, angličtina, maďarčina, automatická detekcia a zmiešaný CZ/SK režim.
- faster-whisper a slovenský KInIT; chýbajúci model sa pripraví pri prvom použití. Váhy nie sú súčasťou ZIPu, po stiahnutí možno pracovať offline.
- Editor s prehrávaním, vyhľadávaním, históriou úprav, hovoriacimi a úpravou časov; ochrana neuloženého textu a zachovanie originálu.
- TXT, SRT, VTT, DOCX a JSON; svetlá/tmavá téma a podpora vysokého kontrastu Windows.

[Návod](docs/NAVOD.md) · [Poznámky k vydaniu](docs/RELEASE-NOTES.md) · [Aktuálny stav a hranice overenia](docs/STATUS.md) · [Vývoj](docs/DEVELOPMENT.md)

Created by Daniel Návojský (ndxnraw) using Codex | 2026
