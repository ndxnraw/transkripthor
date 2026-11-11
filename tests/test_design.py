"""Design contracts: truthful actions, wrapping signature and keyboard focus."""
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.ui import AUTHOR, PALETTES, apply_theme
from test_studio import destroy_window


class DesignTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.app = App(self.root, Path(self.temp.name)/'state')

    def tearDown(self):
        destroy_window(self.root)
        self.temp.cleanup()

    def test_one_primary_action_and_partial_project_access(self):
        app = self.app
        self.assertEqual(app.start_button['style'], 'Accent.TButton')
        self.assertEqual(app.add['style'], 'Accent.TButton')
        self.assertFalse(app.run_panel.winfo_ismapped())
        self.assertFalse(hasattr(app, 'editor_button'))
        audio = Path(self.temp.name)/'reč.wav'
        audio.write_bytes(b'test')
        app.accept_files([str(audio)])
        self.assertEqual(app.add['style'], 'Secondary.TButton')
        app.listbox.selection_set(0)
        item = app.items[0]
        item.update(project='test-project', state='completed')
        app.update_selection()
        self.assertEqual(app.context_button['text'], 'Open transcript')
        self.assertEqual(app.queue_menu.entrycget(0, 'state'), 'disabled')
        item['state'] = 'interrupted'
        app.update_selection()
        self.assertEqual(app.context_button['text'], 'Resume')
        self.assertEqual(app.queue_menu.entrycget(0, 'state'), 'normal')
        # The only secondary editor action still opens an unfinished result.
        with patch.object(app, 'start') as start:
            app.queue_menu.invoke(1)
            start.assert_called_once_with('new')
        app.busy = True
        app.update_selection()
        self.assertEqual(app.queue_menu.entrycget(0, 'state'), 'disabled')
        self.assertEqual(app.queue_menu.entrycget(1, 'state'), 'disabled')

    def test_signature_wraps_without_changing_text(self):
        app = self.app
        # Isolate footer geometry below widths supported by the full workspace.
        app.workspace_tabs.pack_forget()
        self.root.minsize(420, 400)
        for scale in (1, 1.25, 1.5, 1.75, 2):
            self.root.tk.call('tk', 'scaling', 96/72*scale)
            for theme in ('light', 'dark'):
                apply_theme(app, theme)
                for width in (480, 800, 1200):
                    self.root.geometry(f'{width}x600')
                    self.root.update()
                    label = app.author_label
                    self.assertEqual(label['text'], AUTHOR)
                    self.assertEqual(str(label['justify']), 'right')
                    self.assertGreaterEqual(label.winfo_height(), label.winfo_reqheight())
                    self.assertGreaterEqual(label.winfo_rootx(), app.version_label.winfo_rootx()+app.version_label.winfo_width())
                    self.assertLessEqual(label.winfo_rootx()+label.winfo_width(), self.root.winfo_rootx()+width)

    def test_theme_focus_and_selection_contrast(self):
        for theme in ('dark', 'light'):
            apply_theme(self.app, theme)
            p = PALETTES[theme]
            self.assertEqual(self.app.style.lookup('TButton', 'focuscolor'), p['blue'])
            self.assertEqual(self.app.preview['selectforeground'], p['accent_text'])
            self.assertEqual(self.app.preview['selectbackground'], p['blue'])
            # Focus remains distinct with the Bootstrap layout, without custom bitmaps.
            self.assertEqual(self.app.style.theme_use(), f'thor-{theme}')
            self.assertEqual(self.app.style.lookup('TEntry', 'bordercolor', ('focus',)), p['blue'])
            self.app.workspace_tabs.select(self.app.pages['recordings'])
            self.root.update()
            self.app.lang_box.focus_force()
            self.root.update()
            self.assertEqual(self.root.focus_get(), self.app.lang_box)

    def test_header_contains_only_title_next_to_logo(self):
        from ndtranskripthor.core.i18n import tr
        header = self.app.icon.master
        brand = next(w for w in header.winfo_children() if isinstance(w, ttk.Frame))
        for scale in (1, 1.25, 1.5, 1.75, 2):
            self.root.tk.call('tk', 'scaling', 96/72*scale)
            for theme in ('dark', 'light'):
                apply_theme(self.app, theme)
                for width in (1040, 1366):
                    self.root.geometry(f'{width}x740')
                    self.root.update()
                    self.assertEqual(len(brand.winfo_children()), 1)
                    title = brand.winfo_children()[0]
                    self.assertEqual(title['text'], 'ND TranskripThor')
                    self.assertEqual(brand.winfo_reqheight(), title.winfo_reqheight())
                    self.assertNotEqual(title['text'], tr('ui_layout.build_ui.local_transcription_your_recordings_stay_with_you'))
                    self.assertGreater(title.winfo_rootx(), self.app.icon.winfo_rootx()+self.app.icon.winfo_width())
                    self.assertLessEqual(title.winfo_rootx()+title.winfo_width(), self.app.utility_button.winfo_rootx())
                    self.assertEqual(self.app.author_label['text'], AUTHOR)

    def test_subtitle_does_not_return_after_restart(self):
        self.app.save_state()
        destroy_window(self.root)
        self.root = tk.Tk()
        self.app = App(self.root, Path(self.temp.name)/'state')
        for theme in ('light', 'dark'):
            apply_theme(self.app, theme)
            self.root.update()
            brand = next(w for w in self.app.icon.master.winfo_children() if isinstance(w, ttk.Frame))
            self.assertEqual([w['text'] for w in brand.winfo_children()], ['ND TranskripThor'])


if __name__ == '__main__':
    unittest.main()
