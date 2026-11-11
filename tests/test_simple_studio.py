"""Visible studio states and native-menu access to existing queue actions."""
from pathlib import Path
import copy
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from ndtranskripthor.core.i18n import tr
from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.ui import apply_theme
from ndtranskripthor.queueing.state import StateStore
import test_design
import test_editor_speakers
from ndtranskripthor.projects.project import Project
from test_studio import destroy_window
from test_theme import system_palette


class StudioActionsTest(unittest.TestCase):
    setUp = test_design.DesignTest.setUp
    tearDown = test_design.DesignTest.tearDown

    def test_empty_state_has_one_primary_entry_then_reuses_it_above_queue(self):
        app = self.app
        self.root.update()
        button = app.add
        self.assertTrue(app.empty_heading.winfo_ismapped())
        self.assertTrue(button.winfo_ismapped())
        self.assertEqual(button['style'], 'Accent.TButton')
        self.assertFalse(app.run_panel.winfo_ismapped())
        self.assertFalse(app.processing_panel.winfo_ismapped())
        self.root.lift()
        self.root.update()
        center = (button.winfo_rootx()+button.winfo_width()//2,
                  button.winfo_rooty()+button.winfo_height()//2)
        self.assertEqual(self.root.winfo_containing(*center), button)
        audio = Path(self.temp.name)/'Ukážka 日本.wav'
        audio.write_bytes(b'UI fixture')
        app.accept_files([str(audio)])
        self.assertEqual(app.listbox.curselection(), (0,))
        self.root.update()
        self.assertIs(app.add, button)
        self.assertEqual(button['style'], 'Secondary.TButton')
        self.assertFalse(app.empty_heading.winfo_ismapped())
        self.assertTrue(app.start_button.winfo_ismapped())
        self.assertGreater(app.listbox.winfo_height(), 40)
        app.listbox.selection_set(0)
        app.update_selection()
        app.remove.invoke()
        self.root.update()
        self.assertTrue(audio.is_file())
        self.assertEqual(button['style'], 'Accent.TButton')
        self.assertTrue(app.empty_heading.winfo_ismapped())

    def test_overflow_menu_reorders_removes_and_keeps_busy_guards(self):
        app = self.app
        paths = [Path(self.temp.name)/name for name in ('One.wav', 'Two.wav')]
        for path in paths:
            path.write_bytes(b'UI fixture')
        app.accept_files(list(map(str, paths)))
        app.listbox.selection_set(0)
        app.update_selection()
        for action in (app.remove, app.move_up, app.move_down, app.info_button):
            self.assertEqual(app.queue_menu.entrycget(action.index, 'label'), action['text'])
        self.assertEqual(app.move_up['state'], 'disabled')
        app.move_down.invoke()
        self.assertEqual(list(map(Path, app.files)), [path.resolve() for path in reversed(paths)])
        app.move_up.invoke()
        self.assertEqual(list(map(Path, app.files)), [path.resolve() for path in paths])
        app.busy = True
        app.update_selection()
        before = list(app.files)
        for action in (app.remove, app.move_up, app.move_down):
            self.assertEqual(action['state'], 'disabled')
            action.invoke()
        self.assertEqual(app.files, before)
        app.busy = False
        app.update_selection()
        app.remove.invoke()
        self.assertEqual(len(app.files), 1)
        self.assertTrue(all(path.is_file() for path in paths))

    def test_empty_overflow_keeps_results_and_settings_accessible(self):
        self.root.update()
        self.assertFalse(self.app.queue_tools.winfo_ismapped())
        labels = [self.app.utility_menu.entrycget(index, 'label')
                  for index in range(self.app.utility_menu.index('end')+1)
                  if self.app.utility_menu.type(index) != 'separator']
        self.assertIn(tr('ui_layout.build_ui.open_results'), labels)
        self.assertIn(tr('studio.advanced'), labels)

    def test_language_and_quality_are_in_main_flow_without_tabs(self):
        app = self.app
        self.root.update()
        self.assertNotIsInstance(app.workspace_tabs, ttk.Notebook)
        for widget in (app.lang_box, app.model_box):
            self.assertTrue(widget.winfo_ismapped())
        self.assertFalse(app.back_bar.winfo_ismapped())
        self.assertIsNone(app.model_dialog)
        app.workspace_tabs.select(app.pages['settings'])
        self.root.update()
        self.assertTrue(app.back_button.winfo_ismapped())
        app.back_button.invoke()
        self.root.update()
        self.assertEqual(app.workspace_tabs.select(), str(app.pages['recordings']))
        self.assertTrue(app.lang_box.winfo_ismapped())

    def test_missing_online_model_starts_without_opening_model_manager(self):
        audio = Path(self.temp.name)/'Online.wav'
        audio.write_bytes(b'UI fixture')
        self.app.accept_files([str(audio)])
        with patch('ndtranskripthor.models.model_catalog.cached_path', return_value=None), \
             patch('ndtranskripthor.presentation.prepis.threading.Thread') as thread:
            self.app.start()
        self.assertTrue(self.app.busy)
        thread.return_value.start.assert_called_once()
        self.assertIsNone(self.app.model_dialog)
        self.assertEqual(self.app.workspace_tabs.select(), str(self.app.pages['recordings']))

    def test_offline_download_is_explicit_and_stays_in_main_flow(self):
        audio = Path(self.temp.name)/'Offline.wav'
        audio.write_bytes(b'UI fixture')
        self.app.accept_files([str(audio)])
        self.app.offline.set(True)
        with patch('ndtranskripthor.models.model_catalog.cached_path', return_value=None), \
             patch('ndtranskripthor.presentation.prepis.messagebox.askyesno', return_value=True), \
             patch('ndtranskripthor.presentation.prepis.threading.Thread') as thread:
            self.app.start()
        self.assertFalse(self.app.offline.get())
        self.assertTrue(self.app.busy)
        thread.return_value.start.assert_called_once()
        self.assertIsNone(self.app.model_dialog)
        self.assertEqual(self.app.workspace_tabs.select(), str(self.app.pages['recordings']))


class StudioEditorNavigationTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_back_and_reopen_preserve_unsaved_text_cursor_selection_and_history(self):
        self.select(0)
        self.app.editors.append(self.editor)
        self.root.update()
        field = self.editor.text
        field.insert('end', ' Neuložené 日本')
        self.editor.modified()
        field.mark_set('insert', '1.4')
        field.tag_add('sel', '1.0', '1.4')
        self.root.update()
        state = (field.get('1.0', 'end-1c'), field.index('insert'),
                 tuple(map(str, field.tag_ranges('sel'))), copy.deepcopy(self.editor.history.__dict__))
        self.app.back_button.invoke()
        self.root.update()
        self.assertEqual(self.app.workspace_tabs.select(), str(self.app.pages['recordings']))
        self.assertTrue(self.editor.dirty)
        self.app.workspace_tabs.select(self.app.editor_page)
        self.root.update()
        self.assertIs(self.editor.text, field)
        self.assertEqual((field.get('1.0', 'end-1c'), field.index('insert'),
                          tuple(map(str, field.tag_ranges('sel'))), self.editor.history.__dict__), state)
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Text 0.')


class StudioEmptyLayoutTest(unittest.TestCase):
    def test_hero_and_add_button_fit_languages_scales_and_contrast(self):
        modes = (('light', None), ('dark', None),
                 ('dark', system_palette('#000000', '#ffffff', '#ffff00', '#000000')),
                 ('light', system_palette('#ffffff', '#000000', '#000080', '#ffffff')))
        for language in ('en', 'sk'):
            for scale in (1, 1.25, 1.5, 1.75, 2):
                with self.subTest(language=language, scale=scale), tempfile.TemporaryDirectory() as folder:
                    root = tk.Tk()
                    try:
                        root.tk.call('tk', 'scaling', 96/72*scale)
                        StateStore(Path(folder)/'state').save('settings.json', {'ui_language':language})
                        with patch.object(root, 'winfo_screenwidth', return_value=1024), \
                             patch.object(root, 'winfo_screenheight', return_value=768):
                            app = App(root, Path(folder)/'state')
                        for theme, palette in modes:
                            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                                apply_theme(app, theme)
                                root.update()
                                for widget in (app.empty_heading, app.empty_description, app.empty_hint, app.add):
                                    self.assertTrue(widget.winfo_ismapped(), str(widget))
                                    self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight(), str(widget))
                                    self.assertGreaterEqual(widget.winfo_rootx(), app.empty.winfo_rootx())
                                    self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), app.empty.winfo_rootx()+app.empty.winfo_width())
                                    self.assertGreaterEqual(widget.winfo_rooty(), app.empty.winfo_rooty())
                                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), app.empty.winfo_rooty()+app.empty.winfo_height())
                    finally:
                        destroy_window(root)


if __name__ == '__main__':
    unittest.main()
