"""Model-free diagnostic of the actual production window and project services."""
import json
from pathlib import Path
import sys
import time
import wave
from PySide6.QtCore import QObject
from ndtranskripthor.projects.project import Project, fingerprint


def run(app, engine, backend, output, messages):
    output = Path(output).resolve()
    def wait():
        deadline=time.monotonic()+40
        while backend.busy:
            app.processEvents(); time.sleep(.005)
            if time.monotonic()>deadline: raise TimeoutError(backend.status)
        app.processEvents()
    audio=output/'overenie č.wav'
    with wave.open(str(audio),'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE','not compressed')); stream.writeframes(b'\0\0'*96000)
    folder=output/'projekt č'
    with Project(folder,create=True) as project:
        project.initialize(audio,fingerprint(audio),{},[],96000)
        project.commit_chunk(0,[dict(start=0,end=3,text='Pôvodný č ž 日本語',words=[])],'sk'); project.finish()
    backend.add_paths([audio,audio]); assert backend.queueCount==1
    backend.open_project(folder); wait(); assert backend.audioReady and backend.duration==6, (backend.status,backend.issue,backend.duration)
    assert Path(backend.folder)==folder.resolve()
    backend.edit_active('Upravený č ž 日本語'); assert backend.dirty
    backend.save(); wait(); assert not backend.dirty,backend.status
    with Project(folder) as project:
        assert project.segments()[0]['text']=='Upravený č ž 日本語'
        assert project.segments('original')[0]['text']=='Pôvodný č ž 日本語'
    backend.export_files(['txt','srt','vtt','docx','json'],True,True,str(backend.revisions[-1])); wait()
    from ndtranskripthor.exports.export_formats import latest_bundle
    bundle=latest_bundle(folder)
    assert all((bundle/name).is_file() for name in ('prepis.txt','titulky.srt','titulky.vtt','prepis.docx','prepis.json'))
    backend.seek(2); assert backend.position==2 and not backend.playing
    window=engine.rootObjects()[0]
    for theme in ('light','dark'):
        backend.option('theme',theme); app.processEvents()
        assert window.findChild(QObject,'saveButton').property('visible')
    backend.show('home'); app.processEvents()
    # Native imports must work in the onedir package, without system Python.
    import faster_whisper
    import ctranslate2
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    import onnxruntime
    import kaldi_native_fbank
    import sounddevice
    from ndtranskripthor.application.asr_process import supervise
    backend.run_id='frozen-smoke'; backend.outcome={}
    items=[dict(row) for row in backend.queue_model.rows]
    config=dict(cache=str(output/'empty-model-cache'),batch_ids=[row['id'] for row in items],
                batch_mode='pending',resume_settings=None,items=items,ui_language='en',
                arguments=([str(audio)],str(output/'asr-results'),'sk','tiny',True,'cpu'))
    backend.launch('asr',supervise,config,backend.stop,backend.events,backend.run_id,outcome=backend.outcome)
    wait()
    assert backend.store.queue()[0]['state']=='failed',backend.status
    assert backend.store.queue()[0]['error']
    assert 'tkinter' not in sys.modules, 'Qt startup imported Tk'
    assert not messages,messages
    (output/'qml-smoke.json').write_text(json.dumps(dict(status='PASS',queue=True,original_project=True,
        immutable_original=True,save=True,exports=5,seek=True,themes=True,native_runtimes=True,
        isolated_asr_failure=True,qml_warnings=messages,tk_loaded=False)),encoding='utf-8')
    return 0
