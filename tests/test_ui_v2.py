from test_io_support import save_editor, export_editor
import tempfile
import sys
import ctypes
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.ui import apply_theme
from ndtranskripthor.projects.project import Project
from ndtranskripthor.presentation.editor import Editor


class DesktopTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root, Path(self.folder.name)/'state')

    def tearDown(self):
        self.root.update_idletasks()
        for identifier in self.root.tk.splitlist(self.root.tk.call('after','info')):
            self.root.after_cancel(identifier)
        self.root.destroy()
        self.folder.cleanup()

    def test_settings_restore_and_reset(self):
        self.app.language.set('Maďarčina')
        self.app.offline.set(True)
        self.app.output.set(self.folder.name)
        apply_theme(self.app,'light')
        self.app.save_state()
        self.app.language.set('Slovenčina')
        self.app.restore_settings()
        self.assertEqual(self.app.language.get(),'Maďarčina')
        self.assertTrue(self.app.offline.get())
        self.assertEqual(self.app.theme,'light')
        self.app.reset_settings()
        self.assertEqual(self.app.language.get(),'Slovenčina')
        self.assertEqual(self.app.theme,'dark')

    def test_editor_rejects_unprepared_and_empty_projects_without_creating_window(self):
        source = Path(self.folder.name)/'audio.wav'
        source.write_bytes(b'audio')
        target = Path(self.folder.name)/'project'
        self.app.accept_files([str(source)])
        self.app.items[0].update(state='interrupted', project=str(target))
        self.app.refresh_queue()
        self.app.listbox.selection_set(0)
        with Project(target, create=True) as project:
            for state in ('legacy-empty', 'preparing', 'ready', 'complete'):
                with self.subTest(state=state):
                    if state == 'preparing':
                        project.begin_preparation(source, {})
                    elif state == 'ready':
                        project.initialize(source, {}, {}, [], 0)
                    elif state == 'complete':
                        project.finish()
                    expected = project.editor_problem()
                    self.assertTrue(expected)
                    with patch('ndtranskripthor.presentation.prepis.messagebox.showinfo') as info, patch('ndtranskripthor.presentation.editor.Editor') as constructor:
                        self.app.open_editor()
                        constructor.assert_not_called()
                        self.assertEqual(info.call_args.args[1], expected)
                    with self.assertRaises(ValueError) as error:
                        Editor(self.app, str(target))
                    self.assertEqual(str(error.exception), expected)
        self.assertEqual(self.app.editors, [])

    @unittest.skipUnless(sys.platform == 'win32', 'Native Windows painting')
    def test_native_painting_survives_window_restore_and_theme_changes(self):
        from ctypes import wintypes
        from ndtranskripthor.presentation.window_style import titlebar
        user = ctypes.windll.user32
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        get_style = user.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.GetWindowLongW
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        button = str(self.app.start_button)
        for theme in ('light', 'dark'):
            apply_theme(self.app, theme)
            for state in ('normal', 'zoomed', 'iconic', 'normal', 'zoomed', 'normal'):
                self.root.state(state)
                self.root.update()
                titlebar(self.root, theme == 'dark', '#101010', '#eeeeee')
                hwnd = self.root.winfo_id()
                before = get_style(hwnd, -20)
                self.assertFalse(before & 0x02000000)
                self.assertFalse(hasattr(self.root, '_paint_timer'))
                self.assertFalse(hasattr(self.root, '_transition_paint_installed'))
                self.assertEqual(get_style(hwnd, -20), before)
                self.assertEqual(str(self.app.start_button), button)
        self.assertTrue(self.app.start_button.winfo_ismapped())
        self.assertEqual(str(self.app.lang_box['state']), 'readonly')

    def test_queue_order_drop_and_retry_only_failed(self):
        paths = [(Path(self.folder.name)/f'{i} ukážka.wav').resolve() for i in range(3)]
        for path in paths:
            path.write_bytes(b'a')
        self.app.accept_files([str(p) for p in paths])
        self.app.listbox.selection_set(1)
        self.app.move_item(-1)
        self.assertEqual(self.app.files[0],str(paths[1]))
        self.app.items[0]['state']='completed'
        self.app.items[1]['state']='failed'
        self.app.items[2]['state']='interrupted'
        with patch('ndtranskripthor.presentation.prepis.threading.Thread') as thread:
            self.app.start('retry')
            self.assertEqual(thread.call_args.kwargs['args'][0],[str(paths[0]),str(paths[2])])

    @patch('ndtranskripthor.presentation.editor.Editor.load_audio')
    def test_editor_entire_transcript_search_save_and_dirty_prompt(self, load):
        project_folder = Path(self.folder.name)/'project'
        with Project(project_folder,create=True) as project:
            project.initialize('missing.wav', {}, {}, [], 3001 * 16000)
            segments = [dict(start=i*2,end=i*2+1,text=f'Úsek {i}.',words=[],speaker='',language='sk') for i in range(1501)]
            project.commit_chunk(0, segments,'sk')
            project.finish()
        editor = Editor(self.app,str(project_folder))
        editor.query.set('1500')
        editor.search()
        self.assertEqual(editor.matches,[1500])
        editor.tree.selection_set('1500')
        editor.select()
        editor.text.delete('1.0','end')
        editor.text.insert('1.0','Opravený posledný úsek.')
        editor.modified()
        self.assertTrue(editor.dirty)
        with patch('ndtranskripthor.presentation.editor.messagebox.askyesnocancel',return_value=None):
            self.assertFalse(editor.close())
        with patch('ndtranskripthor.presentation.editor.messagebox.showerror', side_effect=AssertionError('Unexpected export error')):
            self.assertTrue(save_editor(editor))
        self.assertTrue(export_editor(editor))
        with Project(project_folder) as project:
            self.assertEqual(project.segments()[-1]['text'],'Opravený posledný úsek.')
            self.assertEqual(project.segments()[-1]['start'],3000)
            self.assertEqual(project.get('editor_export')['state'], 'complete')
        self.assertTrue(editor.close())

    def test_logs_never_enter_transcript_preview(self):
        self.app.events.put(('log','Prevádzková správa'))
        self.app.events.put(('segment',dict(start=0,end=1,text='Skutočný prepis.')))
        self.app.poll()
        self.assertNotIn('Prevádzková',self.app.preview.get('1.0','end'))
        self.assertIn('Skutočný',self.app.preview.get('1.0','end'))
        self.assertIn('Prevádzková',self.app.activity.get('1.0','end'))


