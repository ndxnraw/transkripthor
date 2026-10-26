import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from eval_corpus import validate_manifest
from eval_metrics import detailed,summarize


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'audio č.wav').write_bytes(b'fixture-only-not-real-audio')
        self.row=dict(id='test',audio='audio č.wav',sha256=hashlib.sha256(b'fixture-only-not-real-audio').hexdigest(),
            duration=2,language='cs-sk',kind='real',authorized=True,rights='unit test declaration only',reviewed_by='test',tags=['switching'],
            segments=[dict(start=0,end=1,text='Eva 12',language='cs'),dict(start=1,end=2,text='Dobre',language='sk')],
            entities=[dict(start=0,end=1,text='Eva',kind='name'),dict(start=0,end=1,text='12',kind='number')])

    def manifest(self,row=None):
        p=self.root/'manifest.json'
        p.write_text(json.dumps(dict(schema=2,recordings=[row or self.row]),ensure_ascii=False),encoding='utf-8')
        return p

    def test_validated_manifest_identity_and_unicode(self):
        rows,digest=validate_manifest(self.manifest())
        self.assertEqual(len(digest),64)
        self.assertTrue(Path(rows['recordings'][0]['source']).is_file())
        for key,value in [('authorized',False),('rights',''),('reviewed_by',''),('sha256','bad'),('duration',float('nan')),('tags',[])]:
            with self.subTest(key=key):
                row=copy.deepcopy(self.row);row[key]=value
                with self.assertRaises(ValueError):validate_manifest(self.manifest(row))

    def test_invalid_reference_timing_words_entities_duplicates(self):
        for change in ('overlap','words','entity','duplicate'):
            row=copy.deepcopy(self.row)
            if change=='overlap':row['segments'][1]['start']=.5
            if change=='words':row['segments'][0]['words']=[dict(start=0,end=.5,word='wrong')]
            if change=='entity':row['entities'][0]['text']='Missing'
            p=self.manifest(row)
            if change=='duplicate':
                data=json.loads(p.read_text(encoding='utf-8'));data['recordings'].append(dict(row,id='other'));p.write_text(json.dumps(data),encoding='utf-8')
            with self.subTest(change=change),self.assertRaises(ValueError):validate_manifest(p)

    def test_text_entities_switches_and_missing_timing(self):
        ref=self.row['segments'];hyp=copy.deepcopy(ref);hyp[0]['text']='Eva 13'
        result=detailed(ref,hyp,4,2,self.row['entities'])
        self.assertAlmostEqual(result['wer'],1/3)
        self.assertEqual(result['name_error_rate'],0)
        self.assertEqual(result['number_error_rate'],1)
        self.assertEqual(result['transition_recall'],1)
        self.assertIsNone(result['word_boundary_mae_seconds'])
        hyp[1]['language']='cs'
        self.assertEqual(detailed(ref,hyp,4,2)['transition_recall'],0)

    def test_silence_has_no_fabricated_accuracy(self):
        result=detailed([],[],1,2)
        self.assertIsNone(result['wer']);self.assertIsNone(result['cer'])
        result=detailed([],self.row['segments'],1,2)
        self.assertEqual(result['inserted_words_on_empty_reference'],3)

    def test_word_timing_and_normalization(self):
        ref=[dict(start=0,end=1,text='Áno',language='sk',words=[dict(word='Áno',start=0,end=.5)])]
        hyp=[dict(start=0,end=1,text='A\u0301no',language='sk',words=[dict(word='Áno',start=.1,end=.7)])]
        result=detailed(ref,hyp,1,1)
        self.assertEqual(result['wer'],0)
        self.assertAlmostEqual(result['word_boundary_mae_seconds'],.15)
        self.assertEqual(result['timed_matched_words'],1)

    def test_scenarios_weighted_and_failures_visible(self):
        m=detailed(self.row['segments'],[],1,2,self.row['entities'])
        row=dict(id='x',model='small',revision='a'*40,device='cpu',tags=['noise','switch'],status='ok',metrics=m)
        result=summarize([row,dict(row,id='failed',status='failed')])
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['failures'],1)
        self.assertEqual(result[0]['wer'],1)
        self.assertEqual(result[0]['name_error_rate']['rate'],1)

    def test_production_job_device_revision_and_effective_settings(self):
        from evaluate_mixed import measure
        import contextlib
        project=Mock();project.segments.return_value=self.row['segments']
        project.get.side_effect=lambda key: {'samples':32000,'fingerprint':{'sha256':self.row['sha256']},'execution_history':[]}[key]
        recording=dict(self.row,source=str(self.root/'audio č.wav'))
        with patch('eval_runtime.environment',return_value={}),patch('eval_runtime.memory',return_value={'peak_working_set_bytes':12}), \
             patch('eval_runtime.GpuMemorySampler') as sampler,patch('speech_models.ModelManager') as manager, \
             patch('model_catalog.ensure_model') as ensure,patch('model_catalog.cached_path',return_value=Path('a'*40)), \
             patch('decode_settings.effective_settings',return_value={'backend':'test'}), \
             patch('decode_settings.runtime_settings',return_value={'device':'cuda'}), \
             patch('jobs.transcribe_job',return_value=True) as job,patch('project.Project',return_value=contextlib.nullcontext(project)):
            sampler.return_value.result.return_value={}
            result=measure(recording,'small','a'*40,'cuda',self.root,self.root)
            self.assertEqual(result['status'],'ok')
            self.assertEqual(job.call_args.kwargs['selected_device'],'cuda')
            self.assertEqual(job.call_args.args[3]['model_revision'],'a'*40)
            self.assertEqual(job.call_args.args[3]['decoding'],{'backend':'test'})
            self.assertEqual(manager.return_value.get.call_args.kwargs['revision'],'a'*40)
            self.assertEqual(manager.return_value.get.call_args.args[6],'cuda')
            manager.return_value.close.assert_called_once()
            self.assertTrue(ensure.call_args.args[2])

    def test_gpu_failure_not_silently_retried_on_cpu(self):
        from evaluate_mixed import measure
        with patch('eval_runtime.environment',return_value={}),patch('eval_runtime.memory',return_value={}), \
             patch('eval_runtime.GpuMemorySampler'),patch('speech_models.ModelManager') as manager, \
             patch('model_catalog.ensure_model',side_effect=RuntimeError('CUDA unavailable')):
            result=measure(self.row,'small','a'*40,'cuda',self.root,self.root)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['device'],'cuda')
            manager.return_value.get.assert_not_called()
            manager.return_value.close.assert_called_once()

    def test_cli_validation_and_failed_worker_report(self):
        from evaluate_mixed import main
        import subprocess
        manifest=self.manifest()
        with patch('sys.argv',['eval',str(manifest),'--validate-only']),patch('speech_models.ModelManager') as manager:
            main();manager.assert_not_called()
        output=self.root/'measurement'
        argv=['eval',str(manifest),'--cache',str(self.root),'--output',str(output),'--revision','small='+'a'*40,'--device','cuda']
        with patch('sys.argv',argv),patch('subprocess.run',side_effect=subprocess.TimeoutExpired('worker',1)),self.assertRaises(SystemExit):
            main()
        report=json.loads((output/'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['results'][0]['status'],'failed')
        self.assertEqual(report['results'][0]['device'],'cuda')
        self.assertIsNone(report['scenarios'][0]['wer'])
        with patch('sys.argv',argv),self.assertRaises(FileExistsError):main()
        argv=argv[:-2];argv[argv.index('--output')+1]=str(self.root/'cpu')
        with patch('sys.argv',argv),patch('subprocess.run',side_effect=subprocess.TimeoutExpired('worker',1)),self.assertRaises(SystemExit):main()
        cpu=json.loads((self.root/'cpu'/'report.json').read_text(encoding='utf-8'))
        self.assertEqual(cpu['results'][0]['device'],'cpu')

    def test_gpu_sampling_is_per_process_and_unavailable_is_not_zero(self):
        from eval_runtime import GpuMemorySampler
        import os
        sampler=GpuMemorySampler(True)
        def query(*args,**kwargs):
            sampler.stop.set()
            return Mock(returncode=0,stdout=f'99999999, 9000\n{os.getpid()}, 42\n')
        with patch('subprocess.run',side_effect=query):sampler.run()
        self.assertEqual(sampler.result()['sampled_peak_bytes'],42*1024**2)
        self.assertIsNone(GpuMemorySampler(False).result()['sampled_peak_bytes'])
