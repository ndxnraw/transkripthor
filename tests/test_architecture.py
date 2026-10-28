"""Layer boundaries, data-only services and unchanged project interoperability."""
import ast
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ndtranskripthor.application.project_io import perform_project_io
from ndtranskripthor.application.jobs import job_settings
from ndtranskripthor.core.resources import resource_path, source_root
from ndtranskripthor.exports.export_formats import ExportOptions
from ndtranskripthor.projects.project import Project, fingerprint

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTest(unittest.TestCase):
    def test_non_ui_layers_never_depend_on_tk_or_presentation(self):
        package = ROOT/'src/ndtranskripthor'
        for path in package.rglob('*.py'):
            layer = path.relative_to(package).parts[0]
            if layer in ('presentation', 'diagnostics'):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                modules = ([node.module or ''] if isinstance(node, ast.ImportFrom) else
                           [item.name for item in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    self.assertFalse(module.startswith(('tkinter', 'ndtranskripthor.presentation',
                                                       'ndtranskripthor.diagnostics')), (path, module))
                    if layer == 'core' and module.startswith('ndtranskripthor.'):
                        self.assertTrue(module.startswith('ndtranskripthor.core.'), (path, module))
                    if layer == 'exports':
                        self.assertFalse(module.startswith('ndtranskripthor.projects'), (path, module))

    def test_services_import_without_starting_ui_or_loading_model_runtime(self):
        code = '''import sys
from ndtranskripthor.application import jobs, project_io, asr_process
from ndtranskripthor.queueing.state import StateStore
from ndtranskripthor.audio.playback import Player
assert not any(m in sys.modules for m in ('tkinter','torch','ctranslate2','faster_whisper'))
print('PASS')
'''
        run = subprocess.run([sys.executable, '-c', code], cwd=ROOT/'src', capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('PASS', run.stdout)

    def test_source_and_frozen_resources_have_one_root(self):
        self.assertEqual(source_root(), ROOT/'src')
        self.assertTrue(resource_path('assets/transkripthor.png').is_file())
        self.assertEqual(set(json.loads(resource_path('locales/en.json').read_text(encoding='utf-8'))),
                         set(json.loads(resource_path('locales/sk.json').read_text(encoding='utf-8'))))
        with tempfile.TemporaryDirectory(prefix='Thor ž 日本 ') as folder:
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', folder, create=True):
                self.assertEqual(resource_path('assets/transkripthor.png'), Path(folder)/'assets/transkripthor.png')

    def test_service_saves_revision_reopens_and_exports_without_changing_original(self):
        with tempfile.TemporaryDirectory(prefix='Thor projekt ž ') as folder:
            folder = Path(folder)
            source = folder/'zvuk.wav'; source.write_bytes(b'identity fixture')
            project_folder = folder/'projekt'
            with Project(project_folder, create=True) as project:
                project.initialize(source, fingerprint(source), job_settings('small', 'sk'), [[0,16000]], 16000)
                project.commit_chunk(0, [dict(start=0, end=1, text='Pôvodný 日本.', language='sk', words=[], speaker='')], 'sk')
                project.finish()
                original = project.segments(view='original')
                rows = project.segments()
                rows[0]['text'] = 'Upravený 日本.'
                options = project.subtitle_options()
            events = queue.Queue()
            token = ('saved', 1)
            perform_project_io(project_folder, events, rows=rows, options=options, token=token)
            self.assertEqual(events.get_nowait(), ('io_committed', token))
            self.assertEqual(events.get_nowait(), ('io_done', []))
            with Project(project_folder) as project:
                self.assertEqual(project.segments()[0]['text'], 'Upravený 日本.')
                self.assertEqual(project.segments(view='original'), original)
                revision = project.get('editor_export')['revision']
                self.assertEqual(project.next_segment_id(), rows[0]['id']+1)
            perform_project_io(project_folder, events, request=(ExportOptions(('txt','srt','vtt','docx','json')), 'revision', revision))
            self.assertEqual(events.get_nowait()[0], 'io_done')
            with Project(project_folder) as project:
                self.assertEqual(project.segments(view='original'), original)
                self.assertEqual(project.segments()[0]['text'], 'Upravený 日本.')

    def test_service_write_failure_does_not_claim_commit(self):
        events = queue.Queue()
        with patch('ndtranskripthor.application.project_io.Project', side_effect=PermissionError('fixture')):
            perform_project_io('unused', events, rows=[], token=('pending',))
        kind, issue = events.get_nowait()
        self.assertEqual(kind, 'io_error')
        self.assertEqual(issue['category'], 'permission')
        self.assertTrue(events.empty())
