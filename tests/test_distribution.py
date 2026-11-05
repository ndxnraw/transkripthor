"""Distribution variants, notices and checksums; no model weights or user profiles."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from distribution_notices import collect


class DistributionTest(unittest.TestCase):
    def test_notices_include_notice_and_do_not_claim_missing_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); (base/'NOTICE').write_text('Copyright č 日本',encoding='utf-8')
            class Dist:
                metadata={'Name':'torch'}; version='2.8.0'; files=[Path('NOTICE')]
                def locate_file(self,path): return base/path
            result=collect(base/'notices',[Dist()])
            self.assertEqual((base/'notices/torch/NOTICE').read_text(encoding='utf-8'),'Copyright č 日本')
            self.assertEqual(result['libraries'][0]['status'],'collected')
            self.assertFalse(result['release_ready'])

    def test_missing_notice_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            class Dist:
                metadata={'Name':'torch'}; version='2.8.0'; files=[]
            self.assertIn('torch',collect(Path(folder),[Dist()])['missing_notices'])

    def test_licence_path_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as folder:
            class Dist:
                metadata={'Name':'torch'}; version='2.8.0'; files=[Path('../LICENSE')]
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                collect(Path(folder),[Dist()])

    def test_basic_kinit_error_explains_extended_package(self):
        from ndtranskripthor.asr.speech_models import SlovakWhisper
        from ndtranskripthor.core.i18n import tr
        with patch.dict(sys.modules,{'torch':None}),self.assertRaisesRegex(RuntimeError,'KInIT') as caught:
            SlovakWhisper.__new__(SlovakWhisper).load()
        self.assertEqual(str(caught.exception),tr('distribution.kinit_requires_extended'))

    def test_basic_is_separate_and_default_stays_extended(self):
        spec=(ROOT/'packaging/TranskripTHOR.spec').read_text(encoding='utf-8')
        script=(ROOT/'scripts/build.ps1').read_text(encoding='utf-8')
        self.assertIn("['torch', 'transformers'] if basic else []",spec)
        self.assertIn("$Variant = 'extended'",script)
        self.assertIn('dist/basic',script)
        self.assertLess(script.index('test.ps1'),script.index('freeze.py'))
