"""Small cache fixtures: explicit hashing versus cheap inventory checks."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from model_catalog import cache_folder, inventory, snapshot_state, verify_model
from download_worker import verify_file, IntegrityError
from i18n import set_language


class IntegrityTest(unittest.TestCase):
    def setUp(self):
        set_language('en')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)
        root = cache_folder(self.cache, 'tiny')
        self.path = root/'snapshots'/('a'*40)
        self.path.mkdir(parents=True)
        (root/'refs').mkdir()
        (root/'refs'/'main').write_text('a'*40)
        self.files = {'config.json': b'{}', 'tokenizer.json': b'{}', 'model.bin': b'weights'}
        for name, data in self.files.items(): (self.path/name).write_bytes(data)
        self.stop = threading.Event()
        self.events = []

    def receipt(self):
        files = {}
        for name, data in self.files.items():
            stat = (self.path/name).stat()
            files[name] = dict(size=len(data), digest=hashlib.sha256(data).hexdigest(),
                               mtime=stat.st_mtime_ns, ctime=stat.st_ctime_ns)
        (self.path/'.nd-verified.json').write_text(json.dumps(dict(complete=True, files=files)))

    def verify(self):
        verify_model(self.cache, 'tiny', True, lambda *args: self.events.append(args), self.stop)

    def test_inventory_distinguishes_missing_found_verified_and_changed_without_hashing(self):
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'found')
        self.receipt()
        with patch('download_worker.verify_file', side_effect=AssertionError('Inventory must not hash')):
            rows = {row['model']:row for row in inventory(self.cache)}
        self.assertEqual(rows['tiny']['state'], 'verified')
        self.assertEqual(rows['small']['state'], 'missing')
        (self.path/'model.bin').write_bytes(b'incomplete')
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'incomplete')

    def test_missing_weight_and_invalid_receipt_are_not_verified(self):
        (self.path/'model.bin').unlink()
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'incomplete')
        (self.path/'model.bin').write_bytes(b'weights')
        (self.path/'.nd-verified.json').write_text('{broken')
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'incomplete')

    def test_receipt_without_digest_is_not_integrity_proof(self):
        self.receipt()
        file = self.path/'.nd-verified.json'
        receipt = json.loads(file.read_text())
        del receipt['files']['model.bin']['digest']
        file.write_text(json.dumps(receipt))
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'incomplete')

    def test_legacy_offline_cache_requires_trusted_metadata(self):
        with self.assertRaisesRegex(ValueError, 'Turn off offline'):
            self.verify()
        self.assertFalse((self.path/'.nd-verified.json').exists())
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'found')

    def test_explicit_offline_verification_and_modified_metadata(self):
        self.receipt()
        file = self.path/'model.bin'
        stat = file.stat()
        os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns+10000000))
        self.verify()
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'verified')
        self.assertTrue(any('verified' in value for kind, value in self.events))

    def test_same_size_corruption_detected_without_deleting_bytes(self):
        self.receipt()
        file = self.path/'model.bin'
        stat = file.stat()
        file.write_bytes(b'corrupt')
        os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, 'Files were preserved'):
            self.verify()
        self.assertEqual(file.read_bytes(), b'corrupt')
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'incomplete')

    def test_cancel_preserves_cache_and_allows_retry(self):
        self.receipt()
        self.stop.set()
        with self.assertRaises(InterruptedError): self.verify()
        self.assertEqual((self.path/'model.bin').read_bytes(), b'weights')
        self.stop.clear()
        self.verify()
        self.assertEqual(snapshot_state(self.path, 'tiny'), 'verified')

    def test_file_mutation_during_hash_is_rejected(self):
        file = self.path/'model.bin'
        def progress(event):
            if event['bytes'] == event['total']:
                file.write_bytes(b'changed-after-hash')
        with self.assertRaises(IntegrityError):
            verify_file(file, 7, hashlib.sha256(b'weights').hexdigest(), progress, 'model.bin')

    def test_inventory_follows_changed_ref_and_survives_bad_ref(self):
        self.receipt()
        ref = self.path.parent.parent/'refs'/'main'
        ref.write_text('b'*40)
        self.assertEqual(inventory(self.cache)[0]['state'], 'incomplete')
        ref.write_bytes(b'\xff')
        self.assertEqual(inventory(self.cache)[0]['state'], 'incomplete')

    def test_explicit_online_verification_pins_snapshot(self):
        with patch('download_transport.supervise') as supervise:
            verify_model(self.cache, 'tiny', False, lambda *args: None, self.stop)
        self.assertEqual(supervise.call_args.kwargs, dict(revision='a'*40, verify_only=True))
