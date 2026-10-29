# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from importlib.util import find_spec
import sys
root = Path(SPECPATH).resolve().parent
source = root / 'src'
prototype = globals().get('QML_PROTOTYPE', False)
application_name = 'ND TranskripThor QML Testing' if prototype else 'ND TranskripThor'
sys.path.insert(0, str(source))
from check_runtime import check
check()
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [(str(source / 'assets'), 'assets')]
datas += [(str(source / 'locales'), 'locales')]
binaries = []
# Keep evaluation helpers in the frozen source audit as well as source runs.
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('ndtranskripthor')
if prototype:
    datas += [(str(source / 'prototype_qml/Main.qml'), 'prototype_qml')]
    hiddenimports += ['prototype_qml.controller']
datas += collect_data_files('certifi')
datas += collect_data_files('tkinterdnd2')
if find_spec('kaldi_native_fbank'):
    optional_data, optional_bins, optional_imports = collect_all('kaldi_native_fbank')
    datas += optional_data
    binaries += optional_bins
    hiddenimports += optional_imports
datas += copy_metadata('tqdm')
datas += copy_metadata('huggingface-hub')
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ctranslate2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('av')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


for package in ('torch', 'transformers'):
    package_data, package_bins, package_imports = collect_all(package)
    datas += package_data
    binaries += package_bins
    hiddenimports += package_imports
for distribution in ('torch', 'transformers'):
    datas += copy_metadata(distribution, recursive=True)

a = Analysis(
    [str(source / ('prototype_qml/main.py' if prototype else 'prepis.py'))],
    pathex=[str(source)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tensorflow'] + ([] if prototype else ['PySide6', 'shiboken6', 'prototype_qml']),
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

from version import DISPLAY_VERSION, WINDOWS_VERSION
from PyInstaller.config import CONF
version_path = Path(CONF['workpath']) / 'version_info.txt'
version_path.parent.mkdir(parents=True, exist_ok=True)
version_path.write_text((Path(SPECPATH) / 'version_info.template').read_text(encoding='utf-8')
                       .replace('@VERSION@', DISPLAY_VERSION).replace('@WINDOWS_VERSION@', repr(WINDOWS_VERSION)), encoding='utf-8')

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=application_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version=str(version_path),
    icon=str(source / 'assets/transkripthor.ico'),
    manifest=str(Path(SPECPATH) / 'transkripthor.manifest'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=application_name,
)

