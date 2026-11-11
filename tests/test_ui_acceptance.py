"""Final UI acceptance: resizing, theme metrics and short-lived dialog cleanup."""
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from ndtranskripthor.presentation.responsive import FlowFrame, MessageView
from ndtranskripthor.presentation.error_dialog import show_error
from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.editor import Editor
from ndtranskripthor.presentation.model_dialog import ModelDialog
from ndtranskripthor.presentation.ui import apply_theme
from ndtranskripthor.queueing.state import StateStore
from ndtranskripthor.projects.project import Project
from test_studio import destroy_window
from test_theme import system_palette
import test_design


class ResponsiveAcceptanceTest(unittest.TestCase):
    setUp = test_design.DesignTest.setUp
    tearDown = test_design.DesignTest.tearDown

    def test_closing_pending_control_row_does_not_leave_tcl_errors(self):
        self.root.tk.eval('set ::layout_errors {}; proc bgerror {message} {lappend ::layout_errors $message}')
        for _ in range(5):
            window = tk.Toplevel(self.root)
            row = FlowFrame(window)
            row.pack(fill='x')
            ttk.Button(row, text='Close').pack()
            row.schedule()
            window.destroy()
        self.root.update()
        self.assertEqual(self.root.tk.eval('set ::layout_errors'), '')

    def test_control_rows_reflow_when_theme_changes_requested_sizes(self):
        window = tk.Toplevel(self.root)
        window.geometry('620x300')
        row = FlowFrame(window)
        row.pack(fill='x')
        buttons = [ttk.Button(row, text=text) for text in ('Open project', 'Playback settings', 'Export transcript')]
        for button in buttons:
            button.pack(side='left')
        self.root.update()
        # Font/theme metrics may change without changing the row's width.
        for size in (18, 10, 20):
            self.app.style.configure('TButton', font=(self.app.font, size))
            row.event_generate('<<ThemeChanged>>')
            self.root.update()
            for button in buttons:
                self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
                self.assertGreaterEqual(button.winfo_x(), 0)
                self.assertLessEqual(button.winfo_x()+button.winfo_width(), row.winfo_width())
                self.assertLessEqual(button.winfo_y()+button.winfo_height(), row.winfo_height())
        window.destroy()

    def test_error_explanation_wraps_to_narrow_dialog_without_losing_details(self):
        window = show_error(self.root, 'Podrobnosti chyby', {'code': 'unknown', 'details': 'Detail 日本\n'*30})
        window.geometry('360x500')
        self.root.update()
        label = next(w for w in window.dialog_panel.content.winfo_children() if isinstance(w, ttk.Label))
        self.assertLessEqual(int(label['wraplength']), window.dialog_panel.content.winfo_width())
        self.assertGreaterEqual(label.winfo_height(), label.winfo_reqheight())
        window.details_button.invoke()
        self.root.update()
        self.assertTrue(window.details_text.winfo_ismapped())
        self.assertEqual(str(window.details_text['state']), 'disabled')
        self.assertEqual(window.details_text.get('1.0', 'end-1c'), 'Detail 日本\n'*30)
        for button in window.dialog_panel.actions.winfo_children():
            self.assertLessEqual(button.winfo_y()+button.winfo_height(), window.dialog_panel.actions.winfo_height())
        window.destroy()

    def test_closing_message_dialogs_releases_widget_registry_and_variable_traces(self):
        initial = tuple(self.app.message_widgets)
        value = tk.StringVar(self.root, 'Neuložené 日本')
        for _ in range(8):
            window = tk.Toplevel(self.root)
            MessageView(window, self.app, textvariable=value).pack(fill='x')
            window.destroy()
        value.set('Still usable')
        self.root.update()
        self.assertEqual(value.trace_info(), [])
        self.assertEqual(tuple(self.app.message_widgets), initial)

    def test_wrapped_keyboard_order_skips_disabled_actions(self):
        window = tk.Toplevel(self.root)
        window.geometry('240x300')
        row = FlowFrame(window)
        row.pack(fill='x')
        buttons = [ttk.Button(row, text=text) for text in ('Open project', 'Unavailable action', 'Export transcript')]
        for button in buttons:
            button.pack(side='left')
        buttons[1].state(['disabled'])
        self.root.update()
        self.assertGreater(buttons[2].winfo_y(), buttons[0].winfo_y())
        self.assertEqual(buttons[0].tk_focusNext(), buttons[2])
        self.assertEqual(buttons[2].tk_focusPrev(), buttons[0])
        window.destroy()

    def test_settings_focus_reveals_controls_and_help_in_short_viewport(self):
        self.root.minsize(640, 360)
        self.root.geometry('1040x480')
        self.app.workspace_tabs.select(self.app.pages['settings'])
        self.root.update()
        scroller = self.app.settings_scroll
        messages = [w.text for w in scroller.body.winfo_children() if isinstance(w, MessageView)]
        self.assertEqual(len(messages), 2)
        targets = [self.app.autoplay_box, *messages, self.app.device_box]
        positions = []
        for widget in targets:
            original = widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else None
            widget.focus_force()
            self.root.update()
            self.assertEqual(self.root.focus_get(), widget)
            positions.append(scroller.canvas.yview()[0])
            self.assertGreaterEqual(widget.winfo_rooty(), scroller.canvas.winfo_rooty())
            self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),
                                 scroller.canvas.winfo_rooty()+scroller.canvas.winfo_height())
            if original is not None:
                self.assertEqual(widget.get('1.0', 'end-1c'), original)
                self.assertEqual(str(widget['state']), 'disabled')
        self.assertLess(positions[-1], positions[-2])


