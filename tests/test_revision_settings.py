import copy
import json
import tempfile
import threading
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ndtranskripthor.application.asr_batch import BatchRunner
from ndtranskripthor.asr.decode_settings import effective_settings, apply_settings
from ndtranskripthor.application.jobs import job_settings, transcribe_chunk, transcribe_job
from ndtranskripthor.asr.mixed_language import MixedConfig
from ndtranskripthor.models.model_catalog import cached_path, cache_folder, ensure_model
from ndtranskripthor.projects.project import Project
from ndtranskripthor.asr.speech_models import ModelManager, SlovakWhisper, SLOVAK_MODEL, load_backend

A, B = 'a'*40, 'b'*40


class RevisionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name)
        self.stop = threading.Event()
        self.emit = lambda *args: None

    def snapshot(self, model, revision):
        root = cache_folder(self.cache, model)
        folder = root/'snapshots'/revision
        folder.mkdir(parents=True, exist_ok=True)
        files = ['config.json', 'tokenizer.json', 'model.bin'] if model != SLOVAK_MODEL else [
            'config.json', 'tokenizer.json', 'preprocessor_config.json', 'model.safetensors']
        for name in files: (folder/name).write_text('{}')
        (root/'refs').mkdir(exist_ok=True)
        (root/'refs'/('v2.0' if model == SLOVAK_MODEL else 'main')).write_text(revision)
        return folder

    def test_snapshot_resolution_and_memory_key_ignore_changed_ref(self):
        for model in ('tiny', SLOVAK_MODEL):
            with self.subTest(model=model), patch('ndtranskripthor.asr.speech_models.load_backend', return_value=object()) as load:
                old = self.snapshot(model, A)
                new = self.snapshot(model, B)
                self.assertEqual(cached_path(self.cache, model), new)
                manager = ModelManager()
                try:
                    manager.get('sk', model, self.cache, True, self.emit, self.stop, revision=A)
                    manager.get('sk', model, self.cache, True, self.emit, self.stop, revision=A)
                    self.assertEqual(load.call_count, 1)
                    self.assertEqual(Path(load.call_args.kwargs['snapshot']), old)
                    manager.get('sk', model, self.cache, True, self.emit, self.stop, revision=B)
                    self.assertEqual(load.call_count, 2)
                    self.assertEqual(Path(load.call_args.kwargs['snapshot']), new)
                finally: manager.close()

    def test_missing_revision_never_substitutes_current(self):
        self.snapshot('tiny', B)
        with patch('ndtranskripthor.models.model_catalog.download') as download:
            with self.assertRaisesRegex(ValueError, A):
                ensure_model(self.cache, 'tiny', True, self.emit, self.stop, revision=A)
            download.assert_not_called()
            ensure_model(self.cache, 'tiny', False, self.emit, self.stop, revision=A)
            self.assertEqual(download.call_args.kwargs['revision'], A)
        for invalid in ('../main', 'main', '', 'x'*40):
            with self.assertRaises(ValueError): cached_path(self.cache, 'tiny', invalid)

    def test_both_backends_load_the_exact_local_directory(self):
        old = self.snapshot('tiny', A)
        with patch('faster_whisper.WhisperModel') as load:
            load_backend('tiny', self.cache, True, 'cpu', self.emit, self.stop, snapshot=str(old))
            self.assertEqual(load.call_args.args[0], str(old))
            self.assertTrue(load.call_args.kwargs['local_files_only'])
        old = self.snapshot(SLOVAK_MODEL, A)
        torch, transformers = Mock(float16='fp16', float32='fp32'), Mock()
        with patch.dict('sys.modules', torch=torch, transformers=transformers):
            load_backend(SLOVAK_MODEL, self.cache, True, 'cpu', self.emit, self.stop, snapshot=str(old))
        for loader in (transformers.AutoProcessor.from_pretrained, transformers.AutoModelForSpeechSeq2Seq.from_pretrained):
            self.assertEqual(loader.call_args.args[0], str(old))
            self.assertNotIn('revision', loader.call_args.kwargs)

    def test_batch_uses_each_projects_settings_without_overwriting_them(self):
        self.snapshot('tiny', A); self.snapshot('tiny', B)
        items, original = [], []
        for index, revision in enumerate((A, B)):
            target = self.cache/f'project{index}'
            settings = job_settings('tiny', 'cs' if index == 0 else 'sk')
            settings['model_revision'] = revision
            with Project(target, create=True) as project:
                project.initialize('audio.wav', {}, settings, [], 0)
            original.append(settings)
            items.append(dict(id=str(index), source='audio.wav', project=str(target), state='interrupted'))
        def receive(event):
            kind, value = event
            if kind == 'job':
                _, _, ack, answer = value; answer.append(True); ack.set()
        config = dict(cache=self.cache, items=items, batch_ids=['0','1'], batch_mode='retry', resume_settings=None)
        runner = BatchRunner(config, self.stop, SimpleNamespace(put=receive))
        with patch('ndtranskripthor.asr.speech_models.load_backend', return_value=SimpleNamespace(model=SimpleNamespace(device='cpu'))) as load, \
                patch('ndtranskripthor.application.asr_batch.transcribe_job', return_value=True) as job:
            runner.work(['audio.wav','audio.wav'], str(self.cache), 'en', 'small', True)
        self.assertEqual([Path(c.kwargs['snapshot']).name for c in load.call_args_list], [A, B])
        self.assertEqual([c.args[3] for c in job.call_args_list], original)
        for item, settings in zip(items, original):
            with Project(item['project']) as project:
                self.assertEqual(project.get('settings'), settings)

    def test_faster_settings_are_serializable_and_used_not_current_defaults(self):
        profile = json.loads(json.dumps(effective_settings(object())))
        self.assertEqual(profile['transcribe']['beam_size'], 5)
        self.assertIn('temperature', profile['transcribe'])
        profile['transcribe']['beam_size'] = 7
        model = Mock()
        model.transcribe.return_value = (iter([]), SimpleNamespace(language='cs'))
        transcribe_chunk(model, [0.]*16000, 'cs', None, MixedConfig(), 0, self.stop, profile)
        self.assertEqual(model.transcribe.call_args.kwargs, dict(profile['transcribe'], language='cs'))
        model.detect_language.return_value = ('cs', .99, [('cs', .99), ('sk', .01)])
        transcribe_chunk(model, [0.]*16000, 'cs-sk', None, MixedConfig(), 0, self.stop, profile)
        self.assertEqual(model.transcribe.call_args.kwargs['beam_size'], 7)

    def test_kinit_effective_beams_and_generation_defaults_are_applied(self):
        adapter = SlovakWhisper.__new__(SlovakWhisper)
        adapter.model = SimpleNamespace(generation_config=SimpleNamespace(to_dict=lambda: {'num_beams':1, 'max_length':448}))
        profile = effective_settings(adapter)
        self.assertEqual(profile['generate_kwargs']['num_beams'], 5)
        apply_settings(adapter, copy.deepcopy(profile))
        adapter.pipe = Mock(return_value={'text':'', 'chunks':[]})
        generation = Mock()
        with patch.dict('sys.modules', torch=SimpleNamespace(inference_mode=nullcontext),
                        transformers=SimpleNamespace(GenerationConfig=generation)):
            adapter.infer([0.]*16000)
        generation.from_dict.assert_called_once_with(profile['generation_config'])
        kwargs = adapter.pipe.call_args.kwargs['generate_kwargs']
        self.assertEqual(kwargs['num_beams'], 5)
        self.assertFalse(kwargs['do_sample'])
        self.assertFalse(kwargs['condition_on_prev_tokens'])
        apply_settings(adapter, None)
        with patch.dict('sys.modules', torch=SimpleNamespace(inference_mode=nullcontext)):
            adapter.infer([0.]*16000)
        self.assertEqual(adapter.pipe.call_args.kwargs['generate_kwargs'], {'language':'sk','task':'transcribe'})

    def test_checkpoint_reopen_keeps_decoding_and_records_runtime_change(self):
        import numpy as np
        source = self.cache/'source.wav'; source.write_bytes(b'fixture')
        target = self.cache/'checkpoint'
        profile = effective_settings(object())
        profile['transcribe']['beam_size'] = 7
        settings = dict(job_settings('tiny', 'sk'), model_revision=A, decoding=profile)
        calls = []
        class Model:
            def transcribe(self, audio, **kwargs):
                calls.append(kwargs)
                return iter([SimpleNamespace(start=.1, end=1., text='Preserved', words=[])]), SimpleNamespace(language='sk')
        def emit(kind, value):
            if kind == 'segment': self.stop.set()
        with patch('ndtranskripthor.audio.pcm_audio.decode_audio', return_value=np.zeros(20*16000)), \
                patch('faster_whisper.vad.get_speech_timestamps', return_value=[dict(start=0,end=96000),dict(start=160000,end=256000)]):
            self.assertFalse(transcribe_job(Model(), source, target, settings, self.stop, emit))
            with Project(target) as project:
                saved = project.get('settings')
                self.assertEqual(saved, settings)
                self.assertEqual(project.get('next_chunk'), 1)
            self.stop.clear()
            self.assertTrue(transcribe_job(Model(), source, target, saved, self.stop, self.emit,
                                          resume=True, selected_device='cuda'))
        self.assertEqual([call['beam_size'] for call in calls], [7, 7])
        with Project(target) as project:
            self.assertEqual(project.get('settings'), settings)
            self.assertEqual([s['start'] for s in project.segments()], [.1, 10.1])
            self.assertEqual([h['runtime']['device'] for h in project.get('execution_history')], ['cpu','cuda'])
            self.assertFalse(project.get('execution_history')[0]['runtime']['legacy_decoding_unknown'])

    def test_ui_missing_snapshot_online_offline_and_cancel(self):
        import tkinter as tk
        from ndtranskripthor.presentation.prepis import App
        from test_studio import destroy_window
        source = self.cache/'audio.wav'; source.write_bytes(b'fixture')
        target = self.cache/'project'
        with Project(target, create=True) as project:
            project.initialize(source, {}, dict(job_settings('tiny','cs'), model_revision=A), [], 0)
        root = tk.Tk(); root.withdraw()
        self.addCleanup(lambda: destroy_window(root))
        app = App(root, self.cache/'profile')
        app.accept_files([str(source)])
        app.items[0].update(state='interrupted', project=str(target))
        identifier = app.items[0]['id']
        with patch('ndtranskripthor.models.model_catalog.cached_path', return_value=None), patch('ndtranskripthor.presentation.prepis.messagebox.showinfo') as info, \
                patch('ndtranskripthor.presentation.prepis.messagebox.askyesno', return_value=False) as ask, patch('ndtranskripthor.presentation.prepis.threading.Thread') as thread:
            app.offline.set(True)
            app.start('retry', identifiers=[identifier])
            self.assertIn(A, info.call_args.args[1]); ask.assert_not_called(); thread.assert_not_called()
            app.offline.set(False)
            app.start('retry', identifiers=[identifier])
            self.assertIn(A, ask.call_args.args[1]); thread.assert_not_called()
            ask.return_value = True
            app.start('retry', identifiers=[identifier])
            thread.assert_called_once()
            app.busy = False


if __name__ == '__main__': unittest.main()
