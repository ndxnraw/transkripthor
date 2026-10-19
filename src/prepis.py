"""Lokálny prepis pre Windows. Zvuk neopúšťa počítač."""
from i18n import tr
import os
import sys
import queue
import time
import threading
from pathlib import Path
from datetime import datetime
from dpi import enable_high_dpi
enable_high_dpi()
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui import build_ui, update_files
from speech_models import ModelManager, SLOVAK_MODEL, route, DEVICES, GPUError
from mixed_language import MIXED_LANGUAGE, transcribe_mixed
from state import StateStore, queue_item, ProgressClock, BatchProgress
from jobs import job_settings, transcribe_job, reserve_output
from project import Project

os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')

LANGUAGES = {'Slovenčina': 'sk', 'Čeština': 'cs', 'Čeština + slovenčina': MIXED_LANGUAGE,
             'Angličtina': 'en', 'Maďarčina': 'hu', 'Automaticky': None}
MODELS = {'Small – vyvážený': 'small', 'Medium – presnejší, pomalší': 'medium',
          'Large v3 – najvyššia kvalita, náročný': 'large-v3', 'Tiny – rýchly test': 'tiny',
          'KInIT – slovenský Large v3': SLOVAK_MODEL}

def timestamp(seconds):
    ms = max(0, round(seconds * 1000))
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def transcribe_file(model, source, folder, language, stop, emit):
    target = reserve_output(folder, Path(source).stem)
    if language == MIXED_LANGUAGE:
        segments, info = transcribe_mixed(model, str(source), stop)
    else:
        segments, info = model.transcribe(str(source), language=language, beam_size=5,
                                          vad_filter=True, condition_on_previous_text=False)
    emit('log', tr('prepis.transcribe_file.detected_language_duration_min', p0=info.language, p1=info.duration / 60))
    complete = False
    count = 0
    # Priebežné ukladanie zachová výsledok aj po prerušení alebo chybe.
    with (target / 'prepis.partial.txt').open('w', encoding='utf-8-sig') as txt, \
         (target / 'titulky.partial.srt').open('w', encoding='utf-8-sig') as srt:
        for segment in segments:
            if stop.is_set():
                break
            text = segment.text.strip()
            if text:
                count += 1
                txt.write(text + '\n')
                srt.write(f'{count}\n{timestamp(segment.start)} --> {timestamp(segment.end)}\n{text}\n\n')
                txt.flush()
                srt.flush()
                emit('text', text)
            emit('progress', min(99, 100 * segment.end / max(info.duration, 0.001)))
        else:
            complete = not stop.is_set()
    if complete:
        (target / 'prepis.partial.txt').rename(target / 'prepis.txt')
        (target / 'titulky.partial.srt').rename(target / 'titulky.srt')
        emit('progress', 100)
        if not count:
            emit('log', tr('prepis.transcribe_file.no_speech_could_be_recognized_in_the_recording'))
    return target, complete

