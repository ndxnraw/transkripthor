"""F19: deterministic audio weighting, phase boundaries and outcomes."""
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ndtranskripthor.application.progress import BatchProgress, ProgressClock
from ndtranskripthor.application.asr_batch import BatchRunner, recording_duration
import test_studio


class ProgressTest(unittest.TestCase):
    def test_short_long_weighted_and_failure_is_not_completion(self):
        batch = BatchProgress(['short', 'long'])
        batch.duration('short', 1); batch.duration('long', 999)
        batch.state('short', 'completed')
        self.assertAlmostEqual(batch.fraction(), .001)
        batch.progress('long', 20)
        batch.state('long', 'failed')
        self.assertAlmostEqual(batch.fraction(), .2008)
        self.assertEqual(batch.counts(), dict(completed=1, failed=1, interrupted=0))

    def test_unknown_zero_invalid_and_corrected_duration(self):
        batch = BatchProgress(['a', 'b'])
        batch.duration('a', 10); batch.progress('a', 50)
        self.assertIsNone(batch.fraction())
        batch.duration('b', float('nan'))
        self.assertIsNone(batch.fraction())
        batch.duration('b', 10)
        self.assertAlmostEqual(batch.fraction(), .25)
        batch.duration('b', 30)
        self.assertAlmostEqual(batch.fraction(), .125)
        batch.duration('a', 0); batch.duration('b', 0)
        self.assertIsNone(batch.fraction())

    def test_stagnation_never_counts_elapsed_time_as_work(self):
        clock = ProgressClock(0)
        for now, value in [(10, 0), (15, .4), (20, .8)]: clock.update(value, now)
        self.assertAlmostEqual(clock.remaining(20), 2.5)
        self.assertAlmostEqual(clock.remaining(25), 2.5)
        self.assertIsNone(clock.remaining(50))
        clock.samples.clear()  # Phase change or resumed baseline.
        clock.update(.8, 200)
        self.assertIsNone(clock.remaining(200))

    def test_real_container_durations_and_invalid_file(self):
        with tempfile.TemporaryDirectory() as folder:
            for samples in (1600, 160000):
                path = Path(folder)/f'{samples}.wav'
                with wave.open(str(path), 'wb') as wav:
                    wav.setparams((1, 2, 16000, 0, 'NONE', ''))
                    wav.writeframes(b'\0\0'*samples)
                self.assertAlmostEqual(recording_duration(path), samples/16000)
            self.assertIsNone(recording_duration(Path(folder)/'missing.wav'))

    def test_runner_errors_and_stops_never_emit_fake_hundred(self):
        for interrupt in (False, True):
            with self.subTest(interrupt=interrupt), tempfile.TemporaryDirectory() as folder:
                events, stop = [], threading.Event()
                def receive(event):
                    events.append(event)
                    if event[0] == 'job':
                        _, _, ack, result = event[1]
                        result.append(True); ack.set()
                runner = BatchRunner(dict(cache=folder, batch_ids=['a','b'], batch_mode='pending',
                    items=[dict(id=key, project='') for key in ('a','b')]), stop, SimpleNamespace(put=receive))
                model = SimpleNamespace(model=SimpleNamespace(device='cpu'))
                def transcribe(model, source, target, settings, stop, emit, **kwargs):
                    emit('duration', 999); emit('phase', 'transcribing'); emit('progress', 20)
                    if interrupt:
                        stop.set(); return False
                    raise OSError('fixture disk error')
                with patch('ndtranskripthor.application.asr_batch.recording_duration', side_effect=[1,999]), \
                     patch('ndtranskripthor.models.model_catalog.ensure_model'), patch('ndtranskripthor.models.model_catalog.cached_path', return_value=Path('revision')), \
                     patch.object(runner.models, 'get', return_value=model), \
                     patch('ndtranskripthor.asr.decode_settings.effective_settings', return_value={}), \
                     patch('ndtranskripthor.application.asr_batch.transcribe_job', side_effect=transcribe):
                    runner.work(['a.wav','b.wav'], folder, 'sk', 'tiny', True)
                self.assertNotIn(('progress', 100), events)
                states = [v[1]['state'] for k,v in events if k == 'job']
                self.assertIn('interrupted' if interrupt else 'failed', states)
                self.assertIn(('duration', ('a', 999)), events)


