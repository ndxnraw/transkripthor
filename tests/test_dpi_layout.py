"""Tk scaling/viewport matrix, not a claim of changing Windows system DPI."""
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from itertools import product
from state import StateStore
from unittest.mock import patch
from prepis import App
from editor import Editor
from model_dialog import ModelDialog
from project import Project
from ui import apply_theme
from test_studio import destroy_window
import test_editor_speakers


class SmallScreenTest(unittest.TestCase):
    @patch.object(Editor, 'load_audio')
    def test_all_pages_small_screens_long_text_both_themes(self, _load):
        for ui_language, screen in product(('en', 'sk'), ((1280, 768), (1366, 768), (1536, 864))):
            for scale in (1, 1.25, 1.5, 1.75, 2):
                with self.subTest(screen=screen, scale=scale), tempfile.TemporaryDirectory() as folder:
                    root = tk.Tk()
                    try:
                        StateStore(Path(folder)/'state').save('settings.json', {'ui_language': ui_language})
                        root.tk.call('tk', 'scaling', 96/72*scale)
                        with patch.object(root, 'winfo_screenwidth', return_value=screen[0]), \
                             patch.object(root, 'winfo_screenheight', return_value=screen[1]):
                            app = App(root, Path(folder)/'state')
                        target = Path(folder)/'project'
                        with Project(target, create=True) as project:
                            project.initialize('Dlhý názov nahrávky ' * 12 + '.wav', {}, {}, [], 16000)
                            project.commit_chunk(0, [dict(start=0, end=1, text='Text.', words=[], speaker='')], 'sk')
                        editor = Editor(app, target, parent=app.editor_page)
                        app.editors.append(editor)
                        editor.toggle_details()
                        with patch.object(ModelDialog, 'refresh'):
                            models = ModelDialog(app, parent=app.models_page)
                        app.model_dialog = models
                        long_text = ('Viacriadková chyba s dlhou cestou C:/nahrávky/' + 'nahrávka_'*25 + '\n')*12
                        for value in (app.status, app.selection_info, app.readiness, app.device_status,
                                      models.status, models.description, editor.status):
                            value.set(long_text)
                        for theme in ('dark', 'light'):
                            apply_theme(app, theme)
                            for page in app.pages.values():
                                app.workspace_tabs.select(page)
                                root.update()
                                def inspect(widget):
                                    if isinstance(widget, (ttk.Entry, ttk.Combobox)):
                                        self.assertTrue(widget.winfo_ismapped(), str(widget))
                                        self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight(), str(widget))
                                        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), root.winfo_rootx()+root.winfo_width(), str(widget))
                                        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), root.winfo_rooty()+root.winfo_height(), str(widget))
                                    if isinstance(widget, (ttk.Button, ttk.Menubutton)):
                                        self.assertTrue(widget.winfo_ismapped(), (widget['text'], str(widget), widget.master.winfo_geometry(), widget.master.master.winfo_geometry(), root.winfo_geometry()))
                                        self.assertGreaterEqual(widget.winfo_width()+2, widget.winfo_reqwidth(), widget['text'])
                                        self.assertGreaterEqual(widget.winfo_rootx(), root.winfo_rootx(), widget['text'])
                                        self.assertGreaterEqual(widget.winfo_rooty(), root.winfo_rooty(), widget['text'])
                                        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), root.winfo_rootx()+root.winfo_width(), widget['text'])
                                        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), root.winfo_rooty()+root.winfo_height(), widget['text'])
                                    for child in widget.winfo_children():
                                        inspect(child)
                                inspect(page)
                            self.assertEqual(app.author_label['text'], 'Created by Daniel Návojský (ndxnraw) using Codex | 2026')
                            self.assertGreaterEqual(app.author_label.winfo_height(), app.author_label.winfo_reqheight())
                            self.assertLessEqual(app.author_label.winfo_rootx()+app.author_label.winfo_width(), root.winfo_rootx()+root.winfo_width())
                            self.assertLessEqual(app.author_label.winfo_rooty()+app.author_label.winfo_height(), root.winfo_rooty()+root.winfo_height())
                            self.assertEqual(app.status_view.text.get('1.0', 'end-1c'), long_text)
                            app.status_view.text.yview_moveto(1)
                            self.assertGreater(app.status_view.text.yview()[0], 0)
                    finally:
                        destroy_window(root)


class PlaybackLayoutTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def test_wide_playback_and_details_buttons_remain_fully_visible(self):
        # Hosted Windows desktops can request wider buttons than this machine.
        # Exercise that constraint without changing/ignoring any original test.
        from i18n import tr
        labels = {tr('editor.init.' + key) for key in ('segment', 'resume', 'pause', 'segment_and_subtitles')}
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        buttons = [widget for widget in descendants(self.editor.window)
                   if isinstance(widget, ttk.Button) and widget['text'] in labels]
        self.assertEqual(len(buttons), 4)
        for button in buttons:
            button.configure(width=28)
        self.root.update()
        for button in buttons:
            self.assertTrue(button.winfo_ismapped(), button['text'])
            self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth(), button['text'])
            self.assertGreaterEqual(button.winfo_rootx(), self.root.winfo_rootx(), button['text'])
            self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), self.root.winfo_rootx() + self.root.winfo_width(), button['text'])
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), self.root.winfo_rooty() + self.root.winfo_height(), button['text'])


if __name__ == '__main__':
    unittest.main()
