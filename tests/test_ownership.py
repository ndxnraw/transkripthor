import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock

from ndtranskripthor.core.ownership import Lease, OwnershipError, ProfileOwner
from ndtranskripthor.projects.project import Project
from ndtranskripthor.models.model_catalog import cache_folder, remove_model, download
from ndtranskripthor.asr.speech_models import ModelManager


class OwnershipTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()

    def child(self, code, *args):
        child = subprocess.Popen([sys.executable, '-u', '-c', code, *map(str, args)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            cwd=Path(__file__).resolve().parents[1] / 'src')
        def cleanup():
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
        self.addCleanup(cleanup)
        # Bounded wait even when startup fails or unexpectedly blocks.
        ready = []
        reader = threading.Thread(target=lambda: ready.append(child.stdout.readline()), daemon=True)
        reader.start()
        reader.join(20)
        self.assertFalse(reader.is_alive(), 'Child startup timed out')
        self.assertEqual(ready, ['READY\n'])
        return child

    def test_two_gui_processes_forward_unicode_files_without_overwriting_queue(self):
        first, second = self.folder/'prvá.wav', self.folder/'ďalšia nahrávka 日本.wav'
        first.write_bytes(b'a')
        second.write_bytes(b'b')
        profile = self.folder/'profile'
        code = '''
import json, sys, tkinter as tk
from ndtranskripthor.presentation.prepis import App
root = tk.Tk(); root.withdraw()
app = App(root, sys.argv[1])
app.accept_files([sys.argv[2]])
app.busy = True
print('READY', flush=True)
sys.stdin.readline()
app.poll()
assert len(app.items) == 1
app.busy = False
app.poll()
print(json.dumps([item['source'] for item in app.items]), flush=True)
root.destroy()
'''
        primary = self.child(code, profile, first)
        before = (profile/'queue.sqlite3').read_bytes()
        secondary = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'src' / 'prepis.py'),
            '--profile', str(profile), str(second), str(first)], capture_output=True, timeout=20)
        self.assertEqual(secondary.returncode, 0, secondary.stderr)
        self.assertEqual((profile/'queue.sqlite3').read_bytes(), before)
        primary.stdin.write('go\n'); primary.stdin.flush()
        output, errors = primary.communicate(timeout=20)
        self.assertEqual(primary.returncode, 0, errors)
        self.assertEqual(json.loads(output), [str(first), str(second)])
        self.assertFalse(list((profile/'incoming').glob('*.json')))
        with Lease(profile/'.instance.lock', reentrant=False):
            pass

    def test_crash_releases_profile_and_durable_handoff_survives(self):
        profile = self.folder/'profile'
        # Windows .venv python.exe is a redirector with a different PID from
        # the interpreter. Killing only Popen's PID can leave the lock owner
        # alive. Crash the actual interpreter without finally/atexit cleanup.
        child = self.child('from ndtranskripthor.core.ownership import ProfileOwner; import os, sys; owner=ProfileOwner(sys.argv[1]); print("READY",flush=True); sys.stdin.read(1); os._exit(17)', profile)
        request = ProfileOwner.submit(profile, [self.folder/'čaká.wav'])
        child.stdin.write('x'); child.stdin.flush()
        self.assertEqual(child.wait(timeout=10), 17)
        owner = ProfileOwner(profile)
        self.addCleanup(owner.close)
        got = []
        owner.receive(got.extend, lambda: False)
        self.assertTrue(request.exists())
        owner.receive(lambda paths: None, lambda: True)
        self.assertFalse(request.exists())
        self.assertEqual(got, [str(self.folder/'čaká.wav')])

    def test_independent_profiles_and_duplicate_owner(self):
        a, b = ProfileOwner(self.folder/'a'), ProfileOwner(self.folder/'b')
        self.addCleanup(a.close); self.addCleanup(b.close)
        with self.assertRaises(OwnershipError):
            ProfileOwner(self.folder/'a')
        ProfileOwner.submit(a.folder, [])
        self.assertFalse(list(b.inbox.iterdir()))

    def test_failed_accept_keeps_request_and_invalid_payload_is_quarantined(self):
        owner = ProfileOwner(self.folder/'profile')
        self.addCleanup(owner.close)
        source = self.folder/'audio.wav'
        source.write_bytes(b'a')
        request = ProfileOwner.submit(owner.folder, [source])
        owner.receive(lambda paths: False, lambda: True)
        self.assertTrue(request.exists())
        owner.receive(lambda paths: True, lambda: True)
        self.assertFalse(request.exists())
        (owner.inbox/'bad.json').write_text('{invalid')
        owner.receive(lambda paths: self.fail('Malformed request reached app'), lambda: True)
        self.assertTrue((owner.inbox/'bad.invalid').exists())

    def test_simultaneous_start_elects_exactly_one_owner(self):
        profile = self.folder/'profile'
        code = '''
import sys
from ndtranskripthor.core.ownership import ProfileOwner, OwnershipError
print('READY', flush=True)
sys.stdin.readline()
owner = None
try:
    owner = ProfileOwner(sys.argv[1])
    role = 'primary'
except OwnershipError:
    ProfileOwner.submit(sys.argv[1], [])
    role = 'forwarded'
print(role, flush=True)
sys.stdin.readline()
if owner: owner.close()
'''
        children = [self.child(code, profile) for _ in range(2)]
        for child in children:
            child.stdin.write('start\n'); child.stdin.flush()
        roles = []
        readers = [threading.Thread(target=lambda process=p: roles.append(process.stdout.readline()), daemon=True)
                   for p in children]
        for reader in readers:
            reader.start()
        for reader in readers:
            reader.join(10)
            self.assertFalse(reader.is_alive())
        self.assertEqual(sorted(roles), ['forwarded\n', 'primary\n'])
        for child in children:
            child.stdin.write('close\n'); child.stdin.flush()
            child.communicate(timeout=10)
            self.assertEqual(child.returncode, 0)

    def test_other_process_cannot_open_owned_project_and_crash_releases_it(self):
        folder = self.folder/'project'
        code = '''
from ndtranskripthor.projects.project import Project
from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.editor import Editor
from unittest.mock import patch
from pathlib import Path
import os, sys, tkinter as tk
folder = Path(sys.argv[1])
with Project(folder, create=True) as project:
    project.initialize('audio.wav', {}, {}, [], 16000)
    project.commit_chunk(0, [dict(start=0, end=1, text='Zachované.', words=[], speaker='')], 'sk')
root = tk.Tk(); root.withdraw()
app = App(root, folder/'isolated-profile')
with patch.object(Editor, 'load_audio'):
    editor = Editor(app, folder, parent=app.editor_page)
print('READY', flush=True)
sys.stdin.read(1)
os._exit(17)
'''
        child = self.child(code, folder)
        with self.assertRaises(OwnershipError):
            Project(folder)
        child.stdin.write('x'); child.stdin.flush()
        self.assertEqual(child.wait(timeout=10), 17)
        # Process exit can be signalled before Windows finishes releasing its
        # file handles. Still require real reacquisition and unchanged data.
        deadline = time.monotonic() + 3
        while True:
            try:
                reopened = Project(folder)
                break
            except OwnershipError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.01)
        with reopened as project:
            self.assertEqual(project.segments()[0]['text'], 'Zachované.')

    def test_loaded_model_and_download_prevent_removal(self):
        cache = self.folder/'models'
        target = cache_folder(cache, 'tiny')
        target.mkdir(parents=True)
        (target/'weights').write_bytes(b'keep')
        manager = ModelManager()
        self.addCleanup(manager.close)
        with patch('ndtranskripthor.asr.speech_models.load_backend', return_value=object()):
            manager.get('sk', 'tiny', cache, True, Mock(), threading.Event())
        with self.assertRaises(OwnershipError):
            remove_model(cache, 'tiny')
        manager.close()
        def transfer(*args):
            with self.assertRaises(OwnershipError):
                remove_model(cache, 'tiny')
        with patch('ndtranskripthor.models.download_transport.supervise', side_effect=transfer):
            download(cache, 'tiny', Mock(), threading.Event())
        remove_model(cache, 'tiny')
        self.assertFalse(target.exists())

    def test_another_profile_cannot_delete_model_cache_in_use(self):
        cache = self.folder/'models'
        target = cache_folder(cache, 'tiny')
        target.mkdir(parents=True)
        code = 'from ndtranskripthor.core.ownership import Lease; from pathlib import Path; import os, sys; lease=Lease(Path(sys.argv[1])/".models.lock"); print("READY",flush=True); sys.stdin.read(1); os._exit(17)'
        child = self.child(code, cache)
        with self.assertRaises(OwnershipError):
            remove_model(cache, 'tiny')
        self.assertTrue(target.exists())
        child.stdin.write('x'); child.stdin.flush()
        self.assertEqual(child.wait(timeout=10), 17)
        remove_model(cache, 'tiny')


if __name__ == '__main__':
    unittest.main()
