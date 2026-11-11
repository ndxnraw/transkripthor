"""Theme changes must restyle existing editing sessions, never reload or save them."""
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_editor_speakers
from test_theme import system_palette
from ndtranskripthor.presentation.ui import apply_theme
from ndtranskripthor.presentation.data_dialog import DataDialog
from ndtranskripthor.presentation.error_dialog import show_error
from ndtranskripthor.projects.project import Project


class EditorThemeTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_playback_opened_from_event_callback_returns_and_maps_controls(self):
        palette = system_palette('#000000', '#ffffff', '#ffff00', '#000000')
        returned = []
        def open_dialog():
            self.editor.playback_settings()
            returned.append(True)
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette), \
             patch('ndtranskripthor.presentation.editor.output_devices', return_value=[]):
            apply_theme(self.app, 'light')
            self.root.after(0, open_dialog)
            self.root.update()
            self.assertEqual(returned, [True])
            window = next(w for w in self.editor.window.winfo_children() if isinstance(w, tk.Toplevel))
            fields = [w for w in window.dialog_panel.content.winfo_children() if isinstance(w, ttk.Combobox)]
            self.assertEqual(len(fields), 2)
            for field in fields:
                self.assertTrue(field.winfo_ismapped())
            window.destroy()

    def modes(self):
        yield 'light', None
        yield 'dark', None
        yield 'light', system_palette('#000000', '#ffffff', '#ffff00', '#000000')
        yield 'dark', system_palette('#ffffff', '#000000', '#000080', '#ffffff')
        yield 'dark', None

    def test_unsaved_text_cursor_history_and_search_colors_survive_all_modes(self):
        e = self.editor
        self.select(0)
        e.text.delete('1.0', 'end')
        e.text.insert('1.0', 'Zaznamenaná zmena 日本')
        e.modified()
        e.capture()
        e.text.insert('end', '\nNeuložené ' * 15)
        e.modified()
        e.text.mark_set('insert', '2.4')
        e.text.tag_add('sel', '2.0', '2.4')
        e.text.yview_moveto(.5)
        self.root.update()
        field = e.text
        snapshot = (field.get('1.0', 'end-1c'), field.index('insert'),
                    tuple(map(str, field.tag_ranges('sel'))), field.yview(), e.current,
                    copy.deepcopy(e.history.__dict__), e.dirty, e.saved_state.get())
        # The editor is deliberately not registered in app.editors by this fixture.
        self.assertNotIn(e, self.app.editors)
        with patch.object(e, 'render', side_effect=AssertionError('Theme must not rebuild blocks')), \
             patch.object(e, 'capture', side_effect=AssertionError('Theme must not commit pending text')):
            for mode, palette in self.modes():
                with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                    apply_theme(self.app, mode)
                    self.root.update()
                    self.assertIs(e.text, field)
                    self.assertEqual((field.get('1.0', 'end-1c'), field.index('insert'),
                                      tuple(map(str, field.tag_ranges('sel'))), field.yview(), e.current,
                                      e.history.__dict__, e.dirty, e.saved_state.get()), snapshot)
                    colors = self.app.theme_manager.palette
                    self.assertEqual(field.tag_cget('search_active', 'background'), colors['blue'])
                    self.assertEqual(field.tag_cget('search_match', 'foreground'), colors['text'])
        e.undo()
        self.assertNotIn('Neuložené', e.text.get('1.0', 'end-1c'))
        e.redo()
        self.assertIn('Neuložené', e.text.get('1.0', 'end-1c'))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Text 0.')

    def test_playback_dialog_retains_pending_options_and_does_not_save_editor(self):
        e = self.editor
        self.select(0)
        e.text.insert('end', ' Pending edit')
        e.modified()
        e.player.position = 12000
        device = (3, 'Slúchadlá 日本', 0, 'Host')
        with patch('ndtranskripthor.presentation.editor.output_devices', return_value=[device]):
            e.playback_settings()
        window = next(w for w in e.window.winfo_children() if isinstance(w, tk.Toplevel))
        fields = [w for w in window.dialog_panel.content.winfo_children() if isinstance(w, ttk.Combobox)]
        fields[0].current(1)
        fields[1].current(2)
        for mode, palette in self.modes():
            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                apply_theme(self.app, mode)
                self.root.update()
                self.assertEqual((fields[0].current(), fields[1].current()), (1, 2))
                self.assertEqual(e.player.position, 12000)
                self.assertEqual(e.player.rate, 1)
                self.assertTrue(e.dirty)
                self.assertIn('Pending edit', e.text.get('1.0', 'end-1c'))
        window.destroy()

    def test_readonly_diagnostic_text_and_selection_survive_theme_changes(self):
        self.app.output.set(self.temp.name)
        dialog = DataDialog(self.app)
        # Freeze the view after constructing its real widgets; workers may still
        # deliver events, but this test only changes colors of the displayed copy.
        dialog.window.after_cancel(dialog.timer)
        dialog.display(dialog.preview_text, 'Pripravený náhľad\n' * 30)
        dialog.tabs.select(1)
        self.root.update()
        field = dialog.preview_text
        field.tag_add('sel', '2.0', '2.4')
        before = field.get('1.0', 'end-1c')
        for mode, palette in self.modes():
            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                apply_theme(self.app, mode)
                self.root.update()
                self.assertEqual(field.get('1.0', 'end-1c'), before)
                self.assertEqual(str(field['state']), 'disabled')
                self.assertEqual(tuple(map(str, field.tag_ranges('sel'))), ('2.0', '2.4'))
        dialog.close()

    def test_legacy_query_fields_and_quick_dialog_close_use_shared_theme(self):
        manager = self.app.theme_manager
        window = tk.Toplevel(self.root)
        entry = tk.Entry(window)
        entry.insert(0, 'Neodoslané 日本')
        entry.pack()
        button = tk.Button(window, text='OK')
        button.pack()
        for mode, palette in self.modes():
            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
                apply_theme(self.app, mode)
                self.root.update()
                self.assertEqual(entry.get(), 'Neodoslané 日本')
                self.assertEqual(str(entry['background']), manager.palette['field'])
                self.assertEqual(str(button['foreground']), manager.palette['text'])
        # Reproduce closing a new window before its deferred titlebar callback.
        self.root.tk.eval('set ::theme_bg_errors {}; proc bgerror {message} {lappend ::theme_bg_errors $message}')
        transient = tk.Toplevel(self.root)
        manager.style_widget(transient)
        transient.destroy()
        self.root.update()
        self.assertEqual(self.root.tk.eval('set ::theme_bg_errors'), '')
        window.destroy()
        owner = self.editor.window
        owner.destroy()
        self.assertNotIn(owner, manager.listeners)
