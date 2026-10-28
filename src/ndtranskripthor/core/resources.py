"""One resource root for source runs and the PyInstaller onedir layout."""
from pathlib import Path
import sys


def source_root():
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]


def resource_path(relative):
    return source_root() / relative
