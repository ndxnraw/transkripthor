"""Offline reference evaluation through the application's production job pipeline."""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from ndtranskripthor.core.atomic import atomic_text
from ndtranskripthor.evaluation.eval_metrics import tokens, distance, metrics, detailed, summarize
from ndtranskripthor.evaluation.eval_corpus import validate_manifest


def measure(recording, model_name, revision, device, cache, folder):
    from ndtranskripthor.asr.speech_models import ModelManager
    from ndtranskripthor.models.model_catalog import ensure_model, cached_path, location
    from ndtranskripthor.asr.decode_settings import effective_settings, runtime_settings
    from ndtranskripthor.application.jobs import job_settings, transcribe_job
    from ndtranskripthor.projects.project import Project
    from ndtranskripthor.evaluation.eval_runtime import environment, memory, GpuMemorySampler
    stop=threading.Event()
    emit=lambda *a: None
    manager=ModelManager()
    result=dict(id=recording['id'],tags=recording['tags'],model=model_name,revision=revision,
                device=device,kind='real',status='failed',environment=environment())
    baseline=memory()
    sampler=GpuMemorySampler(device=='cuda')
    sampler.__enter__()
    started=time.perf_counter()
    try:
        ensure_model(cache,model_name,True,emit,stop,revision=revision)
        snapshot=cached_path(cache,model_name,revision)
        if snapshot is None or snapshot.name != revision:
            raise ValueError('Presná revízia modelu nie je dostupná offline.')
        model=manager.get(recording['language'],model_name,cache,True,emit,stop,device,revision=revision)
        result['load_seconds']=time.perf_counter()-started
        result['repository']=location(cache,model_name)[1]
        settings=job_settings(model_name,recording['language'])
        settings.update(model_revision=revision,decoding=effective_settings(model))
        result.update(settings=settings,runtime=runtime_settings(model,device))
        phases={}; phase=None; phase_start=time.perf_counter()
        def progress(kind,value):
            nonlocal phase,phase_start
            if kind=='phase':
                now=time.perf_counter()
                if phase: phases[phase]=phases.get(phase,0)+now-phase_start
                phase,phase_start=value,now
        began=time.perf_counter()
        complete=transcribe_job(model,recording['source'],folder/'project',settings,stop,progress,selected_device=device)
        elapsed=time.perf_counter()-began
        if phase: phases[phase]=phases.get(phase,0)+time.perf_counter()-phase_start
        result['inference_memory']=memory()
        sampler.__exit__()
        if not complete: raise InterruptedError('Meranie bolo prerušené.')
        with Project(folder/'project') as project:
            duration=project.get('samples')/16000
            if abs(duration-recording['duration'])>.05:
                raise ValueError('Referenčná dĺžka sa líši od dekódovaného zvuku o viac ako 50 ms.')
            if project.get('fingerprint')['sha256'] != recording['sha256']:
                raise ValueError('Audio sa od validácie zmenilo.')
            hypothesis=project.segments('original')
            result.update(hypothesis=hypothesis,execution_history=project.get('execution_history'),
                          fingerprint=project.get('fingerprint'))
        result.update(status='ok',phases_seconds=phases,
            metrics=detailed(recording['segments'],hypothesis,elapsed,duration,recording.get('entities',[])))
    except Exception as exc:
        from ndtranskripthor.core.app_errors import classify
        result['error']=classify(exc,'model')
    finally:
        sampler.__exit__()
        result['vram']=sampler.result()
        result['memory']=dict(baseline=baseline,final=result.pop('inference_memory',None) or memory(),scope='Isolated worker through production export, before scoring; includes imports and model load; OS peak working set')
        result['total_seconds']=time.perf_counter()-started
        manager.close()
    return result


def main():
    parser=argparse.ArgumentParser(description='Lokálne offline meranie; bez automatického GPU → CPU fallbacku.')
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--cache',type=Path)
    parser.add_argument('--models',nargs='+',default=['small'])
    parser.add_argument('--revision',action='append',default=[],help='MODEL=40-znakový commit; povinné pre každý model')
    parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--timeout',type=float,default=7200)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:
        request=json.loads(args.manifest.read_text(encoding='utf-8'))
        result=measure(**dict(request,cache=Path(request['cache']),folder=args.manifest.parent))
        atomic_text(args.manifest.parent/'result.json',json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
        return
    corpus,digest=validate_manifest(args.manifest)
    if args.validate_only:
        print(f"Platný korpus: {len(corpus['recordings'])} nahrávok; inferencia sa nespustila.")
        return
    if args.cache is None or args.output is None: parser.error('Meranie vyžaduje --cache a nový priečinok --output.')
    revisions={}
    for value in args.revision:
        model,sep,revision=value.partition('=')
        if not sep or model in revisions or not re.fullmatch('[0-9a-f]{40}',revision):
            parser.error('Revízia musí byť jedinečné MODEL=40-znakový commit.')
        revisions[model]=revision
    from ndtranskripthor.asr.speech_models import SLOVAK_MODEL, route
    import math
    if not math.isfinite(args.timeout) or args.timeout<=0: parser.error('Neplatný timeout.')
    if len(set(args.models))!=len(args.models): parser.error('Duplicitný model.')
    for model in args.models:
        if model not in ('tiny','small','medium','large-v3',SLOVAK_MODEL) or model not in revisions:
            parser.error('Neznámy model alebo chýbajúci presný commit.')
        for recording in corpus['recordings']: route(recording['language'],model)
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(schema=2,manifest_sha256=digest,results=[],scenarios=[])
    for model in args.models:
        for recording in corpus['recordings']:
            folder=args.output/f"run-{len(report['results']):04d}"
            folder.mkdir()
            request=dict(recording=recording,model_name=model,revision=revisions[model],device=args.device,
                         cache=str(args.cache.resolve()))
            request_path=folder/'request.json'
            atomic_text(request_path,json.dumps(request,ensure_ascii=False),'utf-8')
            try:
                with (folder/'worker.log').open('w',encoding='utf-8') as log:
                    subprocess.run([sys.executable,str(Path(__file__).resolve().parents[2]/'evaluate_mixed.py'),str(request_path.resolve()),'--worker'],
                                   stdout=log,stderr=log,timeout=args.timeout,check=True)
                result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
            except (subprocess.TimeoutExpired,subprocess.CalledProcessError,OSError,json.JSONDecodeError) as exc:
                result=dict(id=recording['id'],tags=recording['tags'],model=model,revision=revisions[model],
                            device=args.device,status='failed',error=type(exc).__name__)
            report['results'].append(result)
            report['scenarios']=summarize(report['results'])
            atomic_text(args.output/'report.json',json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
    print(f"Lokálne merania: {args.output/'report.json'}")
    if any(r['status']!='ok' for r in report['results']): raise SystemExit(1)


if __name__=='__main__':
    main()
