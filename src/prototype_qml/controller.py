"""QML adapter using the existing queue, project, ASR and playback services."""
from pathlib import Path
import copy
import os
import queue
import sqlite3
import threading
import uuid
from PySide6.QtCore import QObject, Signal, Slot, Property, QAbstractListModel, QModelIndex, Qt, QTimer
from PySide6.QtWidgets import QFileDialog
from ndtranskripthor.queueing.state import StateStore, queue_item
from ndtranskripthor.core.ownership import Lease
from ndtranskripthor.projects.project import Project, fingerprint
from ndtranskripthor.application.project_io import perform_project_io
from ndtranskripthor.audio.playback import Player
from ndtranskripthor.core.app_errors import explanation


class Rows(QAbstractListModel):
    def __init__(self, fields, parent=None):
        super().__init__(parent); self.fields = fields; self.rows = []
    def roleNames(self):
        return {Qt.UserRole+i+1: name.encode() for i,name in enumerate(self.fields)}
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)
    def data(self, index, role):
        number = role-Qt.UserRole-1
        if index.isValid() and 0 <= number < len(self.fields):
            field = {'bodyText': 'text', 'jobState': 'state'}.get(self.fields[number], self.fields[number])
            return self.rows[index.row()].get(field)
    def replace(self, rows):
        self.beginResetModel(); self.rows = rows; self.endResetModel()


