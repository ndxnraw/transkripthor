"""Optional real Tk compatibility suite, run by test-ttkbootstrap.ps1 (no skips)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))


class BootstrapCompatibilityTest(unittest.TestCase):
    def test_optional_lock_cannot_override_stable_dependency(self):
        from verify_environment import validate_locks
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT/'requirements', root/'requirements')
            lock = root/'requirements/ttkbootstrap.lock'
            lock.write_text(lock.read_text(encoding='utf-8').replace('pillow==12.3.0', 'pillow==99.0.0'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'conflicts with stable runtime'):
                validate_locks(root)

    def test_lifecycle_drop_themes_and_scaling(self):
        with tempfile.TemporaryDirectory(prefix='Thor ttk test č ') as folder:
            report = Path(folder)/'report.json'
            run = subprocess.run([sys.executable, str(ROOT/'src/prototype_ttkbootstrap/main.py'),
                                  '--smoke-output', str(report)], capture_output=True, text=True, timeout=90)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertNotIn('bgerror', run.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'PASS')
            self.assertEqual(len(data['cycles']), 3)
            self.assertEqual(data['ttkbootstrap'], '2.2.7')

    def test_preview_does_not_mutate_stock_widget_api(self):
        code = """import tkinter.ttk as native
before = native.Button.__init__
import prototype_ttkbootstrap.main
assert native.Button.__init__ is before
import sys
assert not any(m in sys.modules for m in ('torch', 'faster_whisper', 'ctranslate2'))
"""
        run = subprocess.run([sys.executable, '-c', code], cwd=ROOT/'src',
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
