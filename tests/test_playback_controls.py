import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np
from ndtranskripthor.audio.playback import Player, RATES, tempo_blocks, output_devices
import test_editor_speakers


class PlaybackTest(unittest.TestCase):
    def setUp(self):
        self.player = Player()
        self.player.audio = np.ones(32000, dtype=np.float32)
        self.addCleanup(self.player.close)

    def test_seek_keeps_pause_and_running_and_clamps(self):
        p = self.player
        p.seek(1)
        self.assertEqual(p.position, 16000)
        self.assertFalse(p.playing)
        p.stream = Mock(active=True)
        with patch.object(p, 'play') as play:
            p.seek(99)
            play.assert_called_once_with()
            self.assertEqual(p.position, 32000)
        p.seek(-1)
        self.assertEqual(p.position, 0)

    def test_configuration_preserves_position_segment_limit_and_pause(self):
        p = self.player
        p.position, p.limit = 8000, 16000
        p.configure(.75, None)
        self.assertEqual(p.position, 8000)
        self.assertFalse(p.playing)
        p.stream = Mock(active=True)
        with patch.object(p, 'play') as play:
            p.configure(1.5, (3, 'Headphones', 0, 'Host'))
            play.assert_called_once_with(end=1.)
        with self.assertRaises(ValueError):
            p.configure(2, None)

    def test_devices_missing_and_unexpected_stop_no_automatic_fallback(self):
        sd = Mock()
        sd.query_hostapis.return_value = [{'name':'Host'}]
        sd.query_devices.return_value = [dict(name='Mic', hostapi=0, max_output_channels=0),
                                         dict(name='Headphones', hostapi=0, max_output_channels=2)]
        with patch.dict(sys.modules, sounddevice=sd):
            self.assertEqual(output_devices(), [(1,'Headphones',0,'Host')])
            self.player.device = (2,'Missing',0,'Host')
            with self.assertRaises(ValueError):
                self.player.play()
            sd.OutputStream.assert_not_called()
        self.player.stream = Mock(active=False)
        self.assertTrue(self.player.poll_error())
        self.assertIsNone(self.player.stream)
        self.assertIsNone(self.player.poll_error())

    def test_real_tempo_preserves_pitch_duration_and_bounded_reads(self):
        samples = np.sin(2*np.pi*440*np.arange(64000)/16000).astype('float32')
        class Audio:
            def __getitem__(self, key):
                self_test.assertLessEqual(key.stop-key.start, 4096)
                return samples[key]
        self_test = self
        for rate in RATES:
            with self.subTest(rate=rate):
                result = np.concatenate(list(tempo_blocks(Audio(), 0, len(samples), rate)))
                self.assertLess(abs(len(result)/16000 - 4/rate), .1)
                middle = result[8000:24000]
                frequency = np.argmax(abs(np.fft.rfft(middle)))
                self.assertLess(abs(frequency-440), 5)

    def test_tempo_callback_clock_and_natural_finish(self):
        sd = Mock()
        class Stop(Exception): pass
        sd.CallbackStop = Stop
        sd.CallbackAbort = RuntimeError
        self.player.rate = 1.25
        with patch.dict(sys.modules, sounddevice=sd):
            self.player.play(.25, 1.25)
            callback = sd.OutputStream.call_args.kwargs['callback']
            callback(np.empty((1024,1), dtype='float32'), 1024, None, None)
            self.assertEqual(self.player.position, 4000+1280)
            for _ in range(30):
                try:
                    callback(np.empty((1024,1), dtype='float32'),1024,None,None)
                except Stop:
                    break
            else:
                self.fail('Playback did not stop at segment end')
            self.assertTrue(self.player.ended)
            self.assertEqual(self.player.position, 20000)
            self.assertIsNone(self.player.poll_error())

    def test_failed_start_and_disconnect_cleanup_keep_audio_position(self):
        sd = Mock()
        sd.OutputStream.return_value.start.side_effect = RuntimeError('device removed')
        sd.OutputStream.return_value.stop.side_effect = RuntimeError('device removed')
        with patch.dict(sys.modules, sounddevice=sd):
            with self.assertRaisesRegex(RuntimeError, 'device removed'):
                self.player.play(.5)
        self.assertIsNone(self.player.stream)
        self.assertEqual(self.player.position, 8000)
        self.assertIsNotNone(self.player.audio)
        sd.OutputStream.return_value.close.assert_called_once()


class PlaybackEditorTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def test_mouse_pause_running_and_keyboard_share_seek_without_edits(self):
        e = self.editor
        e.player.audio = np.zeros(160000, dtype=np.float32)
        e.begin_seek()
        e.position.set(3)
        e.seek()
        self.assertEqual(e.player.position, 48000)
        self.assertFalse(e.player.playing)
        e.player.stream = Mock(active=True)
        with patch.object(e.player, 'play') as play:
            e.begin_seek()
            e.position.set(4)
            e.seek()
            play.assert_called_once_with()
        e.keyboard_seek(-5)
        self.assertEqual(e.player.position, 0)
        self.assertFalse(e.dirty)

    def test_settings_dialog_applies_without_editing_project(self):
        import tkinter as tk
        from tkinter import ttk
        from ndtranskripthor.presentation.ui import apply_theme
        from ndtranskripthor.core.i18n import set_language
        e = self.editor
        device = (3, 'Headphones Unicode č 日本', 0, 'Host')
        for language in ('en', 'sk'):
            set_language(language)
            for theme in ('light', 'dark'):
                self.app.theme = theme
                apply_theme(self.app, theme)
                for scale in (1, 1.25, 1.5, 1.75, 2):
                    self.root.tk.call('tk', 'scaling', scale*96/72)
                    with patch('ndtranskripthor.presentation.editor.output_devices', return_value=[device]):
                        e.playback_settings()
                    window = next(w for w in e.window.winfo_children() if isinstance(w, tk.Toplevel))
                    self.root.update()
                    fields = [w for w in window.dialog_panel.content.winfo_children() if isinstance(w, ttk.Combobox)]
                    fields[0].current(1); fields[1].current(2)
                    for field in fields:
                        self.assertTrue(field.winfo_ismapped())
                        self.assertLessEqual(field.winfo_rootx()+field.winfo_width(), window.winfo_rootx()+window.winfo_width())
                    button = next(w for w in window.dialog_panel.actions.winfo_children()
                                  if isinstance(w, ttk.Button) and w['style']=='Accent.TButton')
                    button.invoke()
                    self.assertEqual(e.player.rate, 1.25)
                    self.assertEqual(e.player.device, device)
                    self.assertFalse(e.dirty)
        set_language('en')
