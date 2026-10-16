"""Complete transcript editor, paged presentation, local audio playback."""
from i18n import tr
from pathlib import Path
import queue
import threading
from types import MappingProxyType
from ownership import Lease
from responsive import MessageView, FlowFrame
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from project import Project, fingerprint
from playback import Player
from subtitles import SubtitleOptions, timestamp
from ui import palette_for
from edit_history import EditHistory


class Editor:
    PAGE_SIZE = 40

    def __init__(self, app, folder, parent=None):
        self.app, self.folder = app, folder
        with Project(folder) as project:
            problem = project.editor_problem()
            if problem:
                raise ValueError(problem)
            self.segments = project.segments()
            self.source, self.digest = project.get('source'), project.get('fingerprint')
            original_available = project.original_available()
            export_request = project.get('editor_export')
            subtitle_options = project.subtitle_options()
            self.project_lease = Lease(Path(folder)/'.project.lock')
        self.embedded = parent is not None
        self.window = tk.Frame(parent) if self.embedded else tk.Toplevel(app.root)
        self.window.bind('<Destroy>', lambda event: self.project_lease.close() if event.widget == self.window else None, add='+')
        if self.embedded:
            app.editor_empty.pack_forget()
            self.window.pack(fill='both', expand=True)
        else:
            self.window.title(tr('editor.labels.transcript_editor_nd_transkripthor'))
            scale = max(1, app.root.winfo_fpixels('1i')/96)
            self.window.geometry(f'{min(round(1080*scale), app.root.winfo_screenwidth()-40)}x{min(round(730*scale), app.root.winfo_screenheight()-80)}+20+20')
            self.window.minsize(750, 550)
            self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.current = None
        self.history = EditHistory()
        self.pending_segments = {}
        self.edit_serial = 0
        self.io_busy = False
        self.io_saved = False
        self.io_success = False
        self.segment_indices = {item['id']: index for index, item in enumerate(self.segments)}
        self.dirty = False
        self.loading_text = False
        self.page = 0
        self.matches = list(range(len(self.segments)))
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.speaker_busy = False
        self.speaker_revisions = {}
        self.speaker_job = None
        self.voice_check = None
        self.player = Player()
        outer = ttk.Frame(self.window, padding=8)
        outer.pack(fill='both', expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill='x', pady=(0, 4))
        self.saved_state = tk.StringVar(value=tr('editor.init.all_changes_saved'))
        ttk.Label(heading, textvariable=self.saved_state, style='Muted.TLabel').pack(side='right')
        self.source_label = MessageView(heading, app, text=Path(self.source).name +
            ('' if original_available else tr('editor.init.original_transcript_cannot_be_verified')), lines=1)
        self.source_label.pack(side='left', fill='x', expand=True)
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x')
        self.query = tk.StringVar()
        ttk.Label(toolbar, text=tr('accessibility.search')).pack(side='left', padx=(0, 4))
        search = ttk.Entry(toolbar, textvariable=self.query)
        self.search_entry = search
        search.pack(side='left', fill='x', expand=True)
        search.bind('<Return>', lambda _: self.search())
        ttk.Button(toolbar, width=0, padding=(8, 2), text=tr('editor.init.search'), command=self.search).pack(side='left', padx=4)
        ttk.Button(toolbar, width=0, padding=(8, 2), text=tr('editor.init.next_match'), command=self.next_match).pack(side='left')
        ttk.Button(toolbar, width=0, padding=(8, 2), text=tr('editor.init.save_txt_srt'), style='Accent.TButton', command=self.save).pack(side='right', padx=(8, 0))
        # Pack fixed controls first so they remain accessible at minimum size.
        bottom = ttk.Frame(outer)
        bottom.pack(side='bottom', fill='x')
        self.status = tk.StringVar(value=tr('editor.init.preparing_audio_selecting_a_segment_does_not_start_playback'))
        self.status_label = MessageView(bottom, app, textvariable=self.status, lines=1)
        self.status_label.pack(side='bottom', fill='x', pady=2)
        self.export_state = tk.StringVar(value=tr('editor.init.export_has_not_been_saved_yet') if not export_request else
            (tr('editor.init.txt_srt_export_complete') if export_request['state'] == 'complete' else tr('editor.init.project_saved_export_is_pending')))
        export_bar = ttk.Frame(bottom)
        export_bar.pack(side='bottom', fill='x')
        ttk.Button(export_bar, width=0, padding=(8, 2), text=tr('editor.init.retry_export'), command=self.retry_export).pack(side='right')
        ttk.Button(export_bar, width=0, padding=(8, 2), text=tr('editor.init.open_export'), command=self.open_export).pack(side='right', padx=4)
        ttk.Label(export_bar, textvariable=self.export_state, style='Muted.TLabel').pack(side='left')
        playback = FlowFrame(bottom)
        playback.pack(fill='x', pady=4)
        details_toggle = ttk.Button(heading, width=0, padding=(8, 2), text=tr('editor.init.segment_and_subtitles'), command=self.toggle_details)
        details_toggle.pack(side='right', padx=(4, 0))
        self.details = ttk.Frame(bottom)
        from transcript_blocks import TranscriptBlocks
        self.tree = TranscriptBlocks(outer, self)
        self.tree.pack(fill='both', expand=True, pady=(8, 0))
        pages = ttk.Frame(bottom)
        pages.pack(fill='x')
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.init.previous_segments'), command=lambda: self.change_page(-1)).pack(side='left')
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.init.next_segments'), command=lambda: self.change_page(1)).pack(side='left', padx=5)
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.undo'), command=self.undo).pack(side='left', padx=4)
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.redo'), command=self.redo).pack(side='left')
        self.page_label = tk.StringVar()
        ttk.Label(pages, textvariable=self.page_label).pack(side='right')
        # Replaced by an inline Text when a block is selected.
        self.text = tk.Text(self.window)
        voice = FlowFrame(self.details)
        voice.pack(fill='x')
        ttk.Label(voice, text=tr('editor.init.segment_speaker')).pack(side='left')
        self.speaker = tk.StringVar()
        self.speaker_entry = ttk.Combobox(voice, textvariable=self.speaker, width=12,
                                        postcommand=self.refresh_speaker_choices)
        self.speaker_entry.pack(side='left')
        self.speaker.trace_add('write', self.speaker_changed)
        ttk.Button(voice, width=0, padding=(8, 2), text=tr('editor.init.rename_voice'), command=self.rename_speaker).pack(side='left', padx=4)
        self.speaker_button = ttk.Button(voice, width=0, padding=(8, 2), text=tr('editor.init.group_similar_voices'), command=self.diarize)
        self.speaker_button.pack(side='right')
        self.speaker_button.configure(state='disabled')
        voice_info = ttk.Frame(self.details)
        voice_info.pack(fill='x')
        ttk.Button(voice_info, width=0, padding=(8, 2), text=tr('voices.help_title'), command=self.voice_help).pack(side='right')
        self.voice_status = tk.StringVar(value=tr('voices.checking'))
        MessageView(voice_info, app, textvariable=self.voice_status, lines=1).pack(side='left', fill='x', expand=True)
        self.details.bind('<Map>', lambda event: self.refresh_voice_availability() if event.widget == self.details else None)
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.segment'), command=self.play_segment).pack(side='left')
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.resume'), command=self.play).pack(side='left')
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.pause'), command=self.player.pause).pack(side='left')
        self.position = tk.DoubleVar(value=0)
        self.slider = ttk.Scale(playback, variable=self.position, from_=0, to=1)
        playback.stretch = self.slider
        self.slider.pack(side='left', fill='x', expand=True, padx=8)
        self.dragging = False
        self.slider.bind('<ButtonPress-1>', self.begin_seek)
        self.slider.bind('<ButtonRelease-1>', self.seek)
        for key, delta in (('<Left>', -5), ('<Right>', 5)):
            self.slider.bind(key, lambda event, amount=delta: self.keyboard_seek(amount))
        self.clock = tk.StringVar(value='00:00:00,000')
        ttk.Label(playback, textvariable=self.clock).pack(side='right')
        subtitle = FlowFrame(self.details)
        subtitle.pack(fill='x')
        self.cue_values = []
        for label, default in [(tr('editor.labels.chars_line'), subtitle_options.characters),
                (tr('editor.labels.lines'), subtitle_options.lines),
                (tr('editor.init.min_seconds'), subtitle_options.min_duration),
                (tr('editor.init.max_seconds'), subtitle_options.max_duration)]:
            ttk.Label(subtitle, text=label).pack(side='left', padx=(0, 4))
            value = tk.StringVar(value=str(default))
            ttk.Entry(subtitle, textvariable=value, width=4).pack(side='left', padx=(0, 10))
            self.cue_values.append(value)
        self.saved_cue_values = tuple(value.get() for value in self.cue_values)
        for value in self.cue_values:
            value.trace_add('write', self.subtitle_changed)
        self.window.bind('<Configure>', lambda event: self.status_label.configure(wraplength=max(200, event.width-32)) if event.widget == self.window else None)
        self.apply_theme()
        self.render()
        self.bind_keys(self.window)
        threading.Thread(target=self.load_audio, daemon=True).start()
        self.poll_timer = self.window.after(100, self.poll)

    def bind_keys(self, widget):
        # Local bindings avoid dispatch to hidden editors or unrelated tabs.
        if widget.winfo_class() in ('Frame', 'TFrame', 'Canvas', 'Label', 'TLabel'):
            # Tk otherwise treats a container with key bindings as a Tab stop.
            if str(widget.cget('takefocus')) not in ('1', 'true'):
                widget.configure(takefocus=False)
        actions = {'<Control-s>': lambda: self.save(), '<Control-f>': self.focus_search,
                   '<Control-z>': self.undo, '<Control-y>': self.redo, '<Control-Shift-Z>': self.redo,
                   '<<Undo>>': self.undo, '<<Redo>>': self.redo,
                   '<F3>': self.next_match, '<Shift-F3>': lambda: self.navigate(-1),
                   '<Alt-Up>': lambda: self.navigate(-1), '<Alt-Down>': lambda: self.navigate(1),
                   '<F6>': self.focus_text}
        for sequence, action in actions.items():
            def invoke(event, callback=action):
                callback()
                return 'break'
            widget.bind(sequence, invoke)
        for key, segment in (('<F7>', True), ('<F8>', False)):
            widget.bind(key, lambda event, part=segment: self.keyboard_playback(event, part))
        for child in widget.winfo_children():
            self.bind_keys(child)

    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, 'end')

    def focus_text(self):
        if self.current is None:
            self.navigate(1)
        else:
            self.text.focus_set()
            self.tree.reveal(self.current)

    def navigate(self, delta):
        if not self.matches:
            self.focus_search()
            return
        self.capture()
        position = (self.matches.index(self.current) + delta) % len(self.matches) if self.current in self.matches else (0 if delta > 0 else len(self.matches)-1)
        index = self.matches[position]
        if self.page != position // self.PAGE_SIZE:
            self.page = position // self.PAGE_SIZE
            self.render()
        self.tree.selection_set(str(index))
        self.select()
        self.tree.reveal(index)

    def keyboard_playback(self, event, segment=False):
        from accessibility import editing
        if editing(event.widget):
            return None
        if segment:
            self.play_segment()
        elif self.player.stream is not None:
            self.player.pause()
        else:
            self.play()
        return 'break'

    def keyboard_seek(self, delta):
        # Keyboard seek preserves pause; arrows elsewhere keep their editing role.
        running = self.player.stream is not None
        self.player.pause()
        if self.player.audio is not None:
            with self.player.lock:
                self.player.position = max(0, min(len(self.player.audio), self.player.position + round(delta * 16000)))
                self.position.set(self.player.position / 16000)
            if running:
                self.play()
        return 'break'

    def apply_theme(self):
        palette = palette_for(self.app)
        self.window.configure(bg=palette['bg'])
        if self.text.winfo_exists():
            self.text.configure(bg=palette['field'], fg=palette['text'], insertbackground=palette['text'],
                                selectbackground=palette['blue'], selectforeground=palette['accent_text'],
                                highlightbackground=palette['border'], highlightcolor=palette['blue'])
        self.tree.canvas.configure(bg=palette['bg'])
        if not self.embedded:
            from window_style import titlebar
            self.window.after_idle(lambda: titlebar(self.window, self.app.theme == 'dark', palette['bg'], palette['text']))

    def mark_dirty(self):
        self.dirty = True
        self.saved_state.set(tr('editor.mark_dirty.unsaved_changes'))
        if not self.embedded:
            self.window.title(tr('editor.mark_dirty.transcript_editor_unsaved_changes'))

    def refresh_dirty(self):
        pending = False
        if self.current is not None:
            item = self.segments[self.current]
            pending = (self.text.get('1.0', 'end-1c') != item['text'] or
                       self.speaker.get().strip() != item.get('speaker', ''))
        self.dirty = self.history.dirty or pending or tuple(v.get() for v in self.cue_values) != self.saved_cue_values
        self.saved_state.set(tr('editor.mark_dirty.unsaved_changes') if self.dirty else tr('editor.save.all_changes_saved'))
        if not self.embedded:
            self.window.title(tr('editor.mark_dirty.transcript_editor_unsaved_changes') if self.dirty else tr('editor.labels.transcript_editor_nd_transkripthor'))

    def record_changes(self, changes):
        self.track_changes(identifier for identifier, *_ in changes)
        if not self.history.record(changes):
            self.status.set(tr('editor.history_limit'))
        self.refresh_dirty()

    def track_changes(self, identifiers):
        for identifier in identifiers:
            self.edit_serial += 1
            self.pending_segments[identifier] = self.edit_serial

    def undo(self):
        self.history_step(False)

    def redo(self):
        self.history_step(True)

    def history_step(self, redo):
        self.capture()
        changes = self.history.step(redo)
        if changes is None:
            self.status.set(tr('editor.nothing_redo') if redo else tr('editor.nothing_undo'))
            return
        for identifier, fields in changes:
            self.segments[self.segment_indices[identifier]].update(fields)
            if 'speaker' in fields:
                self.speaker_revisions[identifier] = self.speaker_revisions.get(identifier, 0) + 1
        self.track_changes(identifier for identifier, _ in changes)
        target = self.segment_indices[changes[0][0]]
        # Re-evaluate the filter; keep it unless it would hide the changed segment.
        query = self.query.get().casefold()
        self.matches = [i for i, item in enumerate(self.segments) if query in item['text'].casefold()]
        if target not in self.matches:
            self.query.set('')
            self.matches = list(range(len(self.segments)))
        self.page = self.matches.index(target) // self.PAGE_SIZE
        self.render()
        self.tree.selection_set(str(target))
        # Selection is a view operation here: never autoplay on Undo/Redo.
        self.current = target
        self.loading_text = True
        try:
            self.tree.edit(target, self.segments[target]['text'])
            self.speaker.set(self.segments[target].get('speaker', ''))
        finally:
            self.loading_text = False
        self.tree.reveal(target)
        self.refresh_dirty()
        self.status.set(tr('editor.redone') if redo else tr('editor.undone'))

    def subtitle_changed(self, *_):
        # Even an incomplete number is an unsaved edit; validate only on Save.
        self.refresh_dirty()

    def modified(self, event=None):
        if self.text.edit_modified():
            if not self.loading_text:
                self.mark_dirty()
                self.status.set(tr('editor.modified.text_edited_segment_timing_is_preserved_precise_word_timing'))
            self.text.edit_modified(False)

    def speaker_changed(self, *_):
        if not self.loading_text and self.current is not None:
            identifier = self.segments[self.current]['id']
            self.speaker_revisions[identifier] = self.speaker_revisions.get(identifier, 0) + 1
            self.mark_dirty()

    def capture(self):
        if self.current is not None:
            item = self.segments[self.current]
            text = self.text.get('1.0', 'end-1c')
            before, after = {}, {}
            if text != item['text']:
                before.update(text=item['text'], words=item.get('words', []))
                after.update(text=text, words=[])
            if item.get('speaker', '') != self.speaker.get().strip():
                before['speaker'] = item.get('speaker', '')
                after['speaker'] = self.speaker.get().strip()
            if after:
                item.update(after)
                self.record_changes([(item['id'], before, after)])
            else:
                self.refresh_dirty()

    def render(self):
        self.current = None
        first = self.page * self.PAGE_SIZE
        self.tree.render(self.matches[first:first + self.PAGE_SIZE])
        self.page_label.set(tr('editor.render.segments', p0=first + 1 if self.matches else 0, p1=min(first + self.PAGE_SIZE, len(self.matches)), p2=len(self.matches)))

    def select(self, event=None):
        chosen = self.tree.selection()
        if not chosen:
            return
        self.capture()
        self.current = int(chosen[0])
        item = self.segments[self.current]
        self.loading_text = True
        self.tree.edit(self.current, item['text'])
        self.speaker.set(item.get('speaker', ''))
        self.loading_text = False
        if self.app.autoplay.get() and self.player.audio is not None:
            self.play_segment()

    def search(self):
        self.capture()
        query = self.query.get().casefold()
        self.matches = [i for i, item in enumerate(self.segments) if query in item['text'].casefold()]
        self.page = 0
        self.render()

    def next_match(self):
        self.navigate(1)

    def toggle_details(self):
        if self.details.winfo_manager():
            self.details.pack_forget()
        else:
            self.details.pack(fill='x', pady=4)

    def change_page(self, delta):
        self.capture()
        self.page = max(0, min(self.page + delta, max(0, (len(self.matches)-1)//self.PAGE_SIZE)))
        self.render()

    def load_audio(self):
        try:
            if fingerprint(self.source, self.stop) != self.digest:
                raise ValueError(tr('editor.load_audio.the_source_recording_has_changed_playback_is_disabled_you'))
            if not self.stop.is_set():
                duration = self.player.load(self.source, Path(self.folder)/'.pcm-cache')
                self.events.put(('loaded', duration))
        except Exception as exc:
            self.events.put(('error', str(exc)))

    def play(self, start=None, end=None):
        try:
            self.player.play(start, end)
        except Exception as exc:
            self.status.set(tr('editor.play.playback_unavailable', p0=exc))

    def play_segment(self):
        if self.current is not None:
            item = self.segments[self.current]
            self.play(item['start'], item['end'])

    def begin_seek(self, event=None):
        self.dragging = True
        self.player.pause()

    def seek(self, event=None):
        self.dragging = False
        self.play(self.position.get())

    def save(self):
        if self.io_busy:
            self.status.set(tr('editor.io_busy'))
            return False
        self.capture()
        try:
            chars, lines, minimum, maximum = [value.get() for value in self.cue_values]
            options = SubtitleOptions(int(chars), int(lines), float(minimum), float(maximum))
            # Only changed records cross the thread boundary. Nested word data is
            # immutable in the editor: edits replace it rather than mutate it.
            versions = dict(self.pending_segments)
            rows = [dict(self.segments[self.segment_indices[key]]) for key in versions]
            token = (self.history.state, tuple(v.get() for v in self.cue_values), versions)
            self.start_io(rows, options, token)
            return True
        except Exception as exc:
            messagebox.showerror(tr('editor.save.save'), str(exc), parent=self.window)
            return False

    def open_export(self):
        try:
            import os
            from export_pair import latest_pair
            os.startfile(str(latest_pair(Path(self.folder), '.opravene')))
        except Exception as exc:
            messagebox.showinfo(tr('editor.labels.export'), tr('editor.open_export.could_not_open_the_completed_export_pair_select_retry') + str(exc), parent=self.window)

    def retry_export(self):
        if self.io_busy:
            self.status.set(tr('editor.io_busy'))
            return False
        self.start_io()
        return True

    def start_io(self, rows=None, options=None, token=None):
        self.io_busy = True
        self.io_is_save = token is not None
        self.io_saved = self.io_success = False
        self.export_state.set(tr('editor.io_saving') if token else tr('editor.io_exporting'))
        def run():
            try:
                with Project(self.folder) as project:
                    if token is not None:
                        project.edit(rows, export_options=options)
                        self.events.put(('io_committed', token))
                    warnings = project.retry_export()
                self.events.put(('io_done', warnings))
            except Exception as exc:
                self.events.put(('io_error', str(exc)))
        # Closing is explicitly refused while this thread owns an unfinished write.
        self.io_thread = threading.Thread(target=run, daemon=False)
        self.io_thread.start()

    def complete_io(self, kind, value):
        if kind == 'io_committed':
            state, cues, versions = value
            self.history.saved = state
            self.saved_cue_values = cues
            for key, version in versions.items():
                if self.pending_segments.get(key) == version:
                    del self.pending_segments[key]
            self.io_saved = True
            self.refresh_dirty()
            self.export_state.set(tr('editor.io_exporting'))
            return
        self.io_busy = False
        self.io_success = kind == 'io_done'
        if self.io_success:
            self.export_state.set(tr('editor.retry_export.txt_srt_export_complete'))
            self.status.set(tr('editor.retry_export.the_txt_srt_pair_is_available_through_open_export') + ' '.join(value))
        elif self.io_is_save and not self.io_saved:
            self.export_state.set(tr('editor.io_failed'))
            messagebox.showerror(tr('editor.save.save'), value, parent=self.window)
        else:
            self.export_state.set(tr('editor.retry_export.export_incomplete_you_can_retry'))
            text = tr('editor.retry_export.saved_project_data_is_preserved_txt_srt_export_could') + value
            self.status.set(tr('editor.retry_export.the_project_remains_saved_retry_export_after_resolving_the'))
            messagebox.showerror(tr('editor.labels.txt_srt_export'), text, parent=self.window)

    def rename_speaker(self):
        self.capture()
        old = self.speaker.get().strip()
        if not old:
            return
        new = simpledialog.askstring(tr('editor.rename_speaker.rename_voice'), tr('editor.rename_speaker.new_name_for', p0=old), parent=self.window)
        if new and new.strip():
            changes = []
            for item in self.segments:
                if item.get('speaker') == old:
                    if old != new.strip():
                        changes.append((item['id'], {'speaker': old}, {'speaker': new.strip()}))
                    item['speaker'] = new.strip()
                    identifier = item['id']
                    self.speaker_revisions[identifier] = self.speaker_revisions.get(identifier, 0) + 1
            self.loading_text = True
            self.speaker.set(new.strip())
            self.loading_text = False
            self.record_changes(changes)
            self.render()

    def refresh_speaker_choices(self):
        self.speaker_entry.configure(values=sorted({item.get('speaker', '') for item in self.segments
                                                    if item.get('speaker')}))

    def voice_help(self):
        messagebox.showinfo(tr('voices.help_title'), tr('voices.help'), parent=self.window)
        self.refresh_voice_availability()

    def refresh_voice_availability(self):
        if self.speaker_busy or self.voice_check is not None:
            return
        token, cache, events = object(), self.app.cache, self.events
        self.voice_check = token
        self.speaker_button.configure(state='disabled')
        self.voice_status.set(tr('voices.checking'))
        def check():
            from speakers import availability
            try:
                result = availability(cache)
            except Exception as exc:
                result = (None, tr('voices.check_failed'), f'{type(exc).__name__}: {exc}')
            # Do not keep Tk/editor objects alive in the worker after closing.
            events.put(('voice_availability', (token, cache, result)))
        threading.Thread(target=check, daemon=True).start()

    def show_voice_availability(self, result):
        path, reason, detail = result
        self.voice_status.set(reason + ('\n' + detail if detail else ''))
        self.speaker_button.configure(state='normal' if path and not self.speaker_busy else 'disabled')
        return path

    def diarize(self):
        if self.app.busy or (self.app.model_dialog and self.app.model_dialog.window.winfo_exists() and self.app.model_dialog.busy):
            self.status.set(tr('editor.diarize.wait_for_transcription_or_model_operations_to_finish'))
            return
        if self.speaker_busy or self.player.audio is None:
            self.status.set(tr('editor.diarize.wait_for_audio_preparation_or_voice_grouping_to_finish'))
            return
        from speakers import availability
        path = self.show_voice_availability(availability(self.app.cache))
        if not path:
            return
        if not messagebox.askyesno(tr('editor.diarize.voice_grouping'), tr('editor.diarize.start_local_voice_grouping_this_replaces_current_assignments_it'), parent=self.window):
            return
        self.capture()
        # The worker needs only immutable identity/timing, never live editor data.
        snapshot = tuple(MappingProxyType({key: item[key] for key in ('id', 'start', 'end')})
                         for item in self.segments)
        baseline = {item['id']: (item['start'], item['end'],
                    self.speaker_revisions.get(item['id'], 0), item.get('speaker', ''))
                    for item in self.segments}
        token = object()
        self.speaker_job = (token, baseline)
        audio = self.player.audio
        self.speaker_busy = True
        self.speaker_button.configure(state='disabled')
        def run():
            try:
                from speakers import assign_speakers
                with Lease(Path(self.app.cache)/'.models.lock'):
                    result = assign_speakers(audio, snapshot, path, self.stop,
                                             lambda text: self.events.put(('status', text)))
                if len(result) != len(snapshot):
                    raise ValueError(tr('editor.run.the_number_of_voice_results_does_not_match_the'))
                self.events.put(('speakers', (token, {item['id']: speaker for item, speaker in zip(snapshot, result)})))
            except Exception as exc:
                self.events.put(('speaker_error', (token, str(exc))))
        threading.Thread(target=run, daemon=True).start()

    def apply_speakers(self, token, assignments):
        if self.speaker_job is None or self.speaker_job[0] is not token:
            return
        self.capture()
        baseline = self.speaker_job[1]
        changed = protected = 0
        changes = []
        for item in self.segments:
            identifier = item['id']
            current = (item['start'], item['end'], self.speaker_revisions.get(identifier, 0), item.get('speaker', ''))
            if identifier not in assignments or current != baseline.get(identifier):
                protected += 1
                continue
            if item.get('speaker', '') != assignments[identifier]:
                changes.append((identifier, {'speaker': item.get('speaker', '')}, {'speaker': assignments[identifier]}))
                item['speaker'] = assignments[identifier]
                changed += 1
        self.speaker_job = None
        self.speaker_busy = False
        self.refresh_voice_availability()
        if changed:
            self.dirty = True
            self.saved_state.set(tr('editor.apply_speakers.unsaved_changes'))
        if self.current is not None:
            self.loading_text = True
            try:
                self.speaker.set(self.segments[self.current].get('speaker', ''))
            finally:
                self.loading_text = False
        self.tree.refresh_speakers()
        self.record_changes(changes)
        self.status.set(tr('editor.apply_speakers.voices_assigned_review_the_results_and_save_your_changes') +
                        (tr('editor.apply_speakers.manually_edited_or_changed_segments_preserved', p0=protected) if protected else ''))

    def poll(self):
        if not self.window.winfo_exists():
            return
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind.startswith('io_'):
                self.complete_io(kind, value)
            elif kind == 'voice_availability':
                token, cache, result = value
                if token is self.voice_check:
                    self.voice_check = None
                    if cache == self.app.cache:
                        self.show_voice_availability(result)
                    else:
                        self.refresh_voice_availability()
            elif kind == 'loaded':
                self.slider.configure(to=max(1, value))
                self.status.set(tr('editor.poll.audio_ready_select_a_segment_and_press_segment'))
            elif kind == 'speakers':
                self.apply_speakers(*value)
            else:
                if kind == 'speaker_error':
                    token, value = value
                    if self.speaker_job is None or self.speaker_job[0] is not token:
                        continue
                    self.speaker_job = None
                    self.speaker_busy = False
                    self.refresh_voice_availability()
                self.status.set(value)
        if not self.dragging:
            self.position.set(self.player.position / 16000)
        self.clock.set(timestamp(self.position.get()))
        self.poll_timer = self.window.after(100, self.poll)

    def close(self):
        if self.io_busy:
            self.status.set(tr('editor.io_busy'))
            return False
        self.capture()
        if self.speaker_busy:
            self.stop.set()
            self.status.set(tr('editor.close.stopping_voice_grouping_waiting_for_the_current_segment'))
            return False
        if self.dirty:
            answer = messagebox.askyesnocancel(tr('editor.close.unsaved_changes'), tr('editor.close.save_changes_before_closing'), parent=self.window)
            if answer:
                self.save()
                return False
            if answer is None:
                return False
        self.stop.set()
        self.player.close()
        self.window.after_cancel(self.poll_timer)
        self.window.destroy()
        if self.embedded:
            self.app.editor_empty.pack(pady=24)
        return True
