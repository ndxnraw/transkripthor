"""Run the freezer without unrelated native toolchains from the caller's PATH."""
import os
from pathlib import Path
import sys


def freezer_path(prefix, executable, windows):
    return os.pathsep.join(str(p) for p in (
        Path(prefix)/'Scripts', Path(executable).parent,
        Path(windows)/'System32', Path(windows)))


if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    if Path(sys.prefix).resolve() != (root/'.venv').resolve():
        raise SystemExit('Use the project .venv')
    os.environ['PATH']=freezer_path(sys.prefix,sys._base_executable,os.environ['SystemRoot'])
    from PyInstaller.__main__ import run
    run(sys.argv[1:])
