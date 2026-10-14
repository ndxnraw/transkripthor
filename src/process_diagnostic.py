"""Offline diagnostic of the actual spawned ASR pipeline in a frozen build."""
import json
import os
import queue
import threading
import time
from pathlib import Path
from asr_process import supervise
from project import Project


def run(cache, audio, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    item = dict(id='diagnostic', source=str(Path(audio).resolve()), project='', state='waiting', error='')
    config = dict(cache=str(Path(cache).resolve()), batch_ids=[item['id']], batch_mode='new',
        resume_settings=None, items=[dict(item)], ui_language='en',
        arguments=([item['source']], str(folder.resolve()/'results'), 'cs-sk', 'tiny', True, 'cpu'))
    events, stop, outcome = queue.Queue(), threading.Event(), {}
    records = []
    bridge = threading.Thread(target=supervise, args=(config, stop, events, 'frozen-diagnostic'),
                              kwargs=dict(outcome=outcome))
    started = time.monotonic()
    bridge.start()
    try:
        while bridge.is_alive() or not events.empty():
            if time.monotonic()-started > 180:
                stop.set()
            try:
                _, (_, kind, value) = events.get(timeout=.1)
            except queue.Empty:
                continue
            if kind == 'job':
                identifier, changes, ack, answer = value
                item.update(changes)
                answer.append(True); ack.set()
                value = (identifier, changes)
            elif kind == 'cpu_request':
                ack, answer = value
                answer.append(False); ack.set()
                value = 'declined'
            records.append((kind, value))
        bridge.join()
        if outcome.get('reason') or item['state'] != 'completed':
            raise RuntimeError(outcome.get('reason') or item['error'] or item['state'])
        with Project(item['project']) as project:
            segments = project.segments()
            if not project.get('complete') or not segments:
                raise RuntimeError('Incomplete or empty project')
        if not (Path(item['project'])/'prepis.txt').read_text(encoding='utf-8-sig').strip():
            raise RuntimeError('Empty TXT export')
        result = dict(status='PASS', parent_pid=os.getpid(), seconds=time.monotonic()-started,
                      project=item['project'], segments=len(segments), events=records)
    except Exception as exc:
        result = dict(status='FAIL', error=f'{type(exc).__name__}: {exc}', events=records)
    finally:
        stop.set(); bridge.join(15)
    (folder/'process-diagnostic.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result['status'] == 'PASS'