class App:
    def __init__(self, root, state_dir=None, owner=None):
        self.root = root
        from ownership import ProfileOwner, profile_path
        self.owner = owner or ProfileOwner(state_dir or profile_path())
        def release_owner(event):
            if event.widget == root:
                try:
                    if hasattr(self, 'models'):
                        self.models.close()
                finally:
                    self.owner.close()
                    from i18n import close_diagnostics
                    close_diagnostics()
        root.bind('<Destroy>', release_owner, add='+')
        show_on_ready = root.state() != 'withdrawn'
        root.withdraw()
        self.store = StateStore(self.owner.folder)
        from i18n import set_language
        self.active_ui_language = self.store.settings(LANGUAGES, MODELS)['ui_language']
        set_language(self.active_ui_language, self.store.folder)
        self.items = self.store.queue()
        self.editors = []
        self.model_dialog = None
        self.persist_timer = None
        self.batch_ids = []
        self.batch_index = 0
        self.file_progress = 0
        self.clock = None
        self.batch_measure = BatchProgress([])
        self.phase = 'preparing'
        self.batch_mode = 'pending'
        self.events = queue.Queue(maxsize=512)
        self.stop = threading.Event()
        self.busy = False
        self.model = None
        self.model_name = None
        self.models = ModelManager()
        default_output = (Path.home() / 'Documents' / 'Prepisy' if self.store.folder.resolve() == profile_path().resolve()
                          else self.store.folder / 'results')
        build_ui(self, root, LANGUAGES, MODELS, default_output, self.store.folder / 'models')
        self.restore_settings()
        self.refresh_queue()
        for variable in (self.language, self.quality, self.output, self.offline, self.autoplay, self.device_choice, self.ui_language):
            variable.trace_add('write', lambda *_: self.schedule_save())
        self.device_choice.trace_add('write', self.device_changed)
        for variable in (self.language, self.quality, self.offline):
            variable.trace_add('write', lambda *_: self.update_readiness())
        self.update_readiness()
        root.bind('<Configure>', lambda event: self.schedule_save() if event.widget == root else None, add='+')
        from file_drop import FileDrop
        self.file_drop = FileDrop(self)
        if self.store.warning:
            self.events.put(('log', self.store.warning))
        if show_on_ready:
            root.deiconify()

    @property
    def files(self):
        return [item['source'] for item in self.items]

    @files.setter
    def files(self, paths):
        self.items = [queue_item(path) for path in paths]

    def restore_settings(self):
        from ui import apply_theme
        settings = self.store.settings(LANGUAGES, MODELS)
        self.ui_language.set(settings['ui_language'])
        self.language.set(settings.get('language', 'Slovenčina'))
        self.quality.set(settings.get('model', next(iter(MODELS))))
        self.device_choice.set(next(label for label, code in DEVICES.items() if code == settings.get('device', 'cpu')))
        self.output.set(settings.get('output', str(Path.home() / 'Documents' / 'Prepisy')))
        self.offline.set(settings.get('offline', False))
        self.autoplay.set(settings.get('autoplay', False))
        apply_theme(self, settings.get('theme', 'dark'))
        # Start at the existing DPI-aware minimum, regardless of saved geometry.

    def schedule_save(self):
        if self.persist_timer:
            self.root.after_cancel(self.persist_timer)
        self.persist_timer = self.root.after(500, self.save_state)

    def save_state(self):
        if self.owner.lease.closed:
            return False
        self.persist_timer = None
        try:
            self.store.save_settings(dict(language=self.language.get(), model=self.quality.get(), ui_language=self.ui_language.get(),
                device=DEVICES.get(self.device_choice.get(), 'cpu'),
                output=self.output.get(), theme=self.theme, offline=self.offline.get(), autoplay=self.autoplay.get(), geometry=self.root.geometry()))
            return True
        except OSError as exc:
            self.status.set(tr('prepis.save_state.could_not_save_settings_queue', p0=exc))
            return False

    def save_queue(self):
        if self.owner.lease.closed:
            return False
        try:
            self.store.save_queue(self.items)
            return True
        except Exception as exc:
            self.status.set(tr('prepis.queue_save_failed', reason=str(exc)))
            return False

    def replace_queue(self, items, selection=()):
        previous = self.items
        self.items = items
        if not self.save_queue():
            self.items = previous
            return False
        self.refresh_queue()
        for index in selection:
            self.listbox.selection_set(index)
        return True

    def reset_settings(self):
        if self.busy:
            return
        from ui import apply_theme
        self.language.set('Slovenčina')
        self.ui_language.set('en')
        self.quality.set(next(iter(MODELS)))
        self.device_choice.set(next(iter(DEVICES)))
        self.output.set(str(Path.home() / 'Documents' / 'Prepisy'))
        self.offline.set(False)
        self.autoplay.set(False)
        width, height = self.root.minsize()
        self.root.geometry(f'{width}x{height}')
        apply_theme(self, 'dark')
        self.save_state()

    def refresh_queue(self):
        self.listbox.set_items(self.items)
        update_files(self)
        self.update_selection()

    def update_selection(self):
        selected = self.listbox.curselection()
        item = self.items[selected[0]] if len(selected) == 1 else None
        idle = not self.busy
        label = tr('prepis.update_selection.open_transcript')
        actionable = bool(item and item.get('project'))
        if item and item['state'] in ('interrupted', 'failed'):
            label, actionable = (tr('prepis.update_selection.resume') if item.get('project') else tr('prepis.update_selection.try_again')), True
        self.context_button.configure(text=label, state='normal' if idle and actionable else 'disabled')
        self.queue_menu.entryconfigure(0, state='normal' if idle and item and item.get('project') and item['state'] in ('interrupted', 'failed') else 'disabled')
        self.queue_menu.entryconfigure(1, state='normal' if idle and selected else 'disabled')
        self.more_button.configure(state='normal' if idle and selected else 'disabled')
        self.info_button.configure(state='normal' if item else 'disabled')
        for button in (self.remove,):
            button.configure(state='normal' if idle and selected else 'disabled')
        for button, direction in ((self.move_up, -1), (self.move_down, 1)):
            target = selected[0]+direction if item else -1
            movable = item and item['state'] == 'waiting' and 0 <= target < len(self.items) and self.items[target]['state'] == 'waiting'
            button.configure(state='normal' if idle and movable else 'disabled')
        if item:
            detail = item['source']
            if item.get('error'):
                detail += tr('prepis.labels.error') + item['error']
            elif item['state'] == 'interrupted':
                detail += tr('prepis.update_selection.resuming_will_use_the_saved_project_settings')
            # Keep the queue usable even for lengthy backend errors; full details remain accessible.
            self.selection_info.set(detail[:260] + ('…' if len(detail) > 260 else ''))
        else:
            self.selection_info.set(tr('prepis.update_selection.selected_recordings', p0=len(selected)) if selected else tr('prepis.update_selection.select_a_recording_for_more_options'))

    def context_action(self):
        if self.busy:
            return
        selected = self.listbox.curselection()
        if len(selected) != 1:
            return
        item = self.items[selected[0]]
        if item['state'] in ('interrupted', 'failed'):
            self.start('retry', identifiers=[item['id']])
        elif item.get('project'):
            self.open_editor()

    def show_item_info(self):
        selected = self.listbox.curselection()
        if len(selected) != 1:
            return
        item = self.items[selected[0]]
        text = item['source'] + tr('prepis.labels.status') + tr('queue.'+item['state'])
        if item.get('project'):
            text += tr('prepis.labels.project') + item['project']
            try:
                with Project(item['project']) as project:
                    settings = project.get('settings', {})
                text += tr('prepis.show_item_info.saved_model_saved_language', p0=settings.get('model', '—'), p1=settings.get('language') or tr('language.auto'))
            except Exception as exc:
                text += tr('prepis.show_item_info.cannot_read_project') + str(exc)
        if item.get('error'):
            text += tr('prepis.labels.error_paragraph') + item['error'] + tr('prepis.show_item_info.check_the_file_model_and_free_disk_space_if')
        messagebox.showinfo(tr('prepis.show_item_info.recording_details'), text, parent=self.root)

    def page_changed(self, _event=None):
        if self.workspace_tabs.select() == str(self.models_page):
            self.manage_models()

    def update_readiness(self):
        from model_catalog import cached_path
        try:
            model = MODELS[self.quality.get()]
            route(LANGUAGES[self.language.get()], model)
            available = cached_path(self.cache, model) is not None
            self.readiness.set(tr('prepis.update_readiness.model_is_available_locally') if available else
                tr('prepis.update_readiness.model_is_missing_it_cannot_be_downloaded_in_offline') if self.offline.get() else
                tr('prepis.update_readiness.the_model_will_be_downloaded_on_first_use_audio'))
        except (KeyError, ValueError, OSError) as exc:
            self.readiness.set(str(exc))

    def accept_files(self, paths):
        if self.busy:
            self.status.set(tr('prepis.accept_files.cannot_add_recordings_during_transcription_stop_transcription_first'))
            return False
        from file_drop import path_key
        known = {path_key(path) for path in self.files}
        added, duplicates, invalid = [], 0, 0
        for path in paths:
            try:
                if not isinstance(path, str) or not path or not Path(path).is_file():
                    invalid += 1
                    continue
                key = path_key(path)
                if key in known:
                    duplicates += 1
                    continue
                added.append(queue_item(path))
                known.add(key)
            except (OSError, ValueError):
                invalid += 1
        if added and not self.replace_queue(self.items + added):
            return False
        self.status.set(tr('prepis.accept_files.added_skipped_duplicates_missing_files_folders_or_invalid_paths', p0=len(added), p1=duplicates + invalid, p2=duplicates, p3=invalid))
        return bool(added or duplicates)

    def add_files(self):
        files = filedialog.askopenfilenames(title=tr('prepis.add_files.select_audio_files'), filetypes=[
            (tr('prepis.labels.audio_and_video'), '*.mp3 *.wav *.m4a *.flac *.ogg *.opus *.aac *.wma *.mp4 *.mkv'), (tr('prepis.add_files.all_files'), '*.*')])
        self.accept_files(files)

    def remove_files(self):
        if self.busy:
            return
        selected = set(self.listbox.curselection())
        self.replace_queue([item for index, item in enumerate(self.items) if index not in selected])

    def move_item(self, direction):
        if self.busy:
            return
        selected = self.listbox.curselection()
        if len(selected) == 1:
            index, target = selected[0], selected[0] + direction
            if 0 <= target < len(self.items) and self.items[index]['state'] == self.items[target]['state'] == 'waiting':
                items = list(self.items)
                items[index], items[target] = items[target], items[index]
                self.replace_queue(items, (target,))

    def open_editor(self):
        selected = self.listbox.curselection()
        if not selected:
            return
        item = self.items[selected[0]]
        if item['state'] == 'processing':
            messagebox.showinfo(tr('prepis.labels.editor'), tr('prepis.open_editor.stop_transcription_before_editing_to_avoid_concurrent_changes'))
            return
        if not item.get('project'):
            messagebox.showinfo(tr('prepis.labels.editor'), tr('prepis.open_editor.this_item_has_no_saved_transcript_project_yet'))
            return
        from editor import Editor
        try:
            with Project(item['project']) as project:
                problem = project.editor_problem()
            if problem:
                messagebox.showinfo(tr('prepis.labels.editor'), problem, parent=self.root)
                return
            for editor in self.editors:
                if editor.window.winfo_exists() and editor.folder == item['project']:
                    self.workspace_tabs.select(self.editor_page)
                    return
            for editor in self.editors:
                if editor.window.winfo_exists() and not editor.close():
                    return
            self.editor_empty.pack_forget()
            self.editors.append(Editor(self, item['project'], parent=self.editor_page))
            self.workspace_tabs.select(self.editor_page)
        except Exception as exc:
            messagebox.showerror(tr('prepis.labels.editor'), str(exc))

    def manage_models(self):
        if self.model_dialog and self.model_dialog.window.winfo_exists():
            self.model_dialog.refresh()
            return
        if self.busy:
            return
        if any(editor.window.winfo_exists() and editor.speaker_busy for editor in self.editors):
            messagebox.showinfo(tr('prepis.manage_models.model_manager'), tr('prepis.manage_models.wait_for_voice_grouping_to_finish'))
            return
        from model_dialog import ModelDialog
        self.model_dialog = ModelDialog(self, parent=self.models_page)

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output.set(folder)

    def open_results(self):
        selected = self.listbox.curselection()
        folder = Path(self.items[selected[0]]['project']) if selected and self.items[selected[0]].get('project') else Path(self.output.get()).expanduser()
        if folder.is_dir():
            os.startfile(str(folder))
        else:
            messagebox.showinfo(tr('prepis.open_results.results'), tr('prepis.open_results.the_output_folder_does_not_exist_yet'))

    def start(self, mode='pending', identifiers=None):
        if self.busy:
            return
        if self.model_dialog and self.model_dialog.window.winfo_exists() and self.model_dialog.busy:
            messagebox.showinfo(tr('prepis.start.model_manager'), tr('prepis.start.wait_for_model_operations_to_finish'))
            return
        for editor in self.editors:
            if editor.window.winfo_exists() and not editor.close():
                return
        self.batch_mode = mode
        states = ('waiting',) if mode == 'pending' else ('interrupted', 'failed')
        chosen = list(self.listbox.curselection())
        selected_items = [self.items[i] for i in chosen] if mode == 'new' else self.items
        if identifiers is not None:
            selected_items = [item for item in selected_items if item['id'] in identifiers]
        selected_items = [item for item in selected_items if mode == 'new' or item['state'] in states]
        self.batch_ids = [item['id'] for item in selected_items]
        if not selected_items or not self.output.get().strip():
            messagebox.showinfo(tr('prepis.labels.transcription'), tr('prepis.start.no_suitable_items_selected_add_a_recording_retry_an'))
            return
        language, model = LANGUAGES[self.language.get()], MODELS[self.quality.get()]
        self.resume_settings = None
        try:
            if identifiers is not None and len(selected_items) == 1 and selected_items[0].get('project'):
                with Project(selected_items[0]['project']) as project:
                    self.resume_settings = project.get('settings')
                if self.resume_settings:
                    language, model = self.resume_settings['language'], self.resume_settings['model']
            route(language, model)
            from model_catalog import cached_path
            revision = self.resume_settings.get('model_revision') if self.resume_settings else None
            if revision is not None and cached_path(self.cache, model, revision) is None:
                if self.offline.get():
                    messagebox.showinfo(tr('prepis.start.model_unavailable'), tr('revision.offline', model=model, revision=revision))
                    return
                if not messagebox.askyesno(tr('prepis.start.model_unavailable'), tr('revision.download', model=model, revision=revision)):
                    return
            existing_projects = mode != 'new' and all(item.get('project') for item in selected_items)
            if self.offline.get() and not existing_projects and not self.resume_settings and cached_path(self.cache, model) is None:
                messagebox.showinfo(tr('prepis.start.model_unavailable'), tr('prepis.start.the_selected_model_is_not_stored_on_this_computer'))
                self.workspace_tabs.select(self.models_page)
                return
        except Exception as exc:
            messagebox.showinfo(tr('prepis.start.model_selection'), str(exc))
            return
        self.busy = True
        self.update_selection()
        self.stop.clear()
        for widget in (self.add, self.remove, self.lang_box, self.model_box, self.device_box, self.browse, self.output_entry, self.offline_box, self.start_button):
            widget.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.progress['value'] = 0
        self.percent.set('0 %')
        self.clock = ProgressClock(time.monotonic())
        self.batch_measure = BatchProgress(self.batch_ids)
        self.phase = 'probing'
        self.batch_index = self.file_progress = 0
        self.save_state()
        args = ([item['source'] for item in selected_items], self.output.get(), language, model, self.offline.get(), DEVICES.get(self.device_choice.get(), 'cpu'))
        import uuid
        self.asr_run = uuid.uuid4().hex
        self.asr_outcome = {}
        self.asr_config = dict(cache=str(self.cache), batch_ids=list(self.batch_ids),
            batch_mode=self.batch_mode, resume_settings=self.resume_settings,
            items=[dict(item) for item in selected_items], ui_language=self.active_ui_language,
            arguments=args)
        self.asr_thread = threading.Thread(target=self.work, args=args, daemon=True)
        self.asr_thread.start()

    def cancel(self):
        self.stop.set()
        self.set_phase('stopping')
        self.status.set(tr('prepis.cancel.stopping_after_the_current_step_partial_text_will_be'))
        self.stop_button.configure(state='disabled')

    def device_changed(self, *_):
        if not self.busy:
            self.model = None
            self.models.close()
            self.device_status.set(tr('prepis.device_changed.device_waiting_for_model_loading'))

    def confirm_cpu(self):
        """Called only on the Tk thread; closing the dialog means cancel."""
        window = tk.Toplevel(self.root)
        window.title(tr('prepis.confirm_cpu.gpu_unavailable'))
        window.transient(self.root)
        answer = [False]
        ttk.Label(window, text=tr('prepis.confirm_cpu.the_gpu_could_not_be_used_you_can_continue'), padding=20).pack()
        ttk.Label(window, text=tr('asr.cpu_deadline'), wraplength=440, padding=(20, 0, 20, 10)).pack()
        actions = ttk.Frame(window, padding=12)
        actions.pack(fill='x')
        def finish(accepted):
            answer[0] = accepted
            window.destroy()
        ttk.Button(actions, text=tr('prepis.confirm_cpu.continue_on_cpu'), command=lambda: finish(True)).pack(side='left', padx=6)
        cancel = ttk.Button(actions, text=tr('prepis.confirm_cpu.cancel'), command=lambda: finish(False))
        cancel.pack(side='right', padx=6)
        window.protocol('WM_DELETE_WINDOW', lambda: finish(False))
        window.bind('<Escape>', lambda _event: finish(False))
        window.grab_set()
        cancel.focus_set()
        expiry = self.root.after(120000, lambda: finish(False))
        try:
            self.root.wait_window(window)
        finally:
            self.root.after_cancel(expiry)
        return answer[0]

    def work(self, files, folder, language, model_name, offline, selected_device='cpu'):
        from asr_process import supervise
        supervise(self.asr_config, self.stop, self.events, self.asr_run, outcome=self.asr_outcome)

    def set_phase(self, phase):
        if phase != self.phase and self.clock:
            self.clock.samples.clear()
        self.phase = phase
        self.progress_label.set(tr('ui_layout.build_ui.recording') if phase in ('transcribing', 'saving')
                                else tr('progress.download' if phase == 'downloading' else 'progress.preparation'))
        self.progress.stop()
        measured = phase in ('transcribing', 'saving')
        self.progress.configure(mode='determinate' if measured else 'indeterminate', value=self.file_progress if measured else 0)
        self.percent.set(f'{int(self.file_progress)} %' if measured else '…')
        if not measured:
            self.progress.start(20)

    def poll(self):
        if not self.busy:
            try:
                self.owner.receive(self.accept_files, self.save_queue)
            except OSError as exc:
                self.status.set(tr('prepis.poll.forwarded_files_are_waiting_to_be_saved', p0=exc))
        # Zlučovanie udalostí: najviac jeden zápis do každého poľa na dávku.
        preview, activity, errors = [], [], []
        latest_status = latest_progress = None
        finished = False
        deadline = time.perf_counter() + 0.004
        for _ in range(200):
            if time.perf_counter() >= deadline:
                break
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'asr':
                run, kind, value = value
                if run != getattr(self, 'asr_run', None):
                    continue
            if kind == 'process_exit':
                reason, stopped = value
                items = [dict(item, state='interrupted', error=reason) if item['id'] in self.batch_ids and item['state'] == 'processing' else item for item in self.items]
                self.replace_queue(items)
                for item in items:
                    if item['state'] == 'interrupted':
                        self.batch_measure.state(item['id'], 'interrupted')
                for identifier, state in list(self.batch_measure.states.items()):
                    if state == 'processing':
                        self.batch_measure.state(identifier, 'interrupted')
                self.status.set(reason)
                activity.append(reason)
                continue
            if kind == 'download_state':
                latest_progress = None
                self.set_phase('downloading' if value else 'loading')
                self.progress.stop()
                self.progress.configure(mode='indeterminate' if value else 'determinate', value=0)
                self.percent.set('…' if value else '0 %')
                if value:
                    self.progress.start(20)
            elif kind == 'status':
                latest_status = value
            elif kind == 'phase':
                latest_progress = None
                self.set_phase(value)
                latest_status = tr('progress.phase.'+value)
            elif kind == 'duration':
                identifier, seconds = value
                self.batch_measure.duration(identifier, seconds)
                if self.clock:
                    self.clock.samples.clear()  # A changed denominator is not ASR work.
            elif kind == 'progress':
                latest_progress = value if self.phase in ('transcribing', 'saving') else None
                self.file_progress = value
                if self.batch_index < len(self.batch_ids):
                    self.batch_measure.progress(self.batch_ids[self.batch_index], value)
                fraction = self.batch_measure.fraction()
                if self.clock and self.phase == 'transcribing' and fraction is not None:
                    self.clock.update(fraction, time.monotonic())
            elif kind == 'batch_index':
                self.batch_index = value
                if value < len(self.batch_ids):
                    self.batch_measure.state(self.batch_ids[value], 'processing')
                self.file_progress = 0
                latest_progress = 0
                if self.clock:
                    self.clock.samples.clear()
            elif kind == 'device':
                self.device_status.set(tr('prepis.labels.device') + value)
            elif kind == 'cpu_request':
                self.set_phase('confirming')
                ack, answer = value
                try:
                    accepted = not self.stop.is_set() and self.confirm_cpu()
                    if accepted:
                        self.device_choice.set(next(iter(DEVICES)))
                        self.save_state()
                    answer.append(accepted)
                finally:
                    ack.set()
            elif kind == 'segment':
                preview.append(f'[{timestamp(value["start"])} – {timestamp(value["end"])}] {value["text"]}')
            elif kind == 'text':
                preview.append(value)
            elif kind == 'log':
                activity.append(value)
            elif kind == 'job':
                identifier, changes, ack, result = value
                try:
                    items = [dict(item, **changes) if item['id'] == identifier else item for item in self.items]
                    result.append(self.replace_queue(items))
                    if result[-1] and 'state' in changes:
                        self.batch_measure.state(identifier, changes['state'])
                        if changes['state'] == 'completed' and self.batch_index < len(self.batch_ids) and identifier == self.batch_ids[self.batch_index]:
                            self.file_progress = latest_progress = 100
                finally:
                    if not result:
                        result.append(False)
                    ack.set()
            elif kind == 'error':
                errors.append(value)
            elif kind == 'finished':
                finished = True
        outcome = getattr(self, 'asr_outcome', {})
        if self.busy and outcome.get('done') and outcome.get('delivery_failed'):
            finished = True
            if outcome.get('reason'):
                reason = outcome['reason']
                self.replace_queue([dict(item, state='interrupted', error=reason) if item['id'] in self.batch_ids and item['state'] == 'processing' else item for item in self.items])
                for item in self.items:
                    if item['state'] == 'interrupted':
                        self.batch_measure.state(item['id'], 'interrupted')
                for identifier, state in list(self.batch_measure.states.items()):
                    if state == 'processing':
                        self.batch_measure.state(identifier, 'interrupted')
                latest_status = reason
        if latest_status is not None and self.status.get() != latest_status:
            self.status.set(latest_status)
        if self.busy and self.stop.is_set() and not finished:
            self.status.set(tr('prepis.poll.stopping_waiting_for_the_current_transcription_or_model_transfer'))
        if latest_progress is not None:
            self.progress['value'] = latest_progress
            self.percent.set(f'{int(latest_progress)} %')
        if self.clock:
            now = time.monotonic()
            fraction = self.batch_measure.fraction()
            self.batch_progress['value'] = 0 if fraction is None else fraction * 100
            counts = self.batch_measure.counts()
            remaining = (self.clock.remaining(now) if self.phase == 'transcribing'
                         and not self.stop.is_set() and not counts['failed'] and not finished else None)
            elapsed = int(now - self.clock.started)
            estimate = max(1, round(remaining)) if remaining is not None else None
            eta = tr('prepis.poll.about', p0=estimate // 60, p1=estimate % 60) if estimate is not None else tr('prepis.poll.calculating')
            if finished or self.stop.is_set():
                eta = '—'
            coverage = tr('progress.unknown') if fraction is None else f'{fraction:.0%}'
            phase = 'finished' if finished else 'stopping' if self.stop.is_set() else self.phase
            timing = tr('progress.summary', coverage=coverage, handled=sum(counts.values()),
                        total=len(self.batch_ids), success=counts['completed'], failed=counts['failed'],
                        stopped=counts['interrupted'], minutes=elapsed//60, seconds=elapsed%60,
                        phase=tr('progress.phase.'+phase), eta=eta)
            if self.timing.get() != timing:
                self.timing.set(timing)
        for widget, lines in ((self.preview, preview), (self.activity, activity)):
            if not lines:
                continue
            follow = widget.yview()[1] >= 0.99
            widget.configure(state='normal')
            widget.insert('end', '\n'.join(lines) + '\n')
            line_count = int(widget.index('end-1c').split('.')[0])
            if line_count > 1200:
                widget.delete('1.0', f'{line_count - 1200 + 1}.0')
            if follow:
                widget.see('end')
            widget.configure(state='disabled')
        if finished:
            self.asr_run = None
            self.progress.stop()
            self.progress.configure(mode='determinate')
            self.busy = False
            self.clock = None
            self.save_state()
            for widget in (self.add, self.remove, self.browse, self.output_entry, self.offline_box, self.start_button):
                widget.configure(state='normal')
            self.lang_box.configure(state='readonly')
            self.model_box.configure(state='readonly')
            self.device_box.configure(state='readonly')
            self.stop_button.configure(state='disabled')
            self.update_selection()
            self.update_readiness()
            self.device_status.set(tr('pcm.model_released'))
            if self.model_dialog and self.model_dialog.window.winfo_exists():
                self.model_dialog.refresh()
            if getattr(self, 'close_after_asr', False):
                self.close_after_asr = False
                self.root.after_idle(self.close)
        for error in errors:
            messagebox.showerror(tr('prepis.labels.transcription_error'), error)
        self.root.after(50 if self.busy or not self.events.empty() else 250, self.poll)

    def close(self):
        if self.busy:
            self.close_after_asr = True
            self.cancel()
        else:
            for editor in self.editors:
                if editor.window.winfo_exists() and not editor.close():
                    return
            if self.model_dialog and self.model_dialog.window.winfo_exists():
                self.model_dialog.close()
                if self.model_dialog.window.winfo_exists():
                    return
            if not self.save_state():
                messagebox.showerror(tr('prepis.close.save'), tr('prepis.close.settings_queue_were_not_saved_check_free_disk_space'))
                return
            self.root.destroy()

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    if os.environ.get('ND_TRANSKRIPTHOR_DEBUG') == '1':
        import logging
        debug_folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LokalnyPrepis'
        debug_folder.mkdir(parents=True, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(debug_folder / 'asr-debug.log', maxBytes=2_000_000,
                                      backupCount=2, encoding='utf-8')
        logging.getLogger('mixed_language').addHandler(handler)
        logging.getLogger('mixed_language').setLevel(logging.DEBUG)
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test-startup':
        from startup_diagnostic import run
        sys.exit(0 if run(sys.argv[2]) else 1)
    elif len(sys.argv) == 5 and sys.argv[1] == '--self-test-process':
        from process_diagnostic import run
        sys.exit(0 if run(*sys.argv[2:]) else 1)
    elif len(sys.argv) == 3 and sys.argv[1] == '--dnd-test':
        # Isolated native Explorer QA; never load/save the user's queue.
        from file_drop import create_root
        root = create_root()
        folder = Path(sys.argv[2])
        app = App(root, folder / 'state')
        app.cache = folder / 'models'
        app.output.set(str(folder / 'results'))
        root.title('ND TranskripThor – DnD test')
        root.mainloop()
    elif len(sys.argv) == 5 and sys.argv[1] == '--self-test-download':
        import json
        from model_catalog import download, cached_path
        folder = Path(sys.argv[4])
        folder.mkdir(parents=True, exist_ok=True)
        records = []
        try:
            download(Path(sys.argv[3]), sys.argv[2], lambda kind, value: records.append((kind,value)), threading.Event())
            if not cached_path(Path(sys.argv[3]), sys.argv[2]):
                raise RuntimeError(tr('prepis.labels.downloaded_model_is_not_ready'))
            (folder/'download.json').write_text(json.dumps(dict(status='PASS',events=records),ensure_ascii=False),encoding='utf-8')
        except Exception as exc:
            (folder/'download.json').write_text(json.dumps(dict(status='FAIL',error=str(exc),events=records),ensure_ascii=False),encoding='utf-8')
            sys.exit(1)
    elif len(sys.argv) == 5 and sys.argv[1] in ('--self-test', '--self-test-sk', '--self-test-hu', '--self-test-mixed', '--self-test-v2'):
        # Diagnostika zostaveného EXE: lokálny model, zvuk a výstupný priečinok.
        import traceback
        folder = Path(sys.argv[4])
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.argv[1] == '--self-test-sk':
                from speech_models import load_backend, SLOVAK_MODEL
                model = ModelManager().get('sk', SLOVAK_MODEL, sys.argv[2], True, lambda *a: None, threading.Event())
                language = 'sk'
            else:
                model = ModelManager().get(None, sys.argv[2], folder / 'model-cache', True,
                    lambda *a: None, threading.Event(), 'cpu')
                language = 'hu' if sys.argv[1] == '--self-test-hu' else 'en'
                if sys.argv[1] in ('--self-test-mixed', '--self-test-v2'):
                    language = MIXED_LANGUAGE
            if sys.argv[1] == '--self-test-v2':
                target = reserve_output(folder, Path(sys.argv[3]).stem)
                complete = transcribe_job(model, sys.argv[3], target, job_settings('small', language), threading.Event(), lambda *a: None)
            else:
                target, complete = transcribe_file(model, sys.argv[3], folder, language, threading.Event(), lambda *a: None)
            if not complete or not (target / 'prepis.txt').read_text(encoding='utf-8-sig').strip():
                raise RuntimeError(tr('prepis.labels.diagnostic_transcription_is_empty_or_incomplete'))
            root = tk.Tk()
            root.withdraw()
            app = App(root, folder / 'test-state')
            root.update()
            if sys.argv[1] == '--self-test-v2':
                # Verify native libraries included in the Windows distribution.
                root.tk.call('package', 'present', 'tkdnd')
                import sounddevice
                sounddevice.query_devices()
                import kaldi_native_fbank
                from editor import Editor
            root.destroy()
            (folder / 'diagnostika.txt').write_text(f'OK: {complete}\n{target}', encoding='utf-8')
        except Exception:
            (folder / 'diagnostika.txt').write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
    else:
        from file_drop import create_root
        from ownership import ProfileOwner, OwnershipError, profile_path
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--profile', type=Path, default=profile_path())
        parser.add_argument('files', nargs='*')
        args = parser.parse_args()
        from i18n import set_language
        set_language(StateStore(args.profile).settings(LANGUAGES, MODELS)['ui_language'])
        try:
            owner = ProfileOwner(args.profile)
        except OwnershipError:
            try:
                ProfileOwner.submit(args.profile, args.files)
            except OSError as exc:
                error_root = tk.Tk()
                error_root.withdraw()
                messagebox.showerror(tr('prepis.labels.forward_files'), tr('prepis.labels.could_not_forward_files_to_the_running_application_add', p0=exc), parent=error_root)
                error_root.destroy()
                sys.exit(1)
            sys.exit(0)
        try:
            ProfileOwner.submit(args.profile, args.files)
            root = create_root()
            app = App(root, owner=owner)
            root.mainloop()
        finally:
            owner.close()