class Controller(QObject):
    changed = Signal()
    def __init__(self, profile):
        super().__init__()
        self.profile = Path(profile)
        self.profile.mkdir(parents=True, exist_ok=True)
        self.lease = Lease(self.profile/'.qml-testing.lock', reentrant=False)
        self.store = StateStore(self.profile)
        self.queue_model = Rows(['source','jobState','project'], self)
        self.segments = Rows(['bodyText','start','end'], self)
        self.queue_model.replace(self.store.queue())
        self.events = queue.Queue(); self.stop = threading.Event()
        self.player = Player(); self.folder = None; self.project_lease = None
        self._busy=False; self._dirty=False; self._status='Testing — projekty sa otvárajú ako pracovné kópie.'
        self._progress=0.; self._duration=0.; self.thread=None; self.run_id=None
        self._asr=False
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(50)
    @Property(bool, notify=changed)
    def busy(self): return self._busy
    @Property(bool, notify=changed)
    def dirty(self): return self._dirty
    @Property(str, notify=changed)
    def status(self): return self._status
    @Property(float, notify=changed)
    def progress(self): return self._progress
    @Property(float, notify=changed)
    def duration(self): return self._duration
    @Property(float, notify=changed)
    def position(self): return self.player.position/16000
    def status_set(self, text):
        self._status=str(text); self.changed.emit()
    def launch(self, task, *, asr=False):
        if self.busy:return
        self._asr=asr
        self._busy=True; self.changed.emit()
        def work():
            try: task()
            except Exception as exc:self.events.put(('failure',f'{type(exc).__name__}: {exc}'))
            finally:self.events.put(('idle',None))
        self.thread=threading.Thread(target=work,daemon=True); self.thread.start()
    @Slot()
    def add_files(self):
        paths,_=QFileDialog.getOpenFileNames(None,'Pridať nahrávky')
        self.add_paths(paths)
    def add_paths(self, paths):
        if self.busy:return
        items=list(self.queue_model.rows); known={os.path.normcase(x['source']) for x in items}
        for name in paths:
            path=Path(name).resolve(); key=os.path.normcase(str(path))
            if path.is_file() and key not in known:items.append(queue_item(path));known.add(key)
        try:self.store.save_queue(items);self.queue_model.replace(items)
        except Exception as exc:self.status_set(exc)
    @Slot(int)
    def remove(self, index):
        if self.busy or not 0<=index<len(self.queue_model.rows):return
        items=list(self.queue_model.rows);items.pop(index)
        try:self.store.save_queue(items);self.queue_model.replace(items);self.status_set('Odstránená iba položka fronty.')
        except Exception as exc:self.status_set(exc)
    @Slot()
    def choose_project(self):
        if self.busy or self.dirty:
            self.status_set('Najprv uložte úpravy alebo počkajte na operáciu.');return
        file,_=QFileDialog.getOpenFileName(None,'Otvoriť pracovnú kópiu projektu','','Projekt (projekt.sqlite3)')
        if file:self.open_project(Path(file).parent)
    @Slot(int)
    def open_result(self,index):
        if 0<=index<len(self.queue_model.rows) and self.queue_model.rows[index]['project']:
            self.open_project(Path(self.queue_model.rows[index]['project']))
    def open_project(self, source):
        if self.busy or self.dirty:return
        self.player.close()
        self.player=Player()
        self._duration=0
        def task():
            destination=self.profile/'projects'/uuid.uuid4().hex
            destination.mkdir(parents=True)
            # Snapshot SQLite without opening/migrating or changing the original.
            with Lease(Path(source)/'.project.lock'):
                original=sqlite3.connect((Path(source)/'projekt.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
                saved=sqlite3.connect(destination/'projekt.sqlite3')
                try:original.backup(saved)
                finally:saved.close();original.close()
            with Project(destination) as project:
                problem=project.editor_problem()
                if problem:raise ValueError(problem)
                rows=project.segments();audio=project.get('source');digest=project.get('fingerprint')
            self.events.put(('opened',(destination,rows)))
            self.player.pause()
            try:
                if fingerprint(audio)!=digest:raise ValueError('Obsah zvuku sa nezhoduje.')
                length=self.player.load(audio,destination/'.pcm-cache')
                self.events.put(('audio',length))
            except Exception as exc:self.events.put(('audio_missing',str(exc)))
        self.launch(task)
    @Slot(int,result=str)
    def segment_text(self,index):
        return self.segments.rows[index]['text'] if 0<=index<len(self.segments.rows) else ''
    @Slot(int,str)
    def edit(self,index,text):
        if self.busy or not 0<=index<len(self.segments.rows):return
        row=self.segments.rows[index]
        if row['text']!=text:
            row['text']=text;row['words']=[];self._dirty=True
            self.segments.dataChanged.emit(self.segments.index(index),self.segments.index(index),[])
            self.changed.emit()
    @Slot()
    def save(self):
        if self.busy or not self.folder or not self.dirty:return
        rows=copy.deepcopy(self.segments.rows)
        self.launch(lambda:perform_project_io(self.folder,self.events,rows=rows,token='qml-save'))
    @Slot()
    def play(self):
        if self.busy:return
        try:self.player.play()
        except Exception as exc:self.status_set(exc)
    @Slot()
    def pause(self):self.player.pause()
    @Slot(float)
    def seek(self,seconds):
        if not self.busy:
            try:self.player.seek(seconds)
            except Exception as exc:self.status_set(exc)
    @Slot()
    def cancel(self):
        if self._asr:
            self.stop.set();self.status_set('Zastavujem — čakám na bezpečné ukončenie.')
        else:
            self.status_set('Dokončujem operáciu súboru; počkajte na bezpečné ukončenie.')
    @Slot(str,str,bool)
    def start(self,language,model,offline):
        if self.busy:return
        items=[dict(x) for x in self.queue_model.rows if x['state']=='waiting']
        if not items:self.status_set('Pridajte čakajúcu nahrávku.');return
        from ndtranskripthor.application.asr_process import supervise
        self.stop.clear();self.run_id=uuid.uuid4().hex;self._progress=0
        config=dict(cache=str(self.profile/'models'),batch_ids=[x['id'] for x in items],batch_mode='pending',
            resume_settings=None,items=items,ui_language='sk',
            arguments=([x['source'] for x in items],str(self.profile/'results'),language,model,offline,'cpu'))
        self.launch(lambda:supervise(config,self.stop,self.events,self.run_id),asr=True)
    def poll(self):
        for _ in range(200):
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='asr':
                run,kind,value=value
                if run!=self.run_id:continue
            if kind=='job':
                identifier,changes,ack,answer=value
                try:
                    items=[dict(x,**changes) if x['id']==identifier else x for x in self.queue_model.rows]
                    self.store.save_queue(items);self.queue_model.replace(items);answer.append(True)
                except Exception as exc:answer.append(False);self.status_set(exc)
                finally:ack.set()
            elif kind=='cpu_request':
                ack,answer=value;answer.append(False);ack.set() # prototype exposes CPU only
            elif kind=='opened':
                if self.project_lease:self.project_lease.close()
                self.folder,rows=value;self.project_lease=Lease(self.folder/'.project.lock')
                self.segments.replace(rows);self._dirty=False;self._duration=0
                self.status_set('Otvorená pracovná kópia: '+str(self.folder))
            elif kind=='audio':self._duration=value
            elif kind=='audio_missing':self._duration=0;self.status_set('Text dostupný bez prehrávania: '+value)
            elif kind=='io_committed':self._dirty=False;self.status_set('Pracovná kópia uložená; originál zachovaný.')
            elif kind in ('io_error','error'):self.status_set(explanation(value))
            elif kind=='idle':self._busy=False
            elif kind=='progress':self._progress=float(value)
            elif kind=='phase':self.status_set({'probing':'Zisťujem dĺžku zvuku','loading':'Načítavam model','preparing':'Pripravujem zvuk','transcribing':'Prepisujem'}.get(value,value))
            elif kind in ('status','failure','process_exit'):self.status_set(value)
        error=self.player.poll_error()
        if error:self.status_set(error)
        self.changed.emit()
    @Slot(result=bool)
    def can_close(self):
        if self.busy:self.cancel();return False
        if self.dirty:self.status_set('Neuložené úpravy — najprv uložte projekt.');return False
        return True
    def close(self):
        self.timer.stop();self.player.close()
        if self.project_lease:self.project_lease.close()
        self.lease.close()
