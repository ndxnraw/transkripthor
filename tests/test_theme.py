"""Real Tk theme transitions with simulated Windows palettes; no OS settings writes."""
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_editor_speakers
from ndtranskripthor.presentation.theme import PALETTES, manager_for
from ndtranskripthor.presentation.ui import apply_theme
from ndtranskripthor.presentation.error_dialog import show_error


def system_palette(background, foreground, selection, selected_text):
    return dict(bg=background, card=background, field=background, text=foreground,
                muted=foreground, border=foreground, blue=selection,
                accent_text=selected_text, info=background, disabled=background)


class ThemeTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def test_theme_preserves_message_geometry_and_complete_first_line(self):
        from pathlib import Path
        audio = Path(self.temp.name)/'Message layout.wav'
        audio.write_bytes(b'UI fixture, not ASR audio')
        self.app.accept_files([str(audio)])
        self.app.set_phase('loading')
        self.app.workspace_tabs.select(self.app.pages['recordings'])
        self.root.update()
        fields = [self.app.selection_label.text, self.app.readiness_label.text, self.app.status_view.text]
        for mode in ('dark', 'light', 'dark'):
            before = [{option: str(w.cget(option)) for option in
                       ('padx', 'pady', 'borderwidth', 'highlightthickness')} for w in fields]
            apply_theme(self.app, mode)
            self.root.update()
            for widget, geometry in zip(fields, before):
                self.assertTrue(widget.winfo_ismapped())
                self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
                self.assertEqual({option: str(widget.cget(option)) for option in geometry}, geometry)

    def test_system_colors_override_and_restore_saved_mode_without_saving(self):
        manager = self.app.theme_manager
        apply_theme(self.app, 'light')
        self.app.save_state()
        for palette in (system_palette('#000000', '#ffffff', '#ffff00', '#000000'),
                        system_palette('#ffffff', '#000000', '#000080', '#ffffff')):
            with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette), \
                 patch.object(self.app, 'schedule_save') as save:
                manager.refresh_system()
                save.assert_not_called()
                self.root.update()
                self.assertEqual(self.app.theme, 'light')
                self.assertEqual(self.app.style.theme_use(), 'clam')
                self.assertEqual(self.editor.text['background'], palette['field'])
                self.assertEqual(self.app.style.lookup('Treeview', 'background', ('selected',)), palette['blue'])
                self.assertEqual(self.app.style.lookup('Treeview', 'foreground', ('selected',)), palette['accent_text'])
                self.assertEqual(self.app.style.lookup('Treeview.Heading', 'background', ('active',)), palette['bg'])
                self.assertEqual(self.app.style.lookup('TCombobox', 'background', ('pressed',)), palette['field'])
                self.assertEqual(self.app.style.lookup('TCombobox', 'arrowcolor', ('disabled',)), palette['text'])
                self.assertEqual(self.app.style.lookup('TEntry', 'selectbackground', ('!focus',)), palette['blue'])
                popup = self.root.tk.call('ttk::combobox::PopdownWindow', self.app.lang_box._w)
                self.assertEqual(self.root.tk.call(str(popup)+'.f.l', 'cget', '-selectbackground'), palette['blue'])
                self.assertNotIn('.round', str(self.app.style.layout('TButton')))
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=None):
            manager.refresh_system()
        self.assertEqual(self.app.style.theme_use(), 'thor-light')
        self.assertEqual(self.editor.text['background'], PALETTES['light']['field'])
        self.assertEqual(self.app.store.settings({}, {})['theme'], 'light')

    def test_live_poll_recolors_open_dialog_and_preserves_editor_state(self):
        e = self.editor
        e.focus_text()
        e.text.insert('end', ' Neuložené 日本')
        e.text.mark_set('insert', '1.3')
        e.text.tag_add('sel', '1.0', '1.3')
        before = (e.text.get('1.0', 'end-1c'), e.text.index('insert'), tuple(map(str, e.text.tag_ranges('sel'))))
        window = tk.Toplevel(self.root)
        field = tk.Text(window)
        field.pack()
        field.insert('1.0', 'Diagnostika')
        field.configure(state='disabled')
        menu = tk.Menu(window, tearoff=False)
        menu.add_command(label='Test')
        selected = ttk.Entry(window)
        selected.pack()
        self.root.update()
        manager = self.app.theme_manager
        self.root.after_cancel(manager.poll_timer)
        manager.poll_timer = None
        palette = system_palette('#000000', '#ffffff', '#00ffff', '#000000')
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
            manager.poll_system()
            self.root.update()
            self.assertEqual(field['background'], palette['bg'])
            self.assertEqual(str(field['state']), 'disabled')
            self.assertEqual(field.get('1.0', 'end-1c'), 'Diagnostika')
            self.assertEqual(str(menu['activebackground']), palette['blue'])
            self.assertEqual(manager_for(field), manager)
            self.assertEqual((e.text.get('1.0', 'end-1c'), e.text.index('insert'), tuple(map(str, e.text.tag_ranges('sel')))), before)
            self.assertIn('Neuložené', e.text.get('1.0', 'end-1c'))
            window.destroy()

    def test_dialog_created_during_contrast_inherits_colors(self):
        palette = system_palette('#ffffff', '#000000', '#000080', '#ffffff')
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
            apply_theme(self.app, 'dark')
            window = show_error(self.root, 'Test', {'code': 'unknown', 'details': 'Podrobnosti 日本'})
            self.root.update()
            # Details start hidden, so expose them before checking the mapped Text.
            window.details_button.invoke()
            self.root.update()
            text = window.details_text
            self.assertEqual(window['background'], palette['bg'])
            self.assertEqual(text['foreground'], palette['text'])
            self.assertEqual(text['selectbackground'], palette['blue'])
            window.destroy()

    def test_user_can_choose_next_mode_while_contrast_is_active(self):
        palette = system_palette('#000000', '#ffffff', '#ffff00', '#000000')
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=palette):
            apply_theme(self.app, 'light')
            self.app.save_state()
            self.assertEqual(self.app.theme, 'light')
            self.assertEqual(self.app.style.theme_use(), 'clam')
        with patch('ndtranskripthor.presentation.accessibility.high_contrast_palette', return_value=None):
            self.app.theme_manager.refresh_system()
        self.assertEqual(self.app.style.theme_use(), 'thor-light')
