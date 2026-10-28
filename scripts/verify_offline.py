"""Opt-in real CPU offline check using an existing cache and authorized audio.

Network audit blocks Python connection/DNS attempts; Windows TCP tables are
sampled for this process. Sampling is not packet capture and does not cover UDP
or other processes. Reports contain counts/technical metadata, never transcript.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import os
import struct
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def tcp_connections():
    table = ctypes.WinDLL('iphlpapi').GetExtendedTcpTable
    table.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                      wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    table.restype = wintypes.DWORD
    count = 0
    for family, stride, pid_offset in ((2, 24, 20), (23, 56, 52)):
        size = wintypes.DWORD()
        result = table(None, ctypes.byref(size), False, family, 5, 0)
        if result not in (0, 122):raise OSError(result, 'TCP table unavailable')
        buffer = ctypes.create_string_buffer(size.value)
        result = table(buffer, ctypes.byref(size), False, family, 5, 0)
        if result:raise OSError(result, 'TCP table changed/unavailable')
        rows = struct.unpack_from('<I', buffer.raw)[0]
        for index in range(rows):
            if struct.unpack_from('<I', buffer.raw, 4+index*stride+pid_offset)[0] == os.getpid():count += 1
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--audio',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',default='tiny')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    attempts=[];samples=[];sampling_errors=[];ended=threading.Event()
    def audit(event, values):
        if event in ('socket.connect','socket.getaddrinfo','socket.sendto','socket.bind'):
            attempts.append(event)
            raise RuntimeError('Network access forbidden during offline verification')
    sys.addaudithook(audit)
    os.environ['HF_HUB_OFFLINE']='1'
    def sample():
        while not ended.is_set():
            try:samples.append(tcp_connections())
            except OSError:sampling_errors.append('TCP measurement unavailable')
            ended.wait(.05)
    observer=threading.Thread(target=sample);observer.start()
    manager=None
    report=dict(status='FAIL',model=args.model,device='cpu',scope='Python network audit and sampled current-process Windows IPv4/IPv6 TCP; not packet capture/UDP/other processes')
    started=time.monotonic()
    try:
        from ndtranskripthor.models.model_catalog import cached_path, ensure_model
        from ndtranskripthor.asr.speech_models import ModelManager
        from ndtranskripthor.asr.decode_settings import effective_settings
        from ndtranskripthor.application.jobs import job_settings, transcribe_job
        from ndtranskripthor.projects.project import Project
        stop=threading.Event();emit=lambda *args:None
        ensure_model(args.cache,args.model,True,emit,stop)
        revision=cached_path(args.cache,args.model).name
        manager=ModelManager()
        model=manager.get('en',args.model,args.cache,True,emit,stop,'cpu',revision=revision)
        settings=job_settings(args.model,'en')
        settings.update(model_revision=revision,decoding=effective_settings(model))
        if not transcribe_job(model,args.audio,args.output/'project',settings,stop,emit):raise RuntimeError('Incomplete offline job')
        with Project(args.output/'project') as project:
            report.update(revision=revision,segments=len(project.segments()),complete=project.get('complete'))
        report['status']='PASS'
    finally:
        if manager:manager.close()
        ended.set();observer.join(5)
        report.update(seconds=time.monotonic()-started,python_network_attempts=len(attempts),tcp_samples=len(samples),
                      max_observed_tcp_connections=max(samples,default=None),sampling_errors=len(sampling_errors))
        if attempts or not samples or sampling_errors or any(samples):report['status']='FAIL'
        (args.output/'offline-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if report['status']!='PASS':raise SystemExit(1)
    print(json.dumps(report))


if __name__=='__main__':main()
