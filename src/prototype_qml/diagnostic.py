"""Model-free source/frozen QML diagnostic with a synthetic, owned project."""
import json
from pathlib import Path
import time
import wave
from PySide6.QtCore import QObject
from ndtranskripthor.projects.project import Project, fingerprint


def run(app, engine, backend, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def wait():
        deadline=time.monotonic()+30
        while backend.busy:
            app.processEvents();time.sleep(.005)
            if time.monotonic()>deadline:raise TimeoutError(backend.status)
        app.processEvents()
    audio=output/'synthetic č.wav'
    with wave.open(str(audio),'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE','not compressed'));stream.writeframes(b'\0\0'*80000)
    folder=output/'original'
    with Project(folder,create=True) as project:
        project.initialize(audio,fingerprint(audio),{},[],80000)
        project.commit_chunk(0,[dict(start=0,end=2,text='Overenie č ž 日本語',words=[])],'sk');project.finish()
    backend.add_paths([audio,audio]);assert len(backend.queue_model.rows)==1
    backend.open_project(folder);wait();assert backend.duration==5
    backend.edit(0,'Upravené č ž 日本語');assert backend.dirty
    backend.save();wait();assert not backend.dirty,backend.status
    with Project(folder) as project:assert project.segments()[0]['text']=='Overenie č ž 日本語'
    with Project(backend.folder) as project:assert project.segments()[0]['text']=='Upravené č ž 日本語'
    backend.seek(2);assert backend.position==2 and not backend.player.playing
    window=engine.rootObjects()[0]
    for dark in (True,False):
        window.setProperty('dark',dark);app.processEvents()
        assert window.findChild(QObject,'saveButton') is not None
    (output/'qml-smoke.json').write_text(json.dumps(dict(status='PASS',queue=True,project_copy=True,save=True,seek=True,themes=True)),encoding='utf-8')
