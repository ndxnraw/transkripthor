"""F03: interrupted preparation and real process termination, isolated projects."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from jobs import job_settings, transcribe_job
from project import Project, fingerprint


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)/'nahrávka.wav'
        self.source.write_bytes(b'fixture')
        self.target = Path(self.temp.name)/'project'
        self.settings = job_settings('small', 'sk')
        self.stop = threading.Event()
        self.audio = np.zeros(6*16000, dtype=np.float32)
        self.spans = [dict(start=0, end=len(self.audio))]
        self.model = Mock()
        self.model.transcribe.side_effect = lambda *a, **k: (iter([
            SimpleNamespace(start=.1, end=1, text='Zachované.', words=[])]), SimpleNamespace(language='sk'))

    def run_job(self, resume=False, emit=None):
        return transcribe_job(self.model, self.source, self.target, self.settings,
                              self.stop, emit or Mock(), resume=resume)

    def resume_and_check(self):
        self.stop.clear()
        with patch('pcm_audio.decode_audio', return_value=self.audio), \
             patch('faster_whisper.vad.get_speech_timestamps', return_value=self.spans):
            self.assertTrue(self.run_job(resume=True))
        with Project(self.target) as project:
            self.assertEqual(project.phase(), 'complete')
            self.assertEqual(project.get('next_chunk'), 1)
            self.assertEqual([s['text'] for s in project.segments()], ['Zachované.'])
            self.assertEqual(project.segments()[0]['start'], .1)
            self.assertEqual(project.segments()[0]['end'], 1)
            self.assertIsNone(project.editor_problem())
        # F08 extends display to the configured one-second minimum within the
        # six-second recording; the original ASR interval above stays untouched.
        self.assertIn('00:00:00,100 --> 00:00:01,100', (self.target/'titulky.srt').read_text(encoding='utf-8-sig'))

    def test_stop_at_each_preparation_stage_then_resume(self):
        for stage in ('hashing', 'decoding', 'vad', 'ready'):
            with self.subTest(stage=stage):
                self.target = Path(self.temp.name)/stage
                self.stop.clear()
                def digest(*args):
                    if stage == 'hashing':
                        self.stop.set()
                        raise InterruptedError('Stopped hashing')
                    return fingerprint(*args)
                def decode(*args, **kwargs):
                    if stage == 'decoding':
                        self.stop.set()
                    return self.audio
                def vad(*args):
                    if stage == 'vad':
                        self.stop.set()
                    return self.spans
                def emit(kind, value):
                    if stage == 'ready' and value == 'Transcribing speech…':
                        self.stop.set()
                with patch('jobs.fingerprint', side_effect=digest), \
                     patch('pcm_audio.decode_audio', side_effect=decode), \
                     patch('faster_whisper.vad.get_speech_timestamps', side_effect=vad):
                    self.assertFalse(self.run_job(emit=emit))
                with Project(self.target) as project:
                    self.assertEqual(project.get('source'), str(self.source.resolve()))
                    self.assertEqual(project.get('settings'), self.settings)
                    self.assertEqual(project.segments(), [])
                    self.assertTrue(project.editor_problem())
                    self.assertEqual(project.phase(), 'transcribing' if stage == 'ready' else 'preparing')
                self.resume_and_check()

    def test_process_crash_at_each_stage_then_resume(self):
        # The child terminates without context-manager cleanup or a Python exception.
        code = '''
import os, sys, threading
from unittest.mock import Mock, patch
import numpy as np
from jobs import transcribe_job, job_settings
from project import fingerprint
stage, source, target = sys.argv[1:]
def die(): os._exit(17)
def digest(*args):
    if stage == 'hashing': die()
    return fingerprint(*args)
def decode(*args, **kwargs):
    if stage == 'decoding': die()
    return np.zeros(96000, dtype=np.float32)
def vad(*args):
    if stage == 'vad': die()
    return [dict(start=0, end=96000)]
def emit(kind, value):
    if stage == 'ready' and value == 'Transcribing speech…': die()
with patch('jobs.fingerprint', side_effect=digest), patch('pcm_audio.decode_audio', side_effect=decode), patch('faster_whisper.vad.get_speech_timestamps', side_effect=vad):
    transcribe_job(Mock(), source, target, job_settings('small', 'sk'), threading.Event(), emit)
'''
        for stage in ('hashing', 'decoding', 'vad', 'ready'):
            with self.subTest(stage=stage):
                self.target = Path(self.temp.name)/stage
                result = subprocess.run([sys.executable, '-c', code, stage, str(self.source), str(self.target)],
                                        capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1] / 'src')
                self.assertEqual(result.returncode, 17, result.stderr)
                with Project(self.target) as project:
                    self.assertEqual(project.get('next_chunk'), 0)
                    self.assertEqual(project.segments(), [])
                    self.assertTrue(project.editor_problem())
                self.resume_and_check()

    def test_preparation_metadata_transaction_rolls_back_on_process_crash(self):
        with Project(self.target, create=True) as project:
            project.begin_preparation(self.source, self.settings)
        code = '''
import os, sys
from project import Project
with Project(sys.argv[1]) as project:
    original = project.put
    def put(key, value):
        original(key, value)
        if key == 'plan': os._exit(19)
    project.put = put
    project.initialize(sys.argv[2], {}, {}, [[0, 96000]], 96000)
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.target), str(self.source)], capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1] / 'src')
        self.assertEqual(result.returncode, 19, result.stderr)
        with Project(self.target) as project:
            self.assertEqual(project.phase(), 'preparing')
            self.assertIsNone(project.get('plan'))
            self.assertEqual(project.get('settings'), self.settings)
        self.resume_and_check()

    def test_legacy_empty_shell_and_ready_project(self):
        with Project(self.target, create=True):
            pass
        self.resume_and_check()
        self.target = Path(self.temp.name)/'legacy-ready'
        with Project(self.target, create=True) as project:
            project.initialize(self.source, fingerprint(self.source), self.settings, [[0, len(self.audio)]], len(self.audio))
            project.db.execute("DELETE FROM metadata WHERE key IN ('phase', 'preparation_stage')")
            project.db.commit()
        self.resume_and_check()

    def test_initial_metadata_crash_rolls_back_and_preserves_existing_data(self):
        code = '''
import os, sys
from project import Project
with Project(sys.argv[1], create=True) as project:
    original = project.put
    def put(key, value):
        original(key, value)
        if key == 'settings': os._exit(23)
    project.put = put
    project.begin_preparation(sys.argv[2], {})
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.target), str(self.source)], capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1] / 'src')
        self.assertEqual(result.returncode, 23, result.stderr)
        with Project(self.target) as project:
            self.assertIsNone(project.get('schema'))
            self.assertIsNone(project.get('source'))
        self.resume_and_check()
        with Project(self.target) as project:
            project.db.execute("DELETE FROM metadata WHERE key='schema'")
            project.db.commit()
            with self.assertRaisesRegex(ValueError, 'metadata is incomplete'):
                project.begin_preparation(self.source, self.settings)
            self.assertEqual(project.segments()[0]['text'], 'Zachované.')

    def test_mismatched_source_settings_and_digest_preserve_project(self):
        with Project(self.target, create=True) as project:
            project.begin_preparation(self.source, self.settings)
            project.preparation_stage('decoding', fingerprint(self.source))
        with Project(self.target) as project:
            with self.assertRaisesRegex(ValueError, 'settings'):
                project.begin_preparation(self.source, job_settings('tiny', 'sk'))
        stat = self.source.stat()
        self.source.write_bytes(b'changed')  # same size and restored mtime: checksum must still reject it
        os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.run_job(resume=True)
        with Project(self.target) as project:
            self.assertEqual(project.get('settings'), self.settings)
            self.assertEqual(project.phase(), 'preparing')

    def test_silent_complete_project_has_explanation(self):
        with Project(self.target, create=True) as project:
            project.initialize(self.source, {}, self.settings, [], 0)
            project.finish()
            self.assertIn('No speech found', project.editor_problem())
            self.assertEqual(project.get('result'), dict(outcome='no_speech', segment_count=0))


if __name__ == '__main__':
    unittest.main()
