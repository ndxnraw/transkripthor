from i18n import tr
from app_errors import classify, explanation, show_error
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from model_catalog import inventory, download, remove_model, verify_model
from responsive import MessageView, FlowFrame


class ModelDialog:
    def __init__(self, app, parent=None):
        self.app = app
        self.embedded = parent is not None
        self.window = tk.Frame(parent) if self.embedded else tk.Toplevel(app.root)
        if self.embedded:
            self.window.pack(fill='both', expand=True)
        else:
            self.window.title(tr('model_dialog.init.model_manager'))
            self.window.transient(app.root)
            self.window.protocol('WM_DELETE_WINDOW', self.close)
        scale = max(1,app.root.winfo_fpixels('1i')/96)
        if not self.embedded:
            self.window.geometry(f'{min(round(1000*scale),app.root.winfo_screenwidth()-40)}x{min(round(450*scale),app.root.winfo_screenheight()-80)}+20+20')
        from ui import palette_for
        from window_style import titlebar
        palette = palette_for(app)
        self.window.configure(bg=palette['bg'])
        if not self.embedded:
            self.window.after_idle(lambda: titlebar(self.window,app.theme=='dark',palette['bg'],palette['text']))
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.refresh_pending = False
        actions = FlowFrame(self.window)
        actions.pack(side='bottom', fill='x', padx=12, pady=6)
        ttk.Label(self.window, text=tr('model_dialog.init.models_on_this_computer'), style='Title.TLabel').pack(anchor='w', padx=12, pady=12)
        self.tree = ttk.Treeview(self.window, columns=('state', 'size'), height=9)
        self.tree.heading('#0', text=tr('model_dialog.init.model'))
        for key, text in [('state', tr('model_dialog.init.local_availability')), ('size', tr('model_dialog.labels.size'))]:
            self.tree.heading(key, text=text)
        self.tree.column('#0', width=round(400*scale))
        self.tree.column('state', width=round(150*scale), stretch=False)
        self.tree.column('size', width=round(100*scale), stretch=False)
        self.tree.pack(fill='both', expand=True, padx=12, pady=12)
        self.description = tk.StringVar(value=tr('model_dialog.init.select_a_model_normal_transcription_does_not_require_a'))
        self.description_label = MessageView(self.window, app, textvariable=self.description, lines=2)
        self.description_label.pack(fill='x', padx=12, pady=8)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        self.buttons = []
        for label, command in [(tr('model_dialog.init.download'), self.download), (tr('integrity.verify'), self.verify), (tr('model_dialog.init.remove'), self.remove), (tr('model_dialog.init.refresh'), self.refresh), (tr('pcm.release_model'), self.release_model)]:
            button = ttk.Button(actions, text=label, command=command)
            button.pack(side='left', padx=4)
            self.buttons.append(button)
        ttk.Button(actions, text=tr('model_dialog.init.stop_download'), command=self.stop.set).pack(side='right')
        self.progress = ttk.Progressbar(self.window, mode='indeterminate')
        self.progress.pack(fill='x', padx=12, pady=(8, 0))
        self.status = tk.StringVar(value=tr('model_dialog.init.reading_local_cache'))
        MessageView(self.window, app, textvariable=self.status, lines=3).pack(fill='x', padx=12, pady=6)
        self.refresh()
        self.poll_timer = self.window.after(100, self.poll)

    def select(self, _event=None):
        from model_catalog import DESCRIPTIONS, SPEAKER_MODEL
        selected = self.tree.selection()
        key = selected[0] if selected else ''
        self.description.set(tr(DESCRIPTIONS[key]) if key in DESCRIPTIONS else tr('model_dialog.select.select_a_specific_model'))
        if key == SPEAKER_MODEL:
            self.description.set(self.description.get() + tr('model_dialog.select.optional_does_not_identify_people_cc_by_no_token'))

    def in_use(self):
        return self.app.busy or any(e.window.winfo_exists() and e.speaker_busy for e in self.app.editors)

    def run(self, action):
        if self.busy or self.in_use():
            self.status.set(tr('model_dialog.run.wait_for_transcription_or_voice_grouping_to_finish'))
            return
        self.busy = True
        self.stop.clear()
        for button in self.buttons:
            button.configure(state='disabled')
        cache = self.app.cache
        def worker():
            error = None
            try:
                action()
            except InterruptedError as exc:
                self.events.put(('status', str(exc)))
            except Exception as exc:
                error = classify(exc, 'model')
            finally:
                try:
                    self.events.put(('rows', (cache, inventory(cache))))
                except Exception as exc:
                    error = error or classify(exc, 'model')
                if error:
                    self.events.put(('issue', error))
                self.events.put(('done', None))
        threading.Thread(target=worker, daemon=True).start()

    def refresh(self):
        if self.busy or self.in_use():
            self.refresh_pending = True
            return
        self.refresh_pending = False
        self.run(lambda: self.events.put(('status', tr('model_dialog.poll.local_availability_checked_downloading_does_not_send_recordings_or'))))

    def verify(self):
        selected = self.tree.selection()
        if not selected or selected[0].startswith('group:'):
            return
        cache, offline = self.app.cache, self.app.offline.get()
        self.run(lambda: verify_model(cache, selected[0], offline,
                                     lambda kind, value: self.events.put((kind, value)), self.stop))

    def release_model(self):
        def release():
            self.app.model = None
            self.app.models.close()
            self.events.put(('released', None))
        self.run(release)

    def download(self):
        selected = self.tree.selection()
        if not selected or selected[0].startswith('group:'):
            return
        if self.app.offline.get():
            messagebox.showinfo(tr('model_dialog.labels.offline_only'), tr('model_dialog.labels.turn_off_offline_only_in_settings_to_download_a'), parent=self.window)
            return
        self.run(lambda: download(self.app.cache, selected[0],
                                 lambda kind, value: self.events.put((kind, value)), self.stop))

    def remove(self):
        if self.busy or self.in_use():
            self.status.set(tr('model_dialog.remove.the_model_is_in_use_stop_processing_first'))
            return
        selected = self.tree.selection()
        if selected and not selected[0].startswith('group:') and messagebox.askyesno(tr('model_dialog.remove.remove_model'), tr('model_dialog.remove.remove_local_files_for_model_recordings_and_transcripts_will', p0=selected[0]), parent=self.window):
            self.app.models.close()
            self.app.model = None
            self.run(lambda: remove_model(self.app.cache, selected[0]))

    def poll(self):
        if not self.window.winfo_exists():
            return
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == 'released':
                self.app.device_status.set(tr('pcm.model_released'))
                self.status.set(tr('pcm.model_released'))
                continue
            if kind == 'issue':
                self.status.set(explanation(value))
                show_error(self.window, tr('error.details'), value)
                continue
            if kind == 'download_state':
                self.progress.stop()
                if value:
                    self.progress.start(20)
            elif kind == 'rows':
                cache, value = value
                if cache != self.app.cache:
                    self.refresh_pending = True
                    continue
                self.refresh_pending = False
                selection, focus = self.tree.selection(), self.tree.focus()
                y, x = self.tree.yview()[0], self.tree.xview()[0]
                opened = {key: self.tree.item(key, 'open') for key in self.tree.get_children()}
                self.tree.delete(*self.tree.get_children())
                from model_catalog import SPEAKER_MODEL
                from prepis import MODELS
                names = {value: tr('model.'+value) for value in MODELS.values()}
                self.tree.insert('', 'end', iid='group:asr', text=tr('model_dialog.poll.speech_transcription'), open=True)
                self.tree.insert('', 'end', iid='group:speakers', text=tr('model_dialog.poll.optional_voice_grouping'), open=True)
                for row in value:
                    self.tree.insert('group:speakers' if row['model'] == SPEAKER_MODEL else 'group:asr', 'end', iid=row['model'], text=names.get(row['model'], 'WeSpeaker'), values=(
                        tr('integrity.state.' + row['state']), f'{row["size"]/1024**2:.1f} MB'))
                for key, is_open in opened.items():
                    if self.tree.exists(key): self.tree.item(key, open=is_open)
                self.tree.selection_set([key for key in selection if self.tree.exists(key)])
                if self.tree.exists(focus): self.tree.focus(focus)
                self.tree.yview_moveto(y)
                self.tree.xview_moveto(x)
                self.select()
            elif kind == 'done':
                self.progress.stop()
                self.busy = False
                for button in self.buttons:
                    button.configure(state='normal')
                self.app.update_readiness()
                if self.refresh_pending and not self.in_use():
                    self.refresh()
            else:
                self.status.set(value)
        if self.refresh_pending and not self.busy and not self.in_use():
            self.refresh()
        self.poll_timer = self.window.after(100, self.poll)

    def close(self):
        if self.busy:
            self.stop.set()
            self.status.set(tr('model_dialog.close.stopping_after_the_current_transfer_please_wait'))
            return
        self.window.after_cancel(self.poll_timer)
        self.window.destroy()
