"""Native Tk event dispatch, isolated profiles; not a Narrator certification."""
import unittest
import time
from unittest.mock import patch
import test_editor_speakers
from ui import PALETTES, apply_theme


def contrast(a, b):
    def luminance(color):
        values = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        values = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(v*w for v, w in zip(values, (.2126, .7152, .0722)))
    values = sorted((luminance(a), luminance(b)))
    return (values[1]+.05)/(values[0]+.05)


class AccessibilityTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def key(self, widget, sequence):
        self.root.update()  # Complete native window mapping before requesting focus.
        widget.focus_force()
        self.wait_focus(widget)
        widget.event_generate(sequence)
        self.root.update()

    def wait_focus(self, widget):
        deadline = time.monotonic() + 3
        while True:
            self.root.update()
            if self.root.focus_get() == widget:
                return
            if time.monotonic() >= deadline:
                self.fail('Native Tk focus did not reach the requested widget')
            time.sleep(.01)

    def test_save_search_navigation_and_no_hidden_editor_dispatch(self):
        e = self.editor
        e.focus_text()
        self.assertEqual(e.current, 0)
        e.text.insert('end', ' preserved')
        self.key(e.text, '<Alt-Up>')
        self.assertEqual(e.current, 44)
        self.assertIn('preserved', e.segments[0]['text'])
        self.key(e.text, '<Control-f>')
        self.assertEqual(self.root.focus_get(), e.search_entry)
        e.query.set('Text 1.')
        self.key(e.search_entry, '<Return>')
        self.key(e.search_entry, '<F3>')
        self.assertEqual(e.current, 1)
        with patch.object(e, 'save', return_value=True) as save:
            self.key(e.text, '<Control-s>')
            save.assert_called_once()
            self.app.workspace_tabs.select(self.app.pages['settings'])
            self.key(self.app.lang_box, '<Control-s>')
            save.assert_called_once()

    def test_typing_tab_and_playback_guards(self):
        e = self.editor
        e.focus_text()
        with patch.object(e, 'play') as play, patch.object(e, 'play_segment') as segment:
            for field in (e.text, e.search_entry):
                for key in ('<F7>', '<F8>'):
                    self.key(field, key)
            play.assert_not_called()
            segment.assert_not_called()
            before = e.text.get('1.0', 'end-1c')
            e.text.mark_set('insert', 'end-1c')
            self.key(e.text, '<space>')
            self.assertEqual(e.text.get('1.0', 'end-1c'), before+' ')
            target = e.text.tk_focusNext()
            self.assertEqual(target, e.tree.blocks['1'][2])
            self.key(e.text, '<Tab>')
            self.assertEqual(self.root.focus_get(), target)
            self.assertNotIn('\t', e.text.get('1.0', 'end-1c'))
            self.key(e.slider, '<F7>')
            segment.assert_called_once()
            self.key(e.slider, '<F8>')
            play.assert_called_once()
        e.player.audio = [0] * 160000
        e.player.position = 80000
        self.key(e.slider, '<Left>')
        self.assertEqual(e.player.position, 0)
        self.assertIsNone(e.player.stream)

    def test_block_focus_and_tab_exit(self):
        e = self.editor
        label = e.tree.blocks['0'][2]
        self.root.update()
        label.focus_force()
        self.wait_focus(label)
        self.assertEqual(label['style'], 'Focus.Transcript.TLabel')
        self.key(label, '<Return>')
        self.assertEqual(e.current, 0)
        previous = e.text.tk_focusPrev()
        self.key(e.text, '<Shift-Tab>')
        self.assertEqual(self.root.focus_get(), previous)
        self.key(e.text, '<Control-Tab>')
        self.assertEqual(self.app.workspace_tabs.select(), str(self.app.pages['models']))

    def test_contrast_and_system_palette_without_changing_windows(self):
        for palette in PALETTES.values():
            for fg, bg in [('text', 'field'), ('text', 'card'), ('muted', 'bg'), ('muted', 'card'), ('accent_text', 'blue')]:
                self.assertGreaterEqual(contrast(palette[fg], palette[bg]), 4.5, (fg, bg))
        system = dict(bg='#000000', card='#000000', field='#000000', text='#ffffff', muted='#ffffff',
                      border='#ffffff', blue='#ffff00', accent_text='#000000', info='#000000', disabled='#000000')
        with patch('accessibility.high_contrast_palette', return_value=system):
            apply_theme(self.app, 'dark')
            self.editor.apply_theme()
            self.assertEqual(self.app.style.lookup('TLabel', 'foreground'), '#ffffff')
            self.assertNotIn('.round', str(self.app.style.layout('TButton')))
        with patch('accessibility.high_contrast_palette', return_value=None):
            apply_theme(self.app, 'light')
            self.assertIn('light.Button.round', str(self.app.style.layout('TButton')))
            self.assertGreaterEqual(contrast(self.app.style.lookup('Accent.TButton', 'focuscolor'), PALETTES['light']['blue']), 3)


if __name__ == '__main__':
    unittest.main()
