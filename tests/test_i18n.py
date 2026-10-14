import json
import ast
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from i18n import Translator, fields, normalize_language, set_language, tr
from prepis import App, LANGUAGES, MODELS
from state import StateStore
from project import Project
from editor import Editor
from test_studio import destroy_window


class CatalogTest(unittest.TestCase):
    def test_all_literal_translation_calls_have_catalog_entries(self):
        catalog = Translator().catalogs['en']
        for path in (Path(__file__).resolve().parents[1] / 'src').glob('*.py'):
            if path.name.startswith('test'):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr' and node.args and isinstance(node.args[0], ast.Constant):
                    self.assertIn(node.args[0].value, catalog, (path.name, node.lineno))

    def test_catalog_parity_and_format_parameters(self):
        catalogs = Translator().catalogs
        self.assertEqual(set(catalogs['en']), set(catalogs['sk']))
        for key, english in catalogs['en'].items():
            self.assertTrue(english.strip(), key)
            self.assertEqual(fields(english), fields(catalogs['sk'][key]), key)

    def test_fallback_and_diagnostics_do_not_log_values(self):
        t = Translator('sk', {'en': {'file.failed': 'Cannot open {path}'}, 'sk': {}})
        with self.assertLogs('ndtranskripthor.i18n') as messages:
            self.assertEqual(t('file.failed', path='C:/Súkromné/žluťoučký.wav'), 'Cannot open C:/Súkromné/žluťoučký.wav')
        self.assertIn('file.failed', messages.output[0])
        self.assertNotIn('Súkromné', messages.output[0])

    def test_invalid_translation_format_falls_back(self):
        t = Translator('sk', {'en': {'value': 'Count: {count}'}, 'sk': {'value': 'Počet: {wrong}'}})
        with self.assertLogs('ndtranskripthor.i18n'):
            self.assertEqual(t('value', count=3), 'Count: 3')
            self.assertEqual(t('value'), 'Count: {count}')

    def test_default_ignores_os_language_and_plural_forms(self):
        with patch.dict(os.environ, {'LANG': 'sk_SK', 'LANGUAGE': 'sk', 'ND_UI_LANGUAGE': 'sk'}):
            self.assertEqual(Translator().language, 'en')
            for value in (None, '', 'de', 12, [], {}):
                self.assertEqual(normalize_language(value), 'en')
        en, sk = Translator('en'), Translator('sk')
        self.assertEqual(en.count('recordings.count', 1), '1 recording')
        self.assertEqual(en.count('recordings.count', 2), '2 recordings')
        self.assertEqual(sk.count('recordings.count', 1), '1 nahrávka')
        self.assertEqual(sk.count('recordings.count', 3), '3 nahrávky')
        self.assertEqual(sk.count('recordings.count', 5), '5 nahrávok')

    def test_legacy_settings_and_queue_migrate_without_losing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            store = StateStore(folder)
            old = dict(language='Čeština', model='Tiny – rýchly test', theme='light', device='cpu', offline=True, custom={'keep': 1})
            store.save('settings.json', old)
            self.assertEqual(store.settings(LANGUAGES, MODELS)['ui_language'], 'en')
            store.save_settings({'ui_language': 'sk'})
            self.assertEqual(store.read('settings.json', {}), dict(old, ui_language='sk'))
            store.save('queue.json', [dict(id='a', source='reč.wav', state='spracúva sa', project='p', error='Pôvodná chyba')])
            item = store.queue()[0]
            self.assertEqual(item['state'], 'interrupted')
            self.assertEqual(item['project'], 'p')
            self.assertEqual(item['error'], 'Pôvodná chyba')

    def test_bundled_catalogs_declared(self):
        spec = Path(__file__).resolve().parents[1] / 'packaging' / 'TranskripTHOR.spec'
        self.assertIn("/ 'locales'", spec.read_text(encoding='utf-8'))


class InterfaceLanguageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.root = None

    def tearDown(self):
        if self.root is not None:
            destroy_window(self.root)
        set_language('en')
        self.temp.cleanup()

    def open_app(self):
        if self.root is not None:
            destroy_window(self.root)
        self.root = tk.Tk()
        self.app = App(self.root, self.folder/'state')
        return self.app

    def test_persist_restart_and_independent_asr(self):
        app = self.open_app()
        self.assertEqual(app.active_ui_language, 'en')
        self.assertEqual(app.start_button['text'], 'Start transcription')
        self.assertEqual(app.lang_box.display_variable.get(), 'Slovak')
        before = (app.language.get(), app.quality.get(), app.device_choice.get())
        app.ui_language.set('sk')
        self.assertTrue(app.save_state())
        self.assertEqual(app.start_button['text'], 'Start transcription')
        self.assertEqual(app.active_ui_language, 'en')
        app = self.open_app()
        self.assertEqual(app.active_ui_language, 'sk')
        self.assertEqual(app.start_button['text'], 'Spustiť prepis')
        self.assertEqual(before, (app.language.get(), app.quality.get(), app.device_choice.get()))
        app.ui_language.set('en')
        app.save_state()
        app = self.open_app()
        self.assertEqual(app.start_button['text'], 'Start transcription')

    @patch.object(Editor, 'load_audio')
    def test_pending_language_keeps_editor_project_and_exports(self, _):
        app = self.open_app()
        target = self.folder/'project'
        with Project(target, create=True) as project:
            project.initialize('reč.wav', {}, {}, [], 32000)
            project.commit_chunk(0, [dict(start=0, end=1, text='Pôvodný československý text.', speaker='Vlastné meno', words=[])], 'sk')
            project.export()
        editor = Editor(app, target, parent=app.editor_page)
        app.editors.append(editor)
        before = {p.name:p.read_bytes() for p in target.iterdir() if p.suffix in ('.sqlite3', '.txt', '.srt')}
        app.busy = True
        app.ui_language.set('sk')
        app.save_state()
        self.assertFalse(editor.dirty)
        self.assertEqual(editor.segments[0]['text'], 'Pôvodný československý text.')
        self.assertEqual(editor.segments[0]['speaker'], 'Vlastné meno')
        self.assertTrue(app.busy)
        self.assertFalse(app.stop.is_set())
        self.assertEqual(before, {p.name:p.read_bytes() for p in target.iterdir() if p.suffix in ('.sqlite3', '.txt', '.srt')})


if __name__ == '__main__':
    unittest.main()
