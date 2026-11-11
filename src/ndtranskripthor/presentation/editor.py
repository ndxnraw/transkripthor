"""Complete transcript editor, paged presentation, local audio playback."""
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.core.app_errors import classify
from ndtranskripthor.presentation.error_dialog import show_error
from pathlib import Path
from ndtranskripthor.application.project_io import perform_project_io
from ndtranskripthor.core.contracts import Playback
import queue
import threading
from types import MappingProxyType
from ndtranskripthor.core.ownership import Lease
from ndtranskripthor.presentation.responsive import MessageView, FlowFrame, DialogPanel
from ndtranskripthor.presentation.tk_lifecycle import TkVariables
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from ndtranskripthor.projects.project import Project, fingerprint
from ndtranskripthor.audio.playback import Player, RATES, output_devices
from ndtranskripthor.exports.subtitles import SubtitleOptions, timestamp
from ndtranskripthor.presentation.theme import palette_for
from ndtranskripthor.projects.edit_history import EditHistory
from ndtranskripthor.projects.transcript_search import occurrences
from bisect import bisect_left, bisect_right


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
            self.structure_ready = project.get('complete', False)
            self.audio_duration = project.get('samples') / 16000 if project.get('samples') is not None else None
            self.next_segment_id = project.next_segment_id()
            original_available = project.original_available()
            export_request = project.get('editor_export')
            bundle_request = project.get('bundle_export')
            subtitle_options = project.subtitle_options()
            self.project_lease = Lease(Path(folder)/'.project.lock')
        self.embedded = parent is not None
        self.window = tk.Frame(parent) if self.embedded else tk.Toplevel(app.root)
        self.variables = TkVariables(self.window)
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
        self.structural_ids = set()
        self.export_request = None
        if bundle_request:
            from ndtranskripthor.exports.export_formats import ExportOptions
            self.export_request = (ExportOptions(**bundle_request['options']), bundle_request['view'], bundle_request['revision'])
        self.edit_serial = 0
        self.io_busy = False
        self.io_saved = False
        self.io_success = False
        self.segment_indices = {item['id']: index for index, item in enumerate(self.segments)}
        self.dirty = False
        self.loading_text = False
        self.page = 0
        self.matches = list(range(len(self.segments)))
        self.search_key = None
        self.hits = []
        self.active_hit = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.speaker_busy = False
        self.speaker_revisions = {}
        self.speaker_job = None
        self.voice_check = None
        self.player: Playback = Player()
        self.audio_busy = True
        outer = ttk.Frame(self.window, padding=8)
        outer.pack(fill='both', expand=True)
        heading = ttk.Frame(outer, style='Card.TFrame', padding=6)
        heading.pack(fill='x', pady=(0, 4))
        self.saved_state = self.variables.string(value=tr('editor.init.all_changes_saved'))
        self.saved_badge = ttk.Label(heading, textvariable=self.saved_state, style='Status.TLabel')
        self.saved_badge.pack(side='right', padx=(6, 0))
        self.source_suffix = '' if original_available else tr('editor.init.original_transcript_cannot_be_verified')
        self.source_name = self.variables.string(value=Path(self.source).name + self.source_suffix)
        self.audio_status = self.variables.string(value=tr('project.audio_checking'))
        self.source_info = self.variables.string()
        def update_source_info(*_):
            self.source_info.set(self.source_name.get() + ' — ' + self.audio_status.get())
        self.audio_status.trace_add('write', update_source_info)
        self.source_name.trace_add('write', update_source_info)
        update_source_info()
        self.source_label = MessageView(heading, app, textvariable=self.source_info, lines=1, surface='card')
        self.source_label.pack(side='left', fill='x', expand=True)
        toolbar = ttk.Frame(outer, style='Card.TFrame', padding=(6, 4))
        toolbar.pack(fill='x', pady=(0, 4))
        self.query = self.variables.string()
        ttk.Label(toolbar, text=tr('accessibility.search'), style='CardMuted.TLabel').pack(side='left', padx=(0, 4))
        search = ttk.Entry(toolbar, textvariable=self.query)
        self.search_entry = search
        search.pack(side='left', fill='x', expand=True)
        search.bind('<Return>', lambda _: self.search())
        ttk.Button(toolbar, width=0, padding=(8, 2), text=tr('editor.init.search'), command=self.search).pack(side='left', padx=4)
        match_button = ttk.Menubutton(toolbar, width=0, padding=(8, 2), text=tr('search.navigation'))
        self.match_menu = tk.Menu(match_button, tearoff=False)
        self.match_menu.add_command(label=tr('editor.init.next_match'), accelerator='F3', command=self.next_match)
        self.match_menu.add_command(label=tr('search.previous'), accelerator='Shift+F3', command=lambda: self.next_match(-1))
        match_button.configure(menu=self.match_menu)
        match_button.pack(side='left')
        self.save_button = ttk.Button(toolbar, width=0, padding=(8, 2), text=tr('exports.save_project'), style='Accent.TButton', command=self.save)
        self.save_button.pack(side='right', padx=(8, 0))
        # Pack fixed controls first so they remain accessible at minimum size.
        bottom = ttk.Frame(outer, style='Card.TFrame', padding=6)
        bottom.pack(side='bottom', fill='x')
        self.status = self.variables.string(value=tr('editor.init.preparing_audio_selecting_a_segment_does_not_start_playback'))
        self.status_label = MessageView(bottom, app, textvariable=self.status, lines=1, surface='card')
        self.status_label.pack(side='bottom', fill='x', pady=2)
        self.export_state = self.variables.string(value=tr('editor.init.export_has_not_been_saved_yet') if not export_request else
            (tr('editor.init.txt_srt_export_complete') if export_request['state'] == 'complete' else tr('editor.init.project_saved_export_is_pending')))
        if bundle_request:
            source = tr('exports.original') if bundle_request['view'] == 'original' else tr('exports.revision', id=bundle_request['revision'])
            self.export_state.set(source+' — '+tr('exports.done' if bundle_request['state'] == 'complete' else 'exports.incomplete'))
        export_bar = ttk.Frame(bottom, style='Card.TFrame')
        export_bar.pack(side='bottom', fill='x')
        ttk.Button(export_bar, width=0, padding=(8, 2), text=tr('editor.init.retry_export'), command=self.retry_export).pack(side='right')
        ttk.Button(export_bar, width=0, padding=(8, 2), text=tr('editor.init.open_export'), command=self.open_export).pack(side='right', padx=4)
        self.export_label = MessageView(export_bar, app, textvariable=self.export_state, lines=1, surface='card')
        self.export_label.pack(side='left', fill='x', expand=True)
        playback = FlowFrame(bottom, style='Card.TFrame')
        playback.pack(fill='x', pady=4)
        details_toggle = ttk.Menubutton(heading, width=0, padding=(8, 2), text=tr('editor.init.segment_and_subtitles'))
        self.project_menu = tk.Menu(details_toggle, tearoff=False)
        self.project_menu.add_command(label=tr('editor.init.segment_and_subtitles'), command=self.toggle_details)
        self.project_menu.add_command(label=tr('project.locate_audio'), command=self.locate_audio, state='disabled')
        self.project_menu.add_command(label=tr('project.open'), command=app.choose_project)
        self.project_menu.add_command(label=tr('playback.settings'), command=self.playback_settings)
        self.project_menu.add_command(label=tr('segments.split'), command=lambda: self.edit_structure('split'))
        self.project_menu.add_command(label=tr('segments.merge'), command=lambda: self.edit_structure('merge'))
        self.project_menu.add_command(label=tr('segments.times'), command=lambda: self.edit_structure('times'))
        self.project_menu.add_command(label=tr('exports.options'), command=self.export_dialog)
        details_toggle.configure(menu=self.project_menu)
        details_toggle.pack(side='right', padx=(4, 0))
        self.details = ttk.Frame(bottom, style='Card.TFrame')
        from ndtranskripthor.presentation.transcript_blocks import TranscriptBlocks
        self.tree = TranscriptBlocks(outer, self)
        self.tree.pack(fill='both', expand=True, pady=(8, 0))
        pages = ttk.Frame(bottom, style='Card.TFrame')
        pages.pack(fill='x')
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.init.previous_segments'), command=lambda: self.change_page(-1)).pack(side='left')
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.init.next_segments'), command=lambda: self.change_page(1)).pack(side='left', padx=5)
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.undo'), command=self.undo).pack(side='left', padx=4)
        ttk.Button(pages, width=0, padding=(8, 2), text=tr('editor.redo'), command=self.redo).pack(side='left')
        self.page_label = self.variables.string()
        MessageView(pages, app, textvariable=self.page_label, lines=1, surface='card').pack(side='right', fill='x', expand=True)
        # Replaced by an inline Text when a block is selected.
        self.text = tk.Text(self.window)
        voice = FlowFrame(self.details, style='Card.TFrame')
        voice.pack(fill='x')
        ttk.Label(voice, text=tr('editor.init.segment_speaker'), style='CardMuted.TLabel').pack(side='left')
        self.speaker = self.variables.string()
        self.speaker_entry = ttk.Combobox(voice, textvariable=self.speaker, width=12,
                                        postcommand=self.refresh_speaker_choices)
        self.speaker_entry.pack(side='left')
        self.speaker.trace_add('write', self.speaker_changed)
        ttk.Button(voice, width=0, padding=(8, 2), text=tr('editor.init.rename_voice'), command=self.rename_speaker).pack(side='left', padx=4)
        self.speaker_button = ttk.Button(voice, width=0, padding=(8, 2), text=tr('editor.init.group_similar_voices'), command=self.diarize)
        self.speaker_button.pack(side='right')
        self.speaker_button.configure(state='disabled')
        voice_info = ttk.Frame(self.details, style='Card.TFrame')
        voice_info.pack(fill='x')
        ttk.Button(voice_info, width=0, padding=(8, 2), text=tr('voices.help_title'), command=self.voice_help).pack(side='right')
        self.voice_status = self.variables.string(value=tr('voices.checking'))
        MessageView(voice_info, app, textvariable=self.voice_status, lines=1, surface='card').pack(side='left', fill='x', expand=True)
        self.details.bind('<Map>', lambda event: self.refresh_voice_availability() if event.widget == self.details else None)
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.segment'), command=self.play_segment).pack(side='left')
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.resume'), command=self.play).pack(side='left')
        ttk.Button(playback, width=0, padding=(8, 2), text=tr('editor.init.pause'), command=self.player.pause).pack(side='left')
        self.position = self.variables.double(value=0)
        self.slider = ttk.Scale(playback, variable=self.position, from_=0, to=1)
        playback.stretch = self.slider
        self.slider.pack(side='left', fill='x', expand=True, padx=8)
        self.dragging = False
        self.slider.bind('<ButtonPress-1>', self.begin_seek)
        self.slider.bind('<ButtonRelease-1>', self.seek)
        for key, delta in (('<Left>', -5), ('<Right>', 5)):
            self.slider.bind(key, lambda event, amount=delta: self.keyboard_seek(amount))
        self.clock = self.variables.string(value='00:00:00,000')
        ttk.Label(playback, textvariable=self.clock, style='CardMuted.TLabel').pack(side='right')
        subtitle = FlowFrame(self.details, style='Card.TFrame')
        subtitle.pack(fill='x')
        self.cue_values = []
        for label, default in [(tr('editor.labels.chars_line'), subtitle_options.characters),
                (tr('editor.labels.lines'), subtitle_options.lines),
                (tr('editor.init.min_seconds'), subtitle_options.min_duration),
                (tr('editor.init.max_seconds'), subtitle_options.max_duration)]:
            ttk.Label(subtitle, text=label, style='CardMuted.TLabel').pack(side='left', padx=(0, 4))
            value = self.variables.string(value=str(default))
            ttk.Entry(subtitle, textvariable=value, width=4).pack(side='left', padx=(0, 10))
            self.cue_values.append(value)
        self.saved_cue_values = tuple(value.get() for value in self.cue_values)
        for value in self.cue_values:
            value.trace_add('write', self.subtitle_changed)
        self.window.bind('<Configure>', lambda event: self.status_label.configure(wraplength=max(200, event.width-32)) if event.widget == self.window else None)
        app.theme_manager.watch(self.window, self.apply_theme)
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
                   '<F3>': self.next_match, '<Shift-F3>': lambda: self.next_match(-1),
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
        from ndtranskripthor.presentation.accessibility import editing
        if editing(event.widget):
            return None
        if segment:
            self.play_segment()
        elif self.player.playing:
            self.player.pause()
        else:
            self.play()
        return 'break'

    def keyboard_seek(self, delta):
        # Keyboard seek preserves pause; arrows elsewhere keep their editing role.
        try:
            self.player.seek(self.player.position / 16000 + delta)
            self.position.set(self.player.position / 16000)
        except Exception as exc:
            self.status.set(tr('editor.play.playback_unavailable', p0=exc))
        return 'break'

    def apply_theme(self):
        palette = palette_for(self.app)
        manager = self.app.theme_manager
        manager.style_menu(self.project_menu)
        manager.style_menu(self.match_menu)
        manager.style_widget(self.window)
        if self.text.winfo_exists():
            manager.style_text(self.text)
            self.text.tag_configure('search_match', background=palette['info'], foreground=palette['text'], underline=True)
            self.text.tag_configure('search_active', background=palette['blue'], foreground=palette['accent_text'], underline=True)
        manager.style_widget(self.tree.canvas)

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
            if '__row__' in fields:
                self.segments = [s for s in self.segments if s['id'] != identifier]
                if fields['__row__'] is not None:
                    self.segments.append(fields['__row__'])
                self.structural_ids.add(identifier)
                self.speaker_revisions[identifier] = self.speaker_revisions.get(identifier, 0) + 1
            else:
                self.segments[self.segment_indices[identifier]].update(fields)
            if 'speaker' in fields:
                self.speaker_revisions[identifier] = self.speaker_revisions.get(identifier, 0) + 1
        self.segments.sort(key=lambda s: (s['start'], s['id']))
        self.segment_indices = {s['id']: i for i, s in enumerate(self.segments)}
        self.track_changes(identifier for identifier, _ in changes)
        target = next((self.segment_indices[key] for key, _ in changes if key in self.segment_indices), 0)
        # Re-evaluate the filter; keep it unless it would hide the changed segment.
        self.refresh_search()
        if target not in self.matches:
            self.query.set('')
            self.refresh_search()
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
        self.highlight_matches()
        self.refresh_dirty()
        self.status.set(tr('editor.redone') if redo else tr('editor.undone'))

    def subtitle_changed(self, *_):
        # Even an incomplete number is an unsaved edit; validate only on Save.
        self.refresh_dirty()

    def modified(self, event=None):
        if self.text.edit_modified():
            if not self.loading_text:
                self.mark_dirty()
                if self.query.get():
                    self.text.tag_remove('search_match', '1.0', 'end')
                    self.text.tag_remove('search_active', '1.0', 'end')
                    self.page_label.set(tr('search.changed'))
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
        self.search_summary()

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
        self.highlight_matches()
        if self.app.autoplay.get() and self.player.audio is not None:
            self.play_segment()

    def search(self):
        self.capture()
        self.refresh_search()
        self.active_hit = None
        self.page = 0
        self.render()
        if self.hits:
            self.next_match()

    def refresh_search(self):
        key = (self.query.get(), self.edit_serial)
        if key == self.search_key:
            return False
        if self.search_key is None or key[0] != self.search_key[0]:
            self.active_hit = None
        self.search_key = key
        self.hits = [(i, start, end) for i, item in enumerate(self.segments)
                     for start, end in occurrences(item['text'], key[0])] if key[0] else []
        self.matches = list(dict.fromkeys(hit[0] for hit in self.hits)) if key[0] else list(range(len(self.segments)))
        return True

    def search_summary(self):
        if self.query.get():
            position = bisect_left(self.hits, self.active_hit) if self.active_hit is not None else -1
            current = position+1 if 0 <= position < len(self.hits) and self.hits[position] == self.active_hit else 0
            self.page_label.set(tr('search.count', current=current, count=len(self.hits), segments=len(self.matches)))
        else:
            first = self.page * self.PAGE_SIZE
            self.page_label.set(tr('editor.render.segments', p0=first + 1 if self.matches else 0, p1=min(first + self.PAGE_SIZE, len(self.matches)), p2=len(self.matches)))

    def highlight_matches(self):
        self.text.tag_remove('search_match', '1.0', 'end')
        self.text.tag_remove('search_active', '1.0', 'end')
        if self.current is None:
            return
        text = self.text.get('1.0', 'end-1c')
        for start, end in occurrences(text, self.query.get()):
            # Text's +Nc moves by Unicode characters, unlike Tcl string length.
            left = f'1.0+{start}c'
            right = f'1.0+{end}c'
            self.text.tag_add('search_match', left, right)
            if self.active_hit == (self.current, start, end):
                self.text.tag_add('search_active', left, right)
                self.text.mark_set('insert', left)
                self.text.see(left)
        self.text.tag_raise('search_active')

    def next_match(self, delta=1):
        if not self.query.get():
            self.navigate(delta)
            return
        self.capture()
        changed = self.refresh_search()
        if not self.hits:
            self.page = 0
            self.active_hit = None
            self.render()
            self.focus_search()
            return
        if self.active_hit is None:
            position = 0 if delta > 0 else len(self.hits)-1
        else:
            position = (bisect_right(self.hits, self.active_hit) if delta > 0 else bisect_left(self.hits, self.active_hit)-1) % len(self.hits)
        self.active_hit = self.hits[position]
        index = self.active_hit[0]
        page = self.matches.index(index) // self.PAGE_SIZE
        if changed or page != self.page:
            self.page = page
            self.render()
        self.tree.selection_set(str(index))
        # Search navigation never starts audio playback.
        self.current = index
        self.loading_text = True
        try:
            self.tree.edit(index, self.segments[index]['text'])
            self.speaker.set(self.segments[index].get('speaker', ''))
        finally:
            self.loading_text = False
        self.highlight_matches()
        self.search_summary()
        self.tree.reveal(index)

    def toggle_details(self):
        if self.details.winfo_manager():
            self.details.pack_forget()
        else:
            self.details.pack(fill='x', pady=4)

    def change_page(self, delta):
        self.capture()
        self.refresh_search()
        self.page = max(0, min(self.page + delta, max(0, (len(self.matches)-1)//self.PAGE_SIZE)))
        self.render()

    def locate_audio(self):
        if self.audio_busy or self.io_busy or self.speaker_busy:
            self.status.set(tr('project.audio_wait'))
            return
        path = filedialog.askopenfilename(parent=self.window, title=tr('project.locate_audio'))
        if not path:
            return
        self.player.pause()
        self.audio_busy = True
        self.project_menu.entryconfigure(1, state='disabled')
        self.audio_status.set(tr('project.audio_checking'))
        threading.Thread(target=self.load_audio, args=(path,), daemon=True).start()

    def load_audio(self, replacement=None):
        try:
            if replacement is not None:
                with Project(self.folder) as project:
                    source = project.relocate_audio(replacement, self.stop)
                self.source = source
                self.events.put(('audio_source', source))
            if replacement is None and fingerprint(self.source, self.stop) != self.digest:
                raise ValueError(tr('editor.load_audio.the_source_recording_has_changed_playback_is_disabled_you'))
            if not self.stop.is_set():
                duration = self.player.load(self.source, Path(self.folder)/'.pcm-cache')
                self.events.put(('loaded', duration))
        except Exception as exc:
            self.events.put(('audio_error', classify(exc, 'input')))
        finally:
            self.events.put(('audio_finished', None))

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
        self.seek_running = self.player.playing
        self.player.pause()

    def seek(self, event=None):
        self.dragging = False
        try:
            self.player.seek(self.position.get(), resume=getattr(self, 'seek_running', False))
        except Exception as exc:
            self.status.set(tr('editor.play.playback_unavailable', p0=exc))

    def playback_settings(self):
        try:
            devices = [None, *output_devices()]
        except Exception as exc:
            self.status.set(tr('editor.play.playback_unavailable', p0=exc))
            return
        if self.player.device is not None and self.player.device not in devices:
            devices.append(self.player.device)
        window = tk.Toplevel(self.window)
        window.title(tr('playback.settings'))
        window.transient(self.window.winfo_toplevel())
        panel = DialogPanel(window, tr('playback.settings'))
        body = panel.content
        ttk.Label(body, text=tr('playback.output'), style='CardMuted.TLabel').pack(anchor='w')
        output = ttk.Combobox(body, state='readonly', width=45,
            values=[tr('playback.default')]+[f'{d[1]} ({d[3]})' for d in devices[1:]])
        output.pack(fill='x', pady=4)
        output.current(devices.index(self.player.device) if self.player.device in devices else 0)
        ttk.Label(body, text=tr('playback.speed'), style='CardMuted.TLabel').pack(anchor='w')
        rate = ttk.Combobox(body, state='readonly', values=[f'{r:g}×' for r in RATES])
        rate.current(RATES.index(self.player.rate))
        rate.pack(fill='x', pady=4)
        panel.message(tr('playback.help')).pack(fill='x', pady=8)
        def apply():
            try:
                self.player.configure(RATES[rate.current()], devices[output.current()])
            except Exception as exc:
                self.status.set(tr('editor.play.playback_unavailable', p0=exc))
            window.destroy()
        ttk.Button(panel.actions, text=tr('error.close'), command=window.destroy).pack(side='left')
        ttk.Button(panel.actions, text=tr('playback.apply'), style='Accent.TButton', command=apply).pack(side='left')
        window.bind('<Escape>', lambda event: window.destroy())
        output.focus_set()
        panel.fit()

    def change_structure(self, operation, *, offset=None, seconds=None, start=None, end=None):
        from ndtranskripthor.projects.segment_edit import split, merge, validate
        if not self.structure_ready:
            raise ValueError(tr('segments.complete_required'))
        if self.io_busy or self.speaker_busy:
            raise ValueError(tr('editor.io_busy'))
        self.capture()
        if self.current is None:
            raise ValueError(tr('segments.select'))
        index = self.current
        before = self.segments[index:index+(2 if operation == 'merge' else 1)]
        if operation == 'split':
            after = split(before[0], offset, seconds, self.next_segment_id)
        elif operation == 'merge' and len(before) == 2:
            after = [merge(*before)]
        elif operation == 'times':
            after = [dict(before[0], start=start, end=end, words=[], manual_timing=True)]
        else:
            raise ValueError(tr('segments.select'))
        candidate = self.segments[:index]+after+self.segments[index+len(before):]
        validate(candidate, self.audio_duration)
        self.player.pause()
        old, new = {r['id']: r for r in before}, {r['id']: r for r in after}
        changes = [(key, {'__row__':old.get(key)}, {'__row__':new.get(key)}) for key in sorted(set(old)|set(new))]
        self.segments = candidate
        self.next_segment_id = max(self.next_segment_id, max(new)+1)
        self.segment_indices = {s['id']: i for i, s in enumerate(self.segments)}
        self.structural_ids.update(set(old)|set(new))
        self.current = None
        self.record_changes(changes)
        self.query.set('')
        self.refresh_search()
        self.page = index//self.PAGE_SIZE
        self.render()
        self.tree.selection_set(str(index))
        self.select()

    def edit_structure(self, operation):
        try:
            if self.current is None:
                raise ValueError(tr('segments.select'))
            self.capture()
            row = self.segments[self.current]
            values = {}
            if operation == 'split':
                values['offset'] = len(self.text.get('1.0', 'insert'))
                values['seconds'] = simpledialog.askfloat(tr('segments.split'), tr('segments.split_time'), parent=self.window)
                if values['seconds'] is None:
                    return
            elif operation == 'times':
                for key in ('start', 'end'):
                    values[key] = simpledialog.askfloat(tr('segments.times'), tr('segments.'+key),
                        initialvalue=row[key], parent=self.window)
                    if values[key] is None:
                        return
            self.change_structure(operation, **values)
        except Exception as exc:
            messagebox.showerror(tr('segments.title'), str(exc), parent=self.window)

    def export_dialog(self):
        if self.io_busy:
            return
        self.capture()
        if self.dirty:
            self.status.set(tr('exports.save_first'))
            return
        from ndtranskripthor.exports.export_formats import FORMATS, ExportOptions
        with Project(self.folder) as project:
            sources = [('revision', identifier) for identifier in project.revision_ids()]
            if project.original_available():
                sources.append(('original', None))
        if not sources:
            self.status.set(tr('exports.save_first'))
            return
        window = tk.Toplevel(self.window)
        window.title(tr('exports.options'))
        window.transient(self.window.winfo_toplevel())
        panel = DialogPanel(window, tr('exports.options'))
        variables = TkVariables(window)
        body = panel.content
        ttk.Label(body, text=tr('exports.source'), style='CardMuted.TLabel').pack(anchor='w')
        source = ttk.Combobox(body, state='readonly', values=[tr('exports.original') if v == 'original' else tr('exports.revision', id=r) for v,r in sources])
        source.current(0); source.pack(fill='x')
        selected = {f:variables.boolean(value=f in ('txt','srt')) for f in FORMATS}
        for format, variable in selected.items():
            ttk.Checkbutton(body, text=format.upper(), variable=variable).pack(anchor='w')
        times, speakers = variables.boolean(value=False), variables.boolean(value=False)
        ttk.Checkbutton(body, text=tr('exports.times'), variable=times).pack(anchor='w')
        ttk.Checkbutton(body, text=tr('exports.speakers'), variable=speakers).pack(anchor='w')
        ttk.Label(body, text=tr('exports.help'), style='CardMuted.TLabel', wraplength=360).pack(fill='x', pady=8)
        def run():
            try:
                options = ExportOptions(tuple(f for f,v in selected.items() if v.get()), times.get(), speakers.get())
                view, revision = sources[source.current()]
                self.export_request = (options, view, revision)
                self.start_io()
                window.destroy()
            except Exception as exc:
                messagebox.showerror(tr('exports.options'), str(exc), parent=window)
        ttk.Button(panel.actions, text=tr('error.close'), command=window.destroy).pack(side='left')
        ttk.Button(panel.actions, text=tr('exports.run'), style='Accent.TButton', command=run).pack(side='left')
        window.bind('<Escape>', lambda event: window.destroy())
        source.focus_set()
        panel.fit()

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
            rows = [dict(self.segments[self.segment_indices[key]]) if key in self.segment_indices
                    else dict(id=key, deleted=True) for key in versions]
            token = (self.history.state, tuple(v.get() for v in self.cue_values), versions)
            self.start_io(rows, options, token)
            return True
        except Exception as exc:
            messagebox.showerror(tr('editor.save.save'), str(exc), parent=self.window)
            return False

    def open_export(self):
        try:
            import os
            from ndtranskripthor.exports.export_pair import latest_pair
            from ndtranskripthor.exports.export_formats import latest_bundle
            folder = Path(self.folder)
            bundle, legacy = folder/'exporty'/'aktualny-balik.json', folder/'exporty'/'aktualny.opravene.json'
            location = latest_bundle(folder) if bundle.exists() and (not legacy.exists() or bundle.stat().st_mtime_ns >= legacy.stat().st_mtime_ns) else latest_pair(folder, '.opravene')
            os.startfile(str(location))
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
        structural = bool(self.structural_ids)
        request = self.export_request
        # The service owns its database connection and returns data-only events.
        # Closing remains refused while this non-daemon worker owns a write.
        self.io_thread = threading.Thread(target=perform_project_io, args=(self.folder, self.events),
            kwargs=dict(rows=rows, options=options, token=token, structural=structural, request=request), daemon=False)
        self.io_thread.start()

    def complete_io(self, kind, value):
        if kind == 'io_committed':
            state, cues, versions = value
            self.history.saved = state
            self.saved_cue_values = cues
            for key, version in versions.items():
                if self.pending_segments.get(key) == version:
                    del self.pending_segments[key]
                    self.structural_ids.discard(key)
            self.io_saved = True
            self.refresh_dirty()
            self.export_state.set(tr('exports.saved_only'))
            return
        self.io_busy = False
        self.io_success = kind == 'io_done'
        if self.io_success:
            self.export_state.set(tr('exports.saved_only') if self.io_is_save else tr('exports.done'))
            self.status.set(tr('exports.saved_only') if self.io_is_save else tr('exports.done')+' '+' '.join(value))
        elif self.io_is_save and not self.io_saved:
            self.export_state.set(tr('editor.io_failed'))
            show_error(self.window, tr('editor.save.save'), value)
        else:
            self.export_state.set(tr('editor.retry_export.export_incomplete_you_can_retry'))
            self.status.set(tr('editor.retry_export.the_project_remains_saved_retry_export_after_resolving_the'))
            show_error(self.window, tr('editor.labels.txt_srt_export'), value)

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
            from ndtranskripthor.asr.speakers import availability
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
        from ndtranskripthor.asr.speakers import availability
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
                from ndtranskripthor.asr.speakers import assign_speakers
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
            elif kind == 'audio_source':
                self.source_name.set(Path(value).name + self.source_suffix)
            elif kind == 'audio_finished':
                self.audio_busy = False
                self.project_menu.entryconfigure(1, state='normal')
            elif kind == 'audio_error':
                self.audio_status.set(tr('project.audio_unavailable') if self.player.audio is None else tr('project.audio_rejected'))
                show_error(self.window, tr('project.locate_audio'), value)
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
                self.audio_status.set(tr('project.audio_ready'))
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
        error = self.player.poll_error()
        if error:
            self.status.set(tr('editor.play.playback_unavailable', p0=error))
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
