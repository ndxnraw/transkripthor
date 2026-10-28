"""Isolated storage, diagnostic privacy, failure and real Tk preview regressions."""
import json
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
import zipfile
from unittest.mock import patch
from ndtranskripthor.application.local_data import measure, inventory, diagnostic_snapshot, save_bundle, NOTICE
from ndtranskripthor.models.model_catalog import ensure_model


class LocalDataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stop = threading.Event()

    def test_sizes_missing_and_bounded_scan_never_read_contents(self):
        (self.root/'ž 日本').mkdir()
        (self.root/'ž 日本'/'secret.wav').write_bytes(b'PRIVATE TEXT')
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Content read')):
            result = measure(self.root, self.stop)
        self.assertEqual(result, dict(bytes=12, files=1, state='complete'))
        self.assertEqual(measure(self.root/'missing', self.stop)['state'], 'missing')
        self.assertEqual(measure(self.root, self.stop, limit=1)['state'], 'partial')
        self.stop.set()
        self.assertEqual(measure(self.root, self.stop)['state'], 'partial')

    def test_denied_and_reparse_point_are_partial_not_zero_success(self):
        with patch('ndtranskripthor.application.local_data.os.scandir', side_effect=PermissionError()):
            self.assertEqual(measure(self.root, self.stop)['state'], 'partial')
        from types import SimpleNamespace
        import stat
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)), \
             patch('ndtranskripthor.application.local_data.os.scandir', side_effect=AssertionError('Link followed')):
            self.assertEqual(measure(self.root, self.stop)['state'], 'partial')

    def test_known_projects_deduplicate_and_include_pcm(self):
        rows = inventory(self.root, self.root/'models', self.root/'output', [self.root/'project']*2, self.stop)
        self.assertEqual([r['kind'] for r in rows].count('project'), 1)
        self.assertEqual([r['kind'] for r in rows].count('project_cache'), 1)
        self.assertTrue(next(r['path'] for r in rows if r['kind']=='project_cache').endswith('.pcm-cache'))

    def test_snapshot_and_zip_exclude_paths_text_tokens_logs_and_match_preview(self):
        secret = 'PRIVATE-záznam-hf_token'
        (self.root/'secret.txt').write_text(secret, encoding='utf-8')
        row = dict(kind='project', bytes=5, files=1, state='complete', path=str(self.root/secret), error=secret, text=secret)
        snapshot = diagnostic_snapshot([row], ['waiting', secret], True)
        self.assertNotIn(secret, snapshot)
        self.assertNotIn(str(self.root), snapshot)
        path = self.root/'diagnostika 日本.zip'
        save_bundle(path, snapshot)
        with zipfile.ZipFile(path) as bundle:
            self.assertEqual(set(bundle.namelist()), {'diagnostics.json','README.txt'})
            self.assertEqual(bundle.read('diagnostics.json').decode('utf-8'), snapshot)
            self.assertEqual(bundle.read('README.txt').decode('utf-8'), NOTICE)
        self.assertEqual((self.root/'secret.txt').read_text(encoding='utf-8'), secret)

    def test_failed_publish_keeps_existing_bundle_and_cleans_own_temp_only(self):
        path = self.root/'bundle.zip'; path.write_bytes(b'previous')
        with patch('ndtranskripthor.application.local_data.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):save_bundle(path, '{}')
        self.assertEqual(path.read_bytes(), b'previous')
        self.assertFalse(list(self.root.glob('.nd-diagnostic-*')))

    def test_offline_missing_model_and_inventory_never_connect(self):
        def reject(*args, **kwargs): raise AssertionError('Network attempt')
        with patch('socket.socket.connect', side_effect=reject), patch('socket.getaddrinfo', side_effect=reject), \
             patch('ndtranskripthor.models.model_catalog.download', side_effect=AssertionError('Download')):
            rows=inventory(self.root, self.root/'models', self.root/'output', [], self.stop)
            self.assertTrue(json.loads(diagnostic_snapshot(rows, [], True))['offline'])
            with self.assertRaises(ValueError):ensure_model(self.root/'models','tiny',True,lambda *a:None,self.stop)


class DataUiTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from ndtranskripthor.presentation.prepis import App
        from test_studio import destroy_window
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=tk.Tk();self.addCleanup(destroy_window,self.root)
        self.app=App(self.root,Path(self.temp.name)/'state')
        self.app.output.set(str(Path(self.temp.name)/'output'))

    def wait(self, dialog):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            self.root.update()
            if str(dialog.refresh_button['state'])!='disabled':return
            time.sleep(.01)
        self.fail('Data worker did not complete')

    def test_preview_required_and_saved_bytes_are_exact_snapshot(self):
        self.app.manage_data();dialog=self.app.data_dialog;self.wait(dialog)
        self.assertEqual(str(dialog.save_button['state']),'disabled')
        with patch('ndtranskripthor.presentation.data_dialog.filedialog.asksaveasfilename') as choose:
            dialog.save();choose.assert_not_called()
        dialog.preview();snapshot=dialog.snapshot
        self.assertIn(snapshot,dialog.preview_text.get('1.0','end'))
        target=Path(self.temp.name)/'diag.zip'
        with patch('ndtranskripthor.presentation.data_dialog.filedialog.asksaveasfilename',return_value=str(target)):
            dialog.save();self.wait(dialog)
        with zipfile.ZipFile(target) as bundle:self.assertEqual(bundle.read('diagnostics.json').decode(),snapshot)
        dialog.refresh();self.wait(dialog)
        self.assertEqual(str(dialog.save_button['state']),'disabled')
        dialog.close()

    def test_queue_removal_keeps_files_and_data_dialog_both_themes(self):
        from ndtranskripthor.presentation.ui import apply_theme
        source=Path(self.temp.name)/'voice.wav';source.write_bytes(b'keep')
        self.app.accept_files([str(source)]);self.app.listbox.selection_set(0);self.app.remove_files()
        self.assertEqual(source.read_bytes(),b'keep');self.assertEqual(self.app.items,[])
        from ndtranskripthor.core.i18n import set_language
        for language in ('en','sk'):
            set_language(language)
            for scale in (1,1.25,1.5,1.75,2):
                self.root.tk.call('tk','scaling',96/72*scale)
                for theme in ('light','dark'):
                    apply_theme(self.app,theme)
                    self.app.manage_data();dialog=self.app.data_dialog;self.wait(dialog)
                    dialog.window.geometry('640x480');self.root.update()
                    dialog.preview();self.root.update()
                    self.assertEqual(str(dialog.preview_text['state']),'disabled')
                    for button in (dialog.refresh_button,dialog.preview_button,dialog.save_button):
                        self.assertTrue(button.winfo_ismapped())
                        self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),dialog.window.winfo_rooty()+dialog.window.winfo_height())
                    dialog.close()
        set_language('en')

    def test_parent_close_waits_for_diagnostic_write(self):
        self.app.manage_data();dialog=self.app.data_dialog;self.wait(dialog);dialog.preview()
        entered,release=threading.Event(),threading.Event()
        def write(*args):
            entered.set()
            if not release.wait(5):raise TimeoutError('Test did not release write')
        with patch('ndtranskripthor.presentation.data_dialog.save_bundle',side_effect=write), \
             patch('ndtranskripthor.presentation.data_dialog.filedialog.asksaveasfilename',return_value=str(Path(self.temp.name)/'diag.zip')):
            try:
                dialog.save();self.assertTrue(entered.wait(2))
                self.app.close()
                self.assertTrue(self.root.winfo_exists())
                self.assertTrue(dialog.window.winfo_exists())
            finally:release.set()
            self.wait(dialog)
        dialog.close()
