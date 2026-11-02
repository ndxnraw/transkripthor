"""Locked toolchain and real PowerShell build gating without invoking a packager."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_environment as env
import build_receipt as receipt
from freeze import freezer_path


class BuildContractTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_current_locks_and_hub_contract(self):
        pins=env.validate_locks()
        self.assertEqual(pins['huggingface-hub'],'0.36.2')
        self.assertEqual(env.pins(ROOT/'requirements/bootstrap.lock')['pip'],'25.0.1')
        self.assertEqual((ROOT/'.python-version').read_text(encoding='ascii').strip(),'3.12.10')

    def test_freezer_excludes_foreign_native_toolchain_path(self):
        import os
        foreign=self.root/'foreign tools';foreign.mkdir()
        windows=self.root/'Windows';system=windows/'System32';system.mkdir(parents=True)
        (foreign/'icuuc.dll').write_bytes(b'incompatible')
        (system/'icuuc.dll').write_bytes(b'windows')
        with patch.dict(os.environ,{'PATH':str(foreign)}):
            search=freezer_path(self.root/'venv č',self.root/'Python č/python.exe',windows)
        self.assertNotIn(str(foreign),search.split(os.pathsep))
        found=next(Path(p)/'icuuc.dll' for p in search.split(os.pathsep) if (Path(p)/'icuuc.dll').exists())
        self.assertEqual(found.read_bytes(),b'windows')

    def test_unhashed_conflicting_and_recursive_locks_rejected(self):
        a=self.root/'a.lock';b=self.root/'b.lock'
        for content in ('pkg>=1','pkg==1', '-r a.lock', '-r ../a.lock'):
            a.write_text(content,encoding='utf-8')
            with self.subTest(content=content),self.assertRaises(ValueError):env.pins(a)
        a.write_text('pkg==1 --hash=sha256:'+'a'*64+'\n-r b.lock',encoding='utf-8')
        b.write_text('pkg==2 --hash=sha256:'+'b'*64,encoding='utf-8')
        with self.assertRaises(ValueError):env.pins(a)

    def test_environment_drift_and_missing_packages_rejected(self):
        class Distribution:
            metadata={'Name':'pip'};version='999';requires=[]
        with self.assertRaises(ValueError):env.check_environment('build',installed=[Distribution()])
        with self.assertRaises(ValueError):env.check_environment('build',installed=[])

    def test_transport_pin_mismatch_is_rejected(self):
        shutil.copytree(ROOT/'requirements',self.root/'requirements')
        (self.root/'src/ndtranskripthor/models').mkdir(parents=True)
        (self.root/'src/ndtranskripthor/models/download_worker.py').write_text("HUB_VERSION='different'",encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Hub lock'):env.validate_locks(self.root)

    def test_real_powershell_test_failure_stops_packaging(self):
        scripts=self.root/'scripts';scripts.mkdir()
        shutil.copy2(ROOT/'scripts/build.ps1',scripts/'build.ps1')
        (scripts/'common.ps1').write_text('''$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path $PSScriptRoot
$ProjectPython='unused'
function Assert-WindowsPython { param($Executable) }
function Invoke-ProjectPython {
 param([string[]]$Arguments)
 if (($Arguments -contains 'PyInstaller') -or ($Arguments -match 'freeze.py$')) { Set-Content -LiteralPath (Join-Path $ProjectRoot 'packager-ran') -Value 'bad' }
}
''',encoding='utf-8')
        (scripts/'test.ps1').write_text("throw 'Intentional mandatory test failure'",encoding='utf-8')
        run=subprocess.run([shutil.which('pwsh') or 'powershell','-NoProfile','-File',str(scripts/'build.ps1')],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('Intentional mandatory test failure',run.stderr)
        self.assertFalse((self.root/'packager-ran').exists())

    def test_receipt_rejects_pending_changed_inputs_and_output(self):
        for name in ('src','scripts','tests','requirements','packaging'):(self.root/name).mkdir()
        (self.root/'.python-version').write_text('3.12.10',encoding='ascii')
        source=self.root/'src'/'app.py';source.write_text('original',encoding='utf-8')
        app=self.root/'dist';app.mkdir();(app/'_internal').mkdir()
        exe=app/'ND TranskripThor.exe';exe.write_bytes(b'fake-test-exe')
        with patch.object(receipt,'check_environment',return_value={'pip':'25.0.1'}),patch.object(receipt.platform,'python_version',return_value='3.12.10'):
            receipt.begin(app,self.root)
            with self.assertRaises(ValueError):receipt.verify(app,self.root)
            receipt.create(app,self.root);receipt.verify(app,self.root)
            source.write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'inputs'):receipt.verify(app,self.root)
            source.write_text('original',encoding='utf-8');exe.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'output'):receipt.verify(app,self.root)
            exe.write_bytes(b'fake-test-exe');receipt.begin(app,self.root)
            self.assertTrue(list((self.root/'build/previous-build-manifests').glob('*.json')))
            with self.assertRaises(ValueError):receipt.verify(app,self.root)

    def test_package_requires_verified_manifest_and_includes_it(self):
        import package
        import zipfile
        for name in ('src','scripts','tests','requirements','packaging'):(self.root/name).mkdir()
        (self.root/'.python-version').write_text('3.12.10',encoding='ascii')
        app=self.root/'app';app.mkdir();(app/'_internal').mkdir()
        (app/'ND TranskripThor.exe').write_bytes(b'fixture only')
        output=self.root/'bundle.zip'
        original_verify=receipt.verify
        with patch.object(receipt,'check_environment',return_value={}),patch.object(receipt.platform,'python_version',return_value='3.12.10'), \
             patch.object(receipt,'verify',side_effect=lambda path:original_verify(path,self.root)),patch.object(package,'distributions',return_value=[]), \
             patch.object(sys,'argv',['package','--app',str(app),'--output',str(output)]):
            with self.assertRaises(FileNotFoundError):package.main()
            self.assertFalse(output.exists())
            receipt.create(app,self.root)
            package.main()
            self.assertTrue(output.with_suffix('.sha256').is_file())
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn('app/build-manifest.json',archive.namelist())
                import hashlib
                manifest=json.loads(archive.read('app/distribution-manifest.json'))
                for name,row in manifest['files'].items():
                    data=archive.read('app/'+name)
                    self.assertEqual(row['bytes'],len(data))
                    self.assertEqual(row['sha256'],hashlib.sha256(data).hexdigest())
                self.assertIn('app/LICENCIE/inventory.json',archive.namelist())
            self.assertFalse((app/'LICENCIE').exists())
