import os
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock
import numpy as np
from ndtranskripthor.audio.pcm_audio import decode_audio, speech_spans, cleanup, RATE


class PCMTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'stereo.wav'
        with wave.open(str(self.source), 'wb') as wav:
            wav.setparams((2, 2, 44100, 0, 'NONE', ''))
            data = np.arange(44100*12*2+246, dtype=np.int16)
            wav.writeframes(data.tobytes())

    def test_exact_legacy_samples_random_slices_and_cleanup(self):
        from faster_whisper.audio import decode_audio as legacy
        expected = legacy(str(self.source), sampling_rate=RATE)
        audio = decode_audio(self.source, folder=self.root/'cache')
        self.assertEqual(len(audio), len(expected))
        for start, end in ((0, 11), (15990, 16111), (len(audio)-10, len(audio))):
            np.testing.assert_array_equal(audio[start:end], expected[start:end])
        np.testing.assert_array_equal(audio[:], expected)
        directory = audio.directory
        os.utime(directory, (0, 0))
        cleanup(directory.parent)
        self.assertTrue(audio.path.exists())  # Active lease, including stale mtime.
        audio.close()
        self.assertFalse(directory.exists())

    def test_stop_low_disk_and_decoder_error_leave_no_partial_cache(self):
        stop = threading.Event(); stop.set()
        cache = self.root/'cache'
        with self.assertRaises(InterruptedError):
            decode_audio(self.source, folder=cache, stop=stop)
        with patch('ndtranskripthor.audio.pcm_audio.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(OSError, 'disk space'):
                decode_audio(self.source, folder=cache)
        with self.assertRaises(Exception):
            decode_audio(self.root/'missing.wav', folder=cache)
        self.assertEqual(list(cache.glob('pcm-*')), [])

    def test_abandoned_cache_reaped_without_deleting_other_files(self):
        cache = self.root/'cache'; stale = cache/'pcm-abandoned'
        stale.mkdir(parents=True)
        (stale/'audio.s16').write_bytes(b'partial')
        (cache/'keep.txt').write_text('keep')
        os.utime(stale, (0, 0))
        cleanup(cache)
        self.assertFalse(stale.exists())
        self.assertTrue((cache/'keep.txt').exists())

    def test_vad_boundaries_have_bounded_inputs_and_no_gap(self):
        class Audio:
            def __len__(self): return RATE*125
            def __getitem__(self, section):
                self_test.assertLessEqual(section.stop-section.start, RATE*62)
                return np.zeros(section.stop-section.start, dtype=np.float32)
        self_test = self
        with patch('faster_whisper.vad.get_speech_timestamps', side_effect=lambda a,o: [dict(start=0,end=len(a))]):
            spans = speech_spans(Audio(), object(), threading.Event())
        self.assertEqual(spans, [dict(start=0,end=RATE*125)])

    def test_player_reads_pcm_and_closes_cache(self):
        from ndtranskripthor.audio.playback import Player
        player = Player()
        player.load(self.source, self.root/'cache')
        directory = player.audio.directory
        self.assertEqual(player.limit, len(player.audio))
        self.assertEqual(len(player.audio[10:20]), 10)
        player.close()
        self.assertFalse(directory.exists())

    def test_real_pcm_stop_checkpoint_resume_and_cleanup(self):
        from ndtranskripthor.application.jobs import job_settings, transcribe_job
        from ndtranskripthor.projects.project import Project
        stop = threading.Event()
        target = self.root/'project'
        settings = job_settings('small', 'sk')
        settings['segmentation']['min_speech_segment_duration'] = 1
        model = Mock()
        model.transcribe.side_effect = lambda *a, **k: (iter([SimpleNamespace(start=.1,end=1,text='Text',words=[])]), SimpleNamespace(language='sk'))
        def emit(kind, value):
            if kind == 'segment': stop.set()
        spans = [dict(start=0,end=RATE*2), dict(start=RATE*6,end=RATE*8)]
        with patch('faster_whisper.vad.get_speech_timestamps', return_value=spans):
            self.assertFalse(transcribe_job(model, self.source, target, settings, stop, emit))
            with Project(target) as project:
                self.assertEqual(project.get('next_chunk'), 1)
                self.assertEqual(len(project.segments()), 1)
            self.assertEqual(list((target/'.pcm-cache').glob('pcm-*')), [])
            stop.clear()
            self.assertTrue(transcribe_job(model, self.source, target, settings, stop, lambda *args: None, resume=True))
        with Project(target) as project:
            self.assertEqual([s['start'] for s in project.segments()], [.1, 6.1])
        self.assertEqual(list((target/'.pcm-cache').glob('pcm-*')), [])


if __name__ == '__main__':
    unittest.main()
