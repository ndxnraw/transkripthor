"""Overenie závislostí Windows zostavy. Voliteľné hlasy neblokujú bežný prepis."""
def check():
    import sys
    from pathlib import Path
    variant = Path(getattr(sys, '_MEIPASS', '')) / 'distribution-variant.txt'
    basic = getattr(sys, 'frozen', False) and variant.is_file() and variant.read_text().strip() == 'basic'
    if not basic:
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    import faster_whisper
    import sounddevice
    import tkinterdnd2
    print('Local model runtimes available; distribution:', 'basic' if basic else 'extended')

if __name__ == '__main__':
    check()
