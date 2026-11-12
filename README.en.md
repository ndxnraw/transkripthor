# ND TranskripThor

[Slovensky](README.md) · English

A Windows app that turns recordings into text and subtitles. Recordings are processed on your computer.

Supports Slovak, Czech, English and Hungarian. You can edit the transcript and export it as TXT, SRT, VTT, DOCX or JSON.

## Download and run

**[Download for Windows 64-bit](https://github.com/ndxnraw/TranskripThor/releases/download/v1.0.0/ND-TranskripThor-v1-Windows-x64.zip)** · [Release v1](https://github.com/ndxnraw/TranskripThor/releases/tag/v1.0.0)

Extract the entire ZIP and run **ND TranskripThor.exe**. Keep the `_internal` folder next to the app. You don't need to install Python.

The required model downloads on first use. After that, you can transcribe offline.

Access to this private repository is required to download the app.

## Projects used

- Transcription: [Whisper](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [CTranslate2](https://github.com/OpenNMT/CTranslate2), [Transformers](https://github.com/huggingface/transformers), [PyTorch](https://github.com/pytorch/pytorch), [Hugging Face Hub](https://github.com/huggingface/huggingface_hub).
- Speech detection and voices: [Silero VAD](https://github.com/snakers4/silero-vad), [WeSpeaker](https://github.com/wenet-e2e/wespeaker), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [kaldi-native-fbank](https://github.com/csukuangfj/kaldi-native-fbank).
- Audio: [PyAV](https://github.com/PyAV-Org/PyAV), [FFmpeg](https://github.com/FFmpeg/FFmpeg), [sounddevice](https://github.com/spatialaudio/python-sounddevice), [NumPy](https://github.com/numpy/numpy).
- Interface: [Qt / PySide6](https://github.com/qtproject/pyside-pyside-setup), [Pillow](https://github.com/python-pillow/Pillow). The older interface uses [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) and [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2).
- Build: [PyInstaller](https://github.com/pyinstaller/pyinstaller).

The Slovak [KInIT Whisper model](https://huggingface.co/kinit/whisper-large-v3-sk) is available on Hugging Face.

[User guide (Slovak)](docs/NAVOD.md) · [Development (Slovak)](docs/DEVELOPMENT.md)