class ProgressUITest(unittest.TestCase):
    setUp = test_studio.StudioTest.setUp

    def tearDown(self):
        self.app.progress.stop()
        test_studio.StudioTest.tearDown(self)

    def test_phases_download_and_final_error_counts_are_independent(self):
        app = self.app
        app.batch_ids = ['a','b']; app.batch_measure = BatchProgress(app.batch_ids)
        app.clock = ProgressClock(time.monotonic())
        for event in [('duration', ('a',1)), ('duration', ('b',999)),
                      ('batch_index',0), ('phase','transcribing'), ('progress',100)]: app.events.put(event)
        app.poll()
        app.batch_measure.state('a','completed')
        self.assertAlmostEqual(float(app.batch_progress['value']), .1)
        for event in [('batch_index',1), ('phase','loading'), ('download_state',True)]: app.events.put(event)
        app.poll()
        self.assertEqual(app.percent.get(), '…')
        self.assertEqual(app.phase, 'downloading')
        self.assertAlmostEqual(float(app.batch_progress['value']), .1)
        for event in [('download_state',False), ('phase','transcribing'), ('progress',20)]: app.events.put(event)
        app.poll()
        app.batch_measure.state('b','failed')
        app.events.put(('finished',None)); app.poll()
        self.assertIn('errors 1', app.timing.get())
        self.assertIn('successful 1', app.timing.get())
        self.assertAlmostEqual(float(app.batch_progress['value']), 20.08)

    def test_new_batch_does_not_credit_previous_queue_success(self):
        app = self.app
        app.items = [dict(id='a',source='old.wav',state='completed',project='',error='')]
        app.batch_ids=['a']; app.batch_measure=BatchProgress(['a'])
        app.batch_measure.duration('a',10); app.clock=ProgressClock(time.monotonic())
        app.poll()
        self.assertEqual(float(app.batch_progress['value']), 0)
        self.assertIn('successful 0', app.timing.get())

    def test_resume_phase_and_denominator_changes_reset_eta(self):
        app = self.app
        app.batch_ids=['a']; app.batch_measure=BatchProgress(['a'])
        app.batch_measure.duration('a',100); app.clock=ProgressClock(0)
        app.set_phase('transcribing')
        for now, value in [(10,0), (20,.1), (30,.2)]: app.clock.update(value,now)
        self.assertIsNotNone(app.clock.remaining(30))
        app.events.put(('phase','loading')); app.poll()
        self.assertEqual(app.clock.samples, [])
        for event in [('phase','transcribing'), ('progress',80)]: app.events.put(event)
        app.poll()
        self.assertIsNone(app.clock.remaining(time.monotonic()))
        app.events.put(('duration',('a',120))); app.poll()
        self.assertEqual(app.clock.samples, [])

    def test_exit_during_preparation_is_interrupted_not_successful(self):
        app = self.app
        app.batch_ids=['a']; app.batch_measure=BatchProgress(['a'])
        app.clock=ProgressClock(time.monotonic())
        for event in [('batch_index',0), ('phase','decoding'), ('progress',0)]: app.events.put(event)
        app.poll()
        self.assertEqual(app.percent.get(), '…')
        self.assertEqual(str(app.progress['mode']), 'indeterminate')
        app.events.put(('process_exit', ('Stopped', True)))
        app.events.put(('finished', None)); app.poll()
        self.assertIn('interrupted 1', app.timing.get())
        self.assertIn('successful 0', app.timing.get())