class MainWindowLifecycleTest(unittest.TestCase):
    def test_manual_refresh_keeps_one_cycle_and_close_cancels_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            try:
                app = App(root, Path(folder)/'state')
                for _ in range(3):
                    app.poll()
                callbacks = [root.tk.call('after', 'info', timer)[0]
                             for timer in root.tk.splitlist(root.tk.call('after', 'info'))]
                self.assertEqual(sum(str(command).endswith('poll') for command in callbacks), 1)
                app.schedule_save()
                pending_save = app.persist_timer
                self.assertTrue(app.save_state())
                self.assertNotIn(pending_save, root.tk.splitlist(root.tk.call('after', 'info')))
                app.schedule_save()
                pending_save = app.persist_timer
                timer = app.poll_timer
                app.close()
                # Tcl timers survive destruction of Tk windows unless cancelled.
                self.assertNotIn(timer, root.tk.splitlist(root.tk.call('after', 'info')))
                self.assertNotIn(pending_save, root.tk.splitlist(root.tk.call('after', 'info')))
                self.assertIsNone(app.poll_timer)
                self.assertIsNone(app.persist_timer)
            finally:
                try:
                    exists = root.winfo_exists()
                except tk.TclError:
                    exists = False
                if exists:
                    destroy_window(root)


class ContrastAcceptanceTest(unittest.TestCase):
    @patch.object(Editor, 'load_audio')
    @patch.object(ModelDialog, 'refresh')
    def test_all_pages_at_every_scale_in_regular_and_contrast_themes(self, _refresh, _load):
        palettes = (system_palette('#000000', '#ffffff', '#ffff00', '#000000'),
                    system_palette('#ffffff', '#000000', '#000080', '#ffffff'))
        for language in ('en', 'sk'):
            for scale in (1, 1.25, 1.5, 1.75, 2):
                with self.subTest(language=language, scale=scale), tempfile.TemporaryDirectory() as folder:
                    root = tk.Tk()
                    try:
                        root.tk.call('tk', 'scaling', 96/72*scale)
                        StateStore(Path(folder)/'state').save('settings.json', {'ui_language': language})
                        with patch.object(root, 'winfo_screenwidth', return_value=1024), \
                             patch.object(root, 'winfo_screenheight', return_value=768):
                            app = App(root, Path(folder)/'state')
                        audio = Path(folder)/'Layout fixture.wav'
                        audio.write_bytes(b'UI fixture, not ASR audio')
                        app.accept_files([str(audio)])
                        app.listbox.selection_set(0)
                        app.update_selection()
                        app.set_phase('loading')
                        target = Path(folder)/'project'
                        with Project(target, create=True) as project:
                            project.initialize('Ukážka 日本.wav', {}, {}, [], 16000)
                            project.commit_chunk(0, [dict(start=0, end=1, text='Text 日本.', words=[], speaker='')], 'sk')
                        editor = Editor(app, target, parent=app.editor_page)
                        app.editors.append(editor)
                        editor.toggle_details()
                        app.model_dialog = ModelDialog(app, parent=app.models_page)
                        for theme, palette in (('dark', None), ('light', None), ('dark', palettes[0]), ('light', palettes[1])):
                            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                                apply_theme(app, theme)
                                for page in app.pages.values():
                                    app.workspace_tabs.select(page)
                                    root.update()
                                    for widget in app.theme_manager.widgets(page):
                                        if isinstance(widget, (ttk.Button, ttk.Menubutton, ttk.Entry, ttk.Combobox, ttk.Checkbutton)):
                                            self.assertTrue(widget.winfo_ismapped(), str(widget))
                                            self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight(), str(widget))
                                            if isinstance(widget, (ttk.Button, ttk.Menubutton, ttk.Checkbutton)):
                                                self.assertGreaterEqual(widget.winfo_width()+2, widget.winfo_reqwidth(), str(widget))
                                            self.assertGreaterEqual(widget.winfo_rootx(), root.winfo_rootx(), str(widget))
                                            self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), root.winfo_rootx()+root.winfo_width(), str(widget))
                                            self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), root.winfo_rooty()+root.winfo_height(), str(widget))
                                    if page is app.pages['settings']:
                                        before = app.autoplay.get()
                                        app.autoplay_box.invoke()
                                        self.assertEqual(app.autoplay.get(), not before)
                                        app.autoplay_box.invoke()
                                self.assertEqual(app.style.theme_use(), 'clam' if palette else 'thor-'+theme)
                                if palette:
                                    for style in ('TCheckbutton', 'TRadiobutton'):
                                        self.assertEqual(app.style.lookup(style, 'upperbordercolor'), palette['border'])
                                        self.assertEqual(app.style.lookup(style, 'lowerbordercolor'), palette['border'])
                                        self.assertGreaterEqual(int(app.style.lookup(style, 'indicatorsize')), round(12*scale)-1)
                    finally:
                        destroy_window(root)


if __name__ == '__main__':
    unittest.main()