class ScalingTest(unittest.TestCase):
    def test_header_and_buttons_fit_at_different_scales(self):
        from tkinter import ttk
        for scale in (1, 1.25, 1.5, 1.75, 2):
            with self.subTest(scale=scale), tempfile.TemporaryDirectory() as folder:
                # Separate interpreter: changing scaling must precede creating fonts.
                window = tk.Tk()
                try:
                    window.tk.call('tk', 'scaling', 96 / 72 * scale)
                    from ndtranskripthor.queueing.state import StateStore
                    StateStore(folder).save('settings.json', {'geometry': '1800x1000+0+0', 'language': 'Maďarčina'})
                    app = App(window, folder)
                    window.update()
                    self.assertEqual((window.winfo_width(), window.winfo_height()), window.minsize())
                    self.assertEqual(app.language.get(), 'Maďarčina')
                    for theme in ('dark', 'light'):
                        apply_theme(app, theme)
                        window.update()
                        self.assertGreaterEqual(app.icon.winfo_width(), app.logo_image.width())
                        self.assertGreaterEqual(app.icon.winfo_height(), app.logo_image.height())
                        def inspect(widget):
                            if widget.winfo_ismapped() and isinstance(widget, ttk.Button):
                                self.assertGreaterEqual(widget.winfo_width()+2, widget.winfo_reqwidth(), str(widget['text']))
                            for child in widget.winfo_children():
                                inspect(child)
                        inspect(window)
                finally:
                    for timer in window.tk.splitlist(window.tk.call('after', 'info')):
                        window.after_cancel(timer)
                    window.destroy()
