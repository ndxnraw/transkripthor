"""Production Qt adapter. Storage/ASR/export services remain UI independent."""
import copy
from pathlib import Path
import queue
import threading
import time
import uuid
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from ndtranskripthor.core.i18n import tr, set_language
from ndtranskripthor.core.ownership import ProfileOwner, profile_path
from ndtranskripthor.core.app_errors import classify, explanation
from ndtranskripthor.core.resources import resource_path
from ndtranskripthor.queueing.state import StateStore, queue_item
from ndtranskripthor.projects.project import Project
from ndtranskripthor.projects.edit_history import EditHistory
from ndtranskripthor.projects.transcript_search import occurrences
from ndtranskripthor.exports.subtitles import SubtitleOptions
from ndtranskripthor.application.project_io import perform_project_io
from ndtranskripthor.application.progress import BatchProgress, ProgressClock
from ndtranskripthor.audio.playback import Player, RATES, output_devices
from ndtranskripthor.presentation.accessibility import high_contrast_palette
from .models import Rows
from .options import LANGUAGES, MODELS
from . import workers


class Controller(QObject):
    changed = Signal()
    settingsChanged = Signal()
    selectionChanged = Signal()
    paletteChanged = Signal()
    questionRequested = Signal(str, str)
    dirtyRequested = Signal()
    closeReady = Signal()
    issueRaised = Signal(str, str)

    def __init__(self, profile=None):
        super().__init__()
        self.profile = Path(profile or profile_path()).resolve()
        self.owner = ProfileOwner(self.profile)
        self.store = StateStore(self.profile)
        self._settings = self.store.settings(LANGUAGES, MODELS)
        self._locale = self._settings.get('ui_language', 'sk')
        set_language(self._locale)
        defaults = dict(language=next(iter(LANGUAGES)), model=next(iter(MODELS)), device='cpu',
                        theme='dark', offline=False, autoplay=False,
                        output=str(Path.home()/'Documents'/'Prepisy' if self.profile == profile_path().resolve() else self.profile/'results'))
        self._settings = dict(defaults, **self._settings)
        self.cache = self.profile/'models'
        self.queue_model = Rows(['fileName','source','jobState','stateLabel','project','error','rowId'], self)
        self.queue_model.replace(self.store.queue())
        self.segments = Rows(['bodyText','start','end','speaker','language','rowId'], self)
        self.model_rows = Rows(['modelId','availability','size'], self)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.player = Player()
        self._duration = 0.
        self._audio_ready = False
        self.folder = None
        self.project_lease = None
        self.history = EditHistory()
        self._pending = {}
        self.baseline = {}
        self._structural = False
        self._cues = SubtitleOptions()
        self.saved_cues = self._cues
        self.complete_project = False
        self.next_id = 0
        self.originals = False
        self.revisions = []
        self.session = uuid.uuid4().hex
        self._selected = -1
        self._view = 'home'
        self._status = tr('qml.ready')
        self._phase = 'ready'
        self._progress = 0.
        self._task = ''
        self.thread = None
        self.run_id = None
        self.batch = BatchProgress([])
        self.clock = None
        self.current_job = None
        self.outcome = {}
        self._logs = []
        self._export_state = ''
        self._issue = ''
        self._search = ''
        self.hits = []
        self.hit = -1
        self._selection = (0, 0)
        self._closing = False
        self._closed = False
        self.deferred = None
        self.question = None
        self._diagnostic = ''
        self._diagnostic_previewed = False
        self._data_rows = []
        self._voice_baseline = {}
        self._voice_revisions = {}
        self._system = high_contrast_palette()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(50)

    @Property(bool, notify=changed)
    def busy(self): return bool(self._task)
    @Property(bool, notify=changed)
    def transcribing(self): return self._task == 'asr'
    @Property(bool, notify=changed)
    def editable(self): return bool(self.folder) and self._task not in ('open','asr','audio')
    @Property(bool, notify=changed)
    def dirty(self): return bool(self._pending) or self.history.dirty or self._cues != self.saved_cues
    @Property(str, notify=changed)
    def status(self): return self._status
    @Property(str, notify=changed)
    def phase(self): return self._phase
    @Property(str, notify=changed)
    def view(self): return self._view
    @Property(str, notify=changed)
    def projectName(self): return Path(self.folder).name if self.folder else ''
    @Property(float, notify=changed)
    def progress(self): return self._progress
    @Property(float, notify=changed)
    def batchProgress(self): return (self.batch.fraction() or 0.)*100
    @Property(str, notify=changed)
    def timing(self):
        if not self.clock: return ''
        elapsed = int(time.monotonic()-self.clock.started)
        eta = self.clock.remaining(time.monotonic()) if self._phase == 'transcribing' and not self.stop.is_set() else None
        counts = self.batch.counts()
        return tr('qml.timing', minutes=elapsed//60, seconds=elapsed%60,
                  completed=counts['completed'], failed=counts['failed'], stopped=counts['interrupted'],
                  eta=tr('qml.eta', seconds=max(1, round(eta))) if eta is not None else '—')
    @Property(str, notify=changed)
    def logs(self): return '\n'.join(self._logs[-1200:])
    @Property(str, notify=changed)
    def exportState(self): return self._export_state
    @Property(str, notify=changed)
    def issue(self): return self._issue
    @Property(str, notify=changed)
    def diagnostic(self): return self._diagnostic
    @Property(bool, notify=changed)
    def diagnosticPreviewed(self): return self._diagnostic_previewed
    @Property(str, notify=changed)
    def diagnosticPreview(self):
        from ndtranskripthor.application.local_data import NOTICE
        return NOTICE+'\n\ndiagnostics.json\n'+self._diagnostic if self._diagnostic_previewed else ''
    @Property(str, notify=changed)
    def dataOverview(self):
        return '\n\n'.join(f"{tr('data.kind.'+r['kind'])}\n{r['path']}\n{r['bytes']/1024**2:.2f} MB — {tr('data.state.'+r['state'])}" for r in self._data_rows)
    @Property(int, notify=changed)
    def queueCount(self): return len(self.queue_model.rows)
    @Property(int, notify=changed)
    def segmentCount(self): return len(self.segments.rows)
    @Property(int, notify=selectionChanged)
    def selectedIndex(self): return self._selected
    @Property('QVariantMap', notify=selectionChanged)
    def activeSegment(self):
        return dict(self.segments.rows[self._selected]) if 0 <= self._selected < len(self.segments.rows) else dict(text='',speaker='',start=0.,end=0.)
    @Property(int, notify=selectionChanged)
    def selectionStart(self): return self._selection[0]
    @Property(int, notify=selectionChanged)
    def selectionEnd(self): return self._selection[1]
    @Property(str, notify=changed)
    def searchCount(self): return f'{self.hit+1 if self.hits else 0} / {len(self.hits)}'
    @Property(float, notify=changed)
    def duration(self): return self._duration
    @Property(float, notify=changed)
    def position(self): return self.player.position/16000 if self._audio_ready else 0.
    @Property(bool, notify=changed)
    def audioReady(self): return self._audio_ready
    @Property(bool, notify=changed)
    def playing(self): return self._audio_ready and self.player.playing
    @Property(float, notify=changed)
    def playbackRate(self): return self.player.rate
    @Property('QVariantMap', notify=settingsChanged)
    def settings(self): return dict(self._settings)
    @Property('QVariantMap', notify=changed)
    def subtitleSettings(self):
        return dict(characters=self._cues.characters,lines=self._cues.lines,
                    minimum=self._cues.min_duration,maximum=self._cues.max_duration)
    @Property('QVariantList', constant=True)
    def languages(self): return [dict(value=name,label=tr('language.'+(code or 'auto'))) for name, code in LANGUAGES.items()]
    @Property('QVariantList', constant=True)
    def qualities(self): return [dict(value=name,label=tr('quality.'+('kinit' if code.startswith('kinit/') else code))) for name, code in MODELS.items()]
    @Property('QVariantList', constant=True)
    def devices(self): return [dict(value='cpu',label=tr('device.cpu')),dict(value='cuda',label=tr('device.cuda'))]
    @Property('QVariantList', notify=changed)
    def exportSources(self):
        return [dict(value=str(identifier),label=tr('exports.revision',id=identifier)) for identifier in reversed(self.revisions)] + ([dict(value='original',label=tr('exports.original'))] if self.originals else [])
    @Property(str, constant=True)
    def version(self):
        from version import DISPLAY_VERSION
        return DISPLAY_VERSION
    @Property(str, constant=True)
    def logo(self): return QUrl.fromLocalFile(str(resource_path('assets/transkripthor.png'))).toString()
    @Property('QVariantMap', notify=paletteChanged)
    def colors(self):
        if self._system: return dict(self._system, contrast=True)
        dark = self._settings['theme'] == 'dark'
        return dict(bg='#0d1526' if dark else '#f0f4fb',card='#18243b' if dark else '#ffffff',
                    field='#101b2e' if dark else '#f8faff',text='#eef2fa' if dark else '#1d293e',
                    muted='#b0bfd4' if dark else '#52627b',border='#36465f' if dark else '#d4deed',
                    blue='#9cbeff' if dark else '#245bdb',accent_text='#111d36' if dark else '#ffffff',
                    contrast=False)

    @Slot(str, result=str)
    def t(self, key): return tr(key)

    def message(self, text):
        self._status = str(text)
        self.changed.emit()

    def error(self, exc, context='disk'):
        issue = exc if isinstance(exc, dict) else classify(exc, context)
        self._issue = str(issue.get('details') or issue.get('code') or '')
        self._status = explanation(issue)
        self.issueRaised.emit(self._status, self._issue)
        self.changed.emit()

    def launch(self, name, function, *args, **kwargs):
        if self.busy: return False
        self._task = name
        self._issue = ''
        events, session = self.events, self.session
        def run():
            try: function(*args, **kwargs)
            except InterruptedError: events.put(('status', tr('qml.stopped')))
            except Exception as exc: events.put(('task_error', (name, classify(exc, 'model' if name.startswith('model') else 'disk'))))
            finally: events.put(('task_done', (name, session)))
        self.thread = threading.Thread(target=run, daemon=False)
        self.thread.start()
        self.changed.emit()
        return True

    def persist_settings(self):
        try: self.store.save_settings(self._settings); return True
        except Exception as exc: self.error(exc); return False

    @Slot(str, 'QVariant')
    def option(self, key, value):
        if key in ('language','model','device','offline','output') and self.transcribing: return
        choices = {'language':LANGUAGES,'model':MODELS,'device':('cpu','cuda'),'theme':('light','dark'),'ui_language':('sk','en')}
        if key in choices and value not in choices[key]: return
        if key in ('offline','autoplay'):
            if type(value) is not bool: return
        elif key == 'output':
            if not isinstance(value,str) or not value.strip(): return
            value = str(Path(value).expanduser())
        elif key not in choices: return
        self._settings[key] = value
        self.persist_settings()
        self.settingsChanged.emit()
        if key == 'theme': self.paletteChanged.emit()
        if key == 'ui_language': self.message(tr('settings.restart'))

    @Slot()
    def toggle_theme(self): self.option('theme','light' if self._settings['theme']=='dark' else 'dark')

    @Slot()
    def choose_output(self):
        path = QFileDialog.getExistingDirectory(None,tr('qml.output'),self._settings['output'])
        if path: self.option('output',path)

    def commit_queue(self, rows):
        try:
            self.store.save_queue(rows)
            self.queue_model.replace(rows)
            self.changed.emit()
            return True
        except Exception as exc: self.error(exc); return False

    @Slot()
    def add_files(self):
        if self.transcribing: return
        paths, _ = QFileDialog.getOpenFileNames(None,tr('ui_layout.build_ui.add_recordings'),'','Audio / video (*.wav *.mp3 *.mp4 *.m4a *.flac *.ogg *.opus *.aac *.wma *.mkv);;All files (*)')
        self.add_paths(paths)

    @Slot('QVariantList', result=bool)
    def add_urls(self, urls):
        paths = []
        for value in urls:
            url = value if isinstance(value,QUrl) else QUrl(str(value))
            if url.isLocalFile(): paths.append(url.toLocalFile())
        return self.add_paths(paths)

    def add_paths(self, paths):
        if self.transcribing: return False
        # Canonicalize locally; importing the Tk adapter would initialize Tk.
        rows = list(self.queue_model.rows)
        known = {str(Path(row['source']).resolve()).casefold() for row in rows}
        count = duplicates = invalid = 0
        for name in paths:
            path = Path(name).resolve()
            key = str(path).casefold()
            if path.is_file() and key not in known:
                rows.append(queue_item(path)); known.add(key); count += 1
            elif path.is_file(): duplicates += 1
            else: invalid += 1
        if count and not self.commit_queue(rows): return False
        self.message(tr('prepis.accept_files.added_skipped_duplicates_missing_files_folders_or_invalid_paths',p0=count,p1=duplicates+invalid,p2=duplicates,p3=invalid))
        return bool(count or duplicates)

    @Slot(int)
    def remove(self, index):
        if not self.transcribing and 0 <= index < len(self.queue_model.rows):
            self.commit_queue([row for i,row in enumerate(self.queue_model.rows) if i != index])

    @Slot(int, int)
    def move(self, index, direction):
        target = index+direction
        rows = list(self.queue_model.rows)
        if self.transcribing or not 0 <= index < len(rows) or not 0 <= target < len(rows): return
        if rows[index]['state'] != 'waiting' or rows[target]['state'] != 'waiting': return
        rows[index],rows[target] = rows[target],rows[index]
        self.commit_queue(rows)

    @Slot(str)
    def show(self, view):
        if view not in ('home','editor','models','settings','diagnostics','log'): return
        if view == 'editor' and not self.folder: return
        self._view = view
        if view == 'models' and not self.busy: self.refresh_models()
        self.changed.emit()

    def ask(self, kind, text, action):
        if self.question is not None: return
        self.question = (kind, action)
        self.questionRequested.emit(kind,text)

    @Slot(str, bool)
    def answer(self, kind, accepted):
        if self.question is None or self.question[0] != kind: return
        _, action = self.question; self.question = None
        action(accepted)

    @Slot()
    def start(self): self.start_batch('pending')

    @Slot(int, bool)
    def retry(self, index, fresh=False):
        if 0 <= index < len(self.queue_model.rows):
            self.start_batch('new' if fresh else 'retry', [self.queue_model.rows[index]['id']])

    def start_batch(self, mode, identifiers=None):
        if self.busy: return
        if self.dirty:
            self.deferred = lambda: self.start_batch(mode, identifiers)
            self.dirtyRequested.emit(); return
        items = [dict(row) for row in self.queue_model.rows if (identifiers is None or row['id'] in identifiers)
                 and (mode == 'new' or row['state'] in (('waiting',) if mode == 'pending' else ('failed','interrupted')))]
        if not items: self.message(tr('qml.add_first')); return
        language, model = LANGUAGES[self._settings['language']], MODELS[self._settings['model']]
        resume = None
        try:
            if mode == 'retry' and len(items)==1 and items[0].get('project'):
                with Project(items[0]['project']) as project: resume = project.get('settings')
                if resume: language,model = resume['language'],resume['model']
            from ndtranskripthor.asr.speech_models import route
            from ndtranskripthor.models.model_catalog import cached_path
            route(language,model)
            revision = resume.get('model_revision') if resume else None
            if self._settings['offline'] and cached_path(self.cache,model,revision) is None:
                def online(yes):
                    if yes: self.option('offline',False); self.start_batch(mode,identifiers)
                self.ask('online',tr('studio.prepare_online'),online); return
        except Exception as exc: self.error(exc,'model'); return
        from ndtranskripthor.application.asr_process import supervise
        self.stop.clear()
        self.player.close(); self.player=Player(); self._audio_ready=False
        if self.project_lease: self.project_lease.close(); self.project_lease=None
        self.folder=None; self.segments.replace([]); self.baseline={}; self._pending={}
        self.history=EditHistory(); self._selected=-1; self._cues=SubtitleOptions(); self.saved_cues=self._cues
        self.session=uuid.uuid4().hex; self.selectionChanged.emit()
        self.run_id = uuid.uuid4().hex
        self.batch = BatchProgress([row['id'] for row in items])
        self.clock = ProgressClock(time.monotonic())
        self._progress = 0.; self.current_job = None; self.outcome = {}
        self._phase = 'probing'; self._view = 'home'
        config = dict(cache=str(self.cache),batch_ids=[row['id'] for row in items],batch_mode=mode,
                      resume_settings=resume,items=items,ui_language=self._locale,
                      arguments=([row['source'] for row in items],self._settings['output'],language,model,self._settings['offline'],self._settings['device']))
        self.message(tr('progress.phase.probing'))
        self.launch('asr',supervise,config,self.stop,self.events,self.run_id,outcome=self.outcome)

    @Slot()
    def cancel(self):
        if self._task in ('asr','voices','diagnostic','audio') or self._task.startswith('model'):
            self.stop.set()
            if self._task == 'audio': self.player.stop.set()
            if self.question and self.question[0]=='cpu': self.answer('cpu',False)
            self.message(tr('qml.stopping'))
        elif self.busy: self.message(tr('qml.wait_write'))

    @Slot()
    def choose_project(self):
        if self.busy: return
        file, _ = QFileDialog.getOpenFileName(None,tr('project.open'),'','Project (projekt.sqlite3)')
        if file: self.open_project(Path(file).parent)

    @Slot(int)
    def open_result(self, index):
        if 0 <= index < len(self.queue_model.rows) and self.queue_model.rows[index].get('project'):
            self.open_project(self.queue_model.rows[index]['project'])

    def open_project(self, folder):
        if self.busy: return
        folder = Path(folder).resolve()
        if self.folder and Path(self.folder)==folder:
            self.show('editor'); return
        if self.dirty:
            self.deferred = lambda: self._open_project(folder)
            self.dirtyRequested.emit(); return
        self._open_project(folder)

    def _open_project(self, folder):
        self.session = uuid.uuid4().hex
        self.message(tr('qml.opening'))
        self.launch('open',workers.read_project,folder,self.events,self.session)

    @Slot(int)
    def select(self, index):
        if not 0 <= index < len(self.segments.rows): return
        self.flush_edits()
        self._selected = index; self._selection = (0,0)
        self.selectionChanged.emit()
        if self._settings['autoplay'] and self._audio_ready: self.play_segment()

    @Slot(str)
    def edit_active(self, text):
        if not self.editable or not 0 <= self._selected < len(self.segments.rows): return
        row = self.segments.rows[self._selected]
        if row['text'] == text: return
        identifier = row['id']
        if identifier not in self._pending: self._pending[identifier] = dict(text=row['text'],words=row.get('words',[]))
        row.update(text=text,words=[])
        self.segments.notify(self._selected)
        self.changed.emit()

    def flush_edits(self):
        if not self._pending: return
        rows = {row['id']:row for row in self.segments.rows}
        changes = [(identifier,before,dict(text=rows[identifier]['text'],words=rows[identifier].get('words',[])))
                   for identifier,before in self._pending.items() if identifier in rows]
        self._pending = {}
        self.history.record(changes)

    def record(self, changes):
        self.history.record(changes)
        self.changed.emit()

    @Slot()
    def undo(self): self.history_step(False)
    @Slot()
    def redo(self): self.history_step(True)

    def history_step(self, redo):
        if not self.editable or self._task == 'voices': return
        self.flush_edits()
        changes = self.history.step(redo)
        if changes is None: return
        rows = {row['id']:dict(row) for row in self.segments.rows}
        selected_id = self.activeSegment.get('id')
        for identifier, values in changes:
            if '__row__' in values:
                if values['__row__'] is None: rows.pop(identifier,None)
                else: rows[identifier] = dict(values['__row__'])
            elif identifier in rows: rows[identifier].update(values)
        result = sorted(rows.values(),key=lambda row:(row['start'],row['id']))
        self.segments.replace(result)
        self._selected = next((i for i,row in enumerate(result) if row['id']==selected_id),min(self._selected,len(result)-1))
        self.selectionChanged.emit(); self.changed.emit()

    @Slot(str, bool)
    def search(self, query, backwards=False):
        self.flush_edits()
        hits = [(index,start,end) for index,row in enumerate(self.segments.rows) for start,end in occurrences(row['text'],query)]
        if query != self._search or hits != self.hits: self.hit = -1 if not backwards else 0
        self._search, self.hits = query,hits
        if hits:
            self.hit = (self.hit+(-1 if backwards else 1))%len(hits)
            index,start,end = hits[self.hit]
            self.select(index)
            text = self.segments.rows[index]['text']
            self._selection = (len(text[:start].encode('utf-16-le'))//2,len(text[:end].encode('utf-16-le'))//2)
            self.selectionChanged.emit()
        else: self.hit = -1
        self.changed.emit()

    @Slot(str, bool)
    def speaker(self, name, all_same=False):
        if not self.editable or self._selected < 0: return
        self.flush_edits()
        old, name = self.activeSegment.get('speaker',''), name.strip()
        changes = []
        for index,row in enumerate(self.segments.rows):
            if index == self._selected or (all_same and row.get('speaker','')==old):
                previous = row.get('speaker','')
                if previous != name:
                    changes.append((row['id'],{'speaker':previous},{'speaker':name}))
                    row['speaker']=name
                    self._voice_revisions[row['id']] = self._voice_revisions.get(row['id'],0)+1
                    self.segments.notify(index)
        self.record(changes)

    @Slot(str, int, float, float)
    def structure(self, operation, offset, start, end):
        if self.busy or self._selected < 0 or not self.complete_project:
            self.message(tr('segments.complete_required')); return
        self.flush_edits()
        from ndtranskripthor.projects.segment_edit import split, merge, validate
        try:
            index = self._selected
            before = self.segments.rows[index:index+(2 if operation=='merge' else 1)]
            if operation == 'split':
                # QML cursor offsets use UTF-16; Python strings use code points.
                text = before[0]['text']
                position = len(text.encode('utf-16-le')[:offset*2].decode('utf-16-le'))
                after = split(before[0],position,start,self.next_id)
            elif operation == 'merge' and len(before)==2: after = [merge(*before)]
            elif operation == 'times': after = [dict(before[0],start=start,end=end,words=[],manual_timing=True)]
            else: raise ValueError(tr('segments.select'))
            rows = self.segments.rows[:index]+after+self.segments.rows[index+len(before):]
            validate(rows,self._duration)
            old, new = {row['id']:row for row in before},{row['id']:row for row in after}
            self.record([(key,{'__row__':old.get(key)},{'__row__':new.get(key)}) for key in sorted(set(old)|set(new))])
            self.next_id = max(self.next_id,max(new)+1)
            self._structural = True
            self.player.pause()
            self.segments.replace(rows)
            self._selected = index
            self.selectionChanged.emit()
        except Exception as exc: self.error(exc)

    @Slot(int, int, float, float)
    def subtitles(self, characters, lines, minimum, maximum):
        if self.transcribing: return
        try: self._cues = SubtitleOptions(characters,lines,minimum,maximum); self.changed.emit()
        except Exception as exc: self.error(exc)

    @Slot()
    def save(self):
        if self.busy or not self.folder: return
        self.flush_edits()
        current = {row['id']:row for row in self.segments.rows}
        changes = [dict(current[key]) if key in current else dict(id=key,deleted=True)
                   for key in sorted(set(current)|set(self.baseline)) if current.get(key)!=self.baseline.get(key)]
        token = (self.session,self.history.state,self._cues,copy.deepcopy(changes))
        self._export_state = tr('editor.io_saving')
        self._io_failed = False
        self.launch('save',perform_project_io,self.folder,self.events,rows=changes,
                    options=self._cues,token=token,structural=self._structural)

    @Slot('QVariantList', bool, bool, str)
    def export_files(self, formats, times, speakers, source):
        if self.busy or not self.folder: return
        if self.dirty: self.message(tr('exports.save_first')); return
        from ndtranskripthor.exports.export_formats import ExportOptions
        try:
            options = ExportOptions(tuple(formats),times,speakers)
            request = (options,'original',None) if source=='original' else (options,'revision',int(source))
            self._export_state = tr('editor.io_exporting')
            self.launch('export',perform_project_io,self.folder,self.events,request=request)
        except Exception as exc: self.error(exc)

    @Slot()
    def retry_export(self):
        if not self.busy and self.folder: self.launch('export',perform_project_io,self.folder,self.events)

    @Slot()
    def open_export(self):
        if not self.folder: return
        try:
            from ndtranskripthor.exports.export_formats import latest_bundle
            from ndtranskripthor.exports.export_pair import latest_pair
            folder = Path(self.folder)
            bundle,legacy=folder/'exporty/aktualny-balik.json',folder/'exporty/aktualny.opravene.json'
            path = latest_bundle(folder) if bundle.exists() and (not legacy.exists() or bundle.stat().st_mtime_ns>=legacy.stat().st_mtime_ns) else latest_pair(folder,'.opravene')
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc: self.error(exc)

    @Slot()
    def open_output(self):
        path = Path(self.folder or self._settings['output'])
        if path.is_dir(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else: self.message(tr('prepis.open_results.the_output_folder_does_not_exist_yet'))

    @Slot()
    def play(self):
        if not self._audio_ready: return
        try: self.player.play()
        except Exception as exc: self.error(exc,'audio')
    @Slot()
    def play_segment(self):
        if self._audio_ready and self._selected >= 0:
            try: self.player.play(self.activeSegment['start'],self.activeSegment['end'])
            except Exception as exc: self.error(exc,'audio')
    @Slot()
    def pause(self): self.player.pause()
    @Slot(float)
    def seek(self, seconds):
        if self._audio_ready:
            try: self.player.seek(seconds)
            except Exception as exc: self.error(exc,'audio')
    @Slot(result='QVariantList')
    def audio_devices(self):
        try:
            self._audio_devices = [None,*output_devices()]
            if self.player.device is not None and self.player.device not in self._audio_devices:
                self._audio_devices.append(self.player.device)
            return [tr('playback.default')]+[f'{item[1]} ({item[3]})' for item in self._audio_devices[1:]]
        except Exception as exc: self.error(exc,'audio'); self._audio_devices=[None]; return [tr('playback.default')]
    @Slot(float, int)
    def configure_audio(self, rate, device_index):
        try: self.player.configure(rate,self._audio_devices[device_index])
        except Exception as exc: self.error(exc,'audio')

    @Slot()
    def choose_audio(self):
        if not self.folder or self.busy: return
        path,_=QFileDialog.getOpenFileName(None,tr('project.audio_choose'))
        if path: self._load_audio(path,self.digest)

    def _load_audio(self, source, digest):
        self.player.close(); self.player=Player(); self._audio_ready=False
        self.launch('audio',workers.load_audio,self.player,source,digest,self.folder,self.events,self.session)

    @Slot()
    def group_voices(self):
        if self.busy or not self._audio_ready: return
        try:
            from ndtranskripthor.asr.speakers import availability
            path,reason,detail = availability(self.cache)
            if not path: self.message(reason+('\n'+detail if detail else '')); return
            self.ask('voices',tr('editor.diarize.start_local_voice_grouping_this_replaces_current_assignments_it'),lambda yes:self._group_voices(path) if yes else None)
        except Exception as exc: self.error(exc,'model')

    def _group_voices(self, path):
        self.flush_edits(); self.stop.clear()
        snapshot = tuple({key:row[key] for key in ('id','start','end')} for row in self.segments.rows)
        self._voice_baseline = {row['id']:(row['start'],row['end'],row.get('speaker',''),self._voice_revisions.get(row['id'],0)) for row in self.segments.rows}
        self.launch('voices',workers.group_voices,self.player.audio,snapshot,path,self.cache,self.stop,self.events,self.session)

    @Slot()
    def refresh_models(self):
        if not self.busy: self.launch('model-list',workers.inventory_models,self.cache,self.events)

    @Slot(int, result=str)
    def model_id(self, index):
        return self.model_rows.rows[index]['model'] if 0 <= index < len(self.model_rows.rows) else ''

    @Slot(int, result=str)
    def queue_info(self, index):
        if not 0 <= index < len(self.queue_model.rows): return ''
        row=self.queue_model.rows[index]
        return row['source']+'\n\n'+tr('queue.'+row['state'])+'\n'+row.get('project','')+'\n'+row.get('error','')

    @Slot()
    def clear_log(self): self._logs=[]; self.changed.emit()

    @Slot(str, str)
    def model_action(self, operation, model):
        if self.busy or not model: return
        if operation == 'remove':
            self.ask('remove-model',tr('model_dialog.remove.remove_local_files_for_model_recordings_and_transcripts_will',p0=model),
                     lambda yes:self._model_action(operation,model) if yes else None)
        else: self._model_action(operation,model)

    def _model_action(self, operation, model):
        self.stop.clear()
        self.launch('model-'+operation,workers.model_operation,operation,self.cache,model,self._settings['offline'],self.events,self.stop)

    @Slot()
    def inspect_data(self):
        if self.busy: return
        self._diagnostic=''; self._diagnostic_previewed=False; self.stop.clear()
        projects = [row['project'] for row in self.queue_model.rows if row.get('project')]
        if self.folder: projects.append(str(self.folder))
        self._view='diagnostics'
        self.launch('diagnostic',workers.diagnostics,self.profile,self.cache,self._settings['output'],projects,
                    [row['state'] for row in self.queue_model.rows],self._settings['offline'],self.stop,self.events)

    @Slot()
    def save_diagnostic(self):
        if self.busy or not self._diagnostic or not self._diagnostic_previewed: return
        target,_=QFileDialog.getSaveFileName(None,tr('data.save'),'ND-TranskripThor-diagnostics.zip','ZIP (*.zip)')
        if target:
            from ndtranskripthor.application.local_data import save_bundle
            self.launch('diagnostic-save',save_bundle,target,self._diagnostic)

    @Slot()
    def preview_diagnostic(self):
        if self._diagnostic: self._diagnostic_previewed=True; self.changed.emit()

    @Slot(result=bool)
    def request_close(self):
        if self.busy:
            self._closing=True; self.cancel(); return False
        if self.dirty:
            self.deferred = lambda:self.closeReady.emit()
            self.dirtyRequested.emit(); return False
        if not self.persist_settings(): return False
        return True

    @Slot(str)
    def resolve_dirty(self, action):
        if action == 'cancel': self.deferred=None; self._closing=False; return
        if action == 'discard':
            self.segments.replace(sorted(copy.deepcopy(list(self.baseline.values())),key=lambda row:(row['start'],row['id'])))
            self._pending={}; self.history=EditHistory(); self._cues=self.saved_cues
            self._selected=min(self._selected,len(self.segments.rows)-1)
            self.selectionChanged.emit()
            continuation,self.deferred=self.deferred,None
            if continuation: continuation()
        elif action == 'save': self.save()

    def poll(self):
        if self._closed: return
        system = high_contrast_palette()
        if system != self._system: self._system=system; self.paletteChanged.emit()
        if not self.transcribing:
            try: self.owner.receive(self.add_paths,lambda:True)
            except OSError as exc: self.message(exc)
        for _ in range(300):
            try: kind,value=self.events.get_nowait()
            except queue.Empty: break
            if kind == 'asr':
                run,kind,value=value
                if run != self.run_id: continue
            if kind == 'job':
                identifier,changes,ack,answer=value
                try:
                    rows=[dict(row,**changes) if row['id']==identifier else row for row in self.queue_model.rows]
                    result=self.commit_queue(rows); answer.append(result)
                    if result and 'state' in changes:
                        self.batch.state(identifier,changes['state'])
                        if changes['state']=='processing': self.current_job=identifier
                finally: ack.set()
            elif kind == 'duration': self.batch.duration(*value)
            elif kind == 'progress':
                self._progress=float(value)
                if self.current_job: self.batch.progress(self.current_job,self._progress)
                fraction=self.batch.fraction()
                if self.clock and fraction is not None and self._phase=='transcribing': self.clock.update(fraction,time.monotonic())
            elif kind == 'phase': self._phase=value; self.message(tr('progress.phase.'+value))
            elif kind == 'cpu_request':
                ack,answer=value
                def respond(yes, ack=ack, answer=answer): answer.append(yes); ack.set()
                self.ask('cpu',tr('qml.cpu_fallback'),respond)
            elif kind == 'project_opened':
                session,data,lease=value
                if session != self.session: lease.close(); continue
                if self.project_lease: self.project_lease.close()
                self.project_lease=lease; self.folder=data['folder']; self.source=data['source']; self.digest=data['fingerprint']
                self.segments.replace(data['rows']); self.baseline=copy.deepcopy({row['id']:row for row in data['rows']})
                self.complete_project=data['complete']; self._duration=data['duration'] or 0.; self.next_id=data['next_id']
                self._cues=data['subtitles']; self.saved_cues=self._cues; self.originals=data['originals']; self.revisions=data['revisions']
                self.history=EditHistory(); self._pending={}; self._structural=False; self._selected=0 if data['rows'] else -1
                self._voice_revisions={}; self._view='editor'; self._selection=(0,0)
                self.selectionChanged.emit(); self.message(tr('qml.project_open'))
            elif kind == 'audio_loaded':
                session,length=value
                if session==self.session: self._duration=length; self._audio_ready=True
            elif kind == 'io_committed':
                session,state,cues,rows=value
                if session==self.session:
                    self.history.saved=state; self.saved_cues=cues
                    for row in rows:
                        if row.get('deleted'): self.baseline.pop(row['id'],None)
                        else: self.baseline[row['id']]=row
                    self._export_state=tr('editor.init.project_saved_export_is_pending')
            elif kind == 'io_done':
                self._export_state=tr('exports.done')+ ('\n'+'\n'.join(value) if value else '')
                if self.folder:
                    with Project(self.folder) as project: self.revisions=project.revision_ids()
            elif kind in ('io_error','error'):
                self._io_failed=True; self._export_state=tr('exports.incomplete'); self.error(value)
            elif kind == 'task_error':
                task,issue=value
                if task=='audio': self._audio_ready=False; self.message(tr('project.audio_missing'))
                else: self.error(issue)
            elif kind == 'task_done':
                task,session=value
                if self.thread: self.thread.join(.1)
                self._task=''
                if task == 'open' and self.folder and session==self.session:
                    self._load_audio(self.source,self.digest)
                elif task == 'asr':
                    self._phase='finished'; self.run_id=None
                    # Any interrupted process is reflected durably in queue state.
                    stale=[dict(row,state='interrupted') if row['state']=='processing' else row for row in self.queue_model.rows]
                    if stale != self.queue_model.rows: self.commit_queue(stale)
                    self.message(str(self.outcome.get('reason') or tr('progress.phase.finished')))
                elif task == 'save' and not self.dirty and not self._io_failed and self.deferred:
                    continuation,self.deferred=self.deferred,None; continuation()
                if self._closing and not self.busy:
                    self._closing=False
                    if self.request_close(): self.closeReady.emit()
            elif kind == 'model_rows': self.model_rows.replace(value)
            elif kind == 'voices':
                session,assignments=value
                if session==self.session:
                    self.flush_edits(); changes=[]
                    for index,row in enumerate(self.segments.rows):
                        old=row.get('speaker','')
                        identity=(row['start'],row['end'],old,self._voice_revisions.get(row['id'],0))
                        if row['id'] in assignments and identity==self._voice_baseline.get(row['id']) and old!=assignments[row['id']]:
                            changes.append((row['id'],{'speaker':old},{'speaker':assignments[row['id']]}))
                            row['speaker']=assignments[row['id']]; self.segments.notify(index)
                    self.record(changes)
            elif kind == 'diagnostic': self._data_rows,self._diagnostic=value
            elif kind in ('log','text'):
                self._logs.append(str(value)); self._logs=self._logs[-1200:]
            elif kind == 'status': self._status=str(value)
        error=self.player.poll_error()
        if error: self.message(error)
        self.changed.emit()

    def close(self):
        if self._closed: return
        if self.thread and self.thread.is_alive(): raise RuntimeError('Wait for the worker before closing')
        self._closed=True; self.timer.stop(); self.player.close()
        if self.project_lease: self.project_lease.close()
        self.persist_settings(); self.owner.close()
