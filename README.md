# ND TranskripThor

Slovensky · [English](README.en.md)

Program na prepis nahrávok do textu a titulkov pre Windows. Nahrávky sa spracúvajú priamo vo vašom počítači.

Podporuje slovenčinu, češtinu, angličtinu a maďarčinu. Prepis môžete upraviť v editore a uložiť ako TXT, SRT, VTT, DOCX alebo JSON.

## Stiahnutie a spustenie

**[Stiahnuť pre Windows 64-bit](https://github.com/ndxnraw/TranskripThor/releases/download/v1.0.0/ND-TranskripThor-v1-Windows-x64.zip)** · [Release v1](https://github.com/ndxnraw/TranskripThor/releases/tag/v1.0.0)

Rozbaľte celý ZIP a spustite **ND TranskripThor.exe**. Priečinok `_internal` nechajte vedľa programu. Python netreba inštalovať.

Pri prvom použití sa stiahne potrebný model. Potom môžete prepisovať aj offline.

## Použité projekty

- Prepis: [Whisper](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [CTranslate2](https://github.com/OpenNMT/CTranslate2), [Transformers](https://github.com/huggingface/transformers), [PyTorch](https://github.com/pytorch/pytorch), [Hugging Face Hub](https://github.com/huggingface/huggingface_hub).
- Detekcia reči a hlasy: [Silero VAD](https://github.com/snakers4/silero-vad), [WeSpeaker](https://github.com/wenet-e2e/wespeaker), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [kaldi-native-fbank](https://github.com/csukuangfj/kaldi-native-fbank).
- Zvuk: [PyAV](https://github.com/PyAV-Org/PyAV), [FFmpeg](https://github.com/FFmpeg/FFmpeg), [sounddevice](https://github.com/spatialaudio/python-sounddevice), [NumPy](https://github.com/numpy/numpy).
- Rozhranie: [Qt / PySide6](https://github.com/qtproject/pyside-pyside-setup), [Pillow](https://github.com/python-pillow/Pillow). Staršie rozhranie používa [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) a [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2).
- Zostavenie: [PyInstaller](https://github.com/pyinstaller/pyinstaller).

Slovenský model [KInIT Whisper](https://huggingface.co/kinit/whisper-large-v3-sk) je dostupný na Hugging Face.

[Návod](docs/NAVOD.md) · [Vývoj](docs/DEVELOPMENT.md)
