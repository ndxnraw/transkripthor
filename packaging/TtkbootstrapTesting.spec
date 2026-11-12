# Isolated compatibility EXE; no model runtime or user profile is needed.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).resolve().parent
source = root / 'src'
sys.path.insert(0, str(source))
from version import DISPLAY_VERSION, WINDOWS_VERSION, PRERELEASE
from PyInstaller.config import CONF
version_path = Path(CONF['workpath']) / 'version_info.txt'
version_path.parent.mkdir(parents=True, exist_ok=True)
version_path.write_text((Path(SPECPATH) / 'version_info.template').read_text(encoding='utf-8')
                       .replace('@VERSION@', DISPLAY_VERSION).replace('@WINDOWS_VERSION@', repr(WINDOWS_VERSION))
                       .replace('@VERSION_FLAGS@', '0x2' if PRERELEASE else '0x0')
                       .replace('ND TranskripThor.exe', 'ND TranskripThor ttkbootstrap Preview.exe'), encoding='utf-8')
a = Analysis([str(source / 'prototype_ttkbootstrap/main.py')], pathex=[str(source)],
             datas=[(str(source / 'assets'), 'assets'), (str(source / 'locales'), 'locales')]
                   + collect_data_files('ttkbootstrap') + collect_data_files('tkinterdnd2')
                   + copy_metadata('ttkbootstrap'),
             hiddenimports=['PIL._tkinter_finder'],
             # window_style.rounded_styles refers to the stable UI, which imports
             # ASR settings. The preview uses only titlebar from that module.
             excludes=['ndtranskripthor.presentation.ui', 'ndtranskripthor.presentation.ui_layout',
                       'ndtranskripthor.asr', 'torch', 'transformers', 'faster_whisper', 'ctranslate2'])
pyz = PYZ(a.pure)
name = 'ND TranskripThor ttkbootstrap Preview'
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=name,
          console=False, icon=str(source / 'assets/transkripthor.ico'), uac_admin=False,
          version=str(version_path))
coll = COLLECT(exe, a.binaries, a.datas, name=name)
