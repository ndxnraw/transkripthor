"""Local data overview and explicit preview-before-save diagnostics."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.core.app_errors import classify
from ndtranskripthor.presentation.error_dialog import show_error
from ndtranskripthor.presentation.responsive import FlowFrame
from ndtranskripthor.presentation.accessibility import text_navigation
from ndtranskripthor.presentation.ui import palette_for
from ndtranskripthor.application.local_data import inventory, diagnostic_snapshot, save_bundle, NOTICE


class DataDialog:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title(tr('data.title'))
        self.window.transient(app.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.geometry(f'{min(900, app.root.winfo_screenwidth()-60)}x{min(650, app.root.winfo_screenheight()-80)}')
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.saving = False
        self.snapshot = None
        self.rows = []
        actions = FlowFrame(self.window)
        actions.pack(side='bottom', fill='x', padx=12, pady=8)
        self.refresh_button = ttk.Button(actions, text=tr('data.refresh'), command=self.refresh)
        self.refresh_button.pack(side='left', padx=4)
        self.preview_button = ttk.Button(actions, text=tr('data.preview'), command=self.preview, state='disabled')
        self.preview_button.pack(side='left', padx=4)
        self.save_button = ttk.Button(actions, text=tr('data.save'), command=self.save, state='disabled')
        self.save_button.pack(side='left', padx=4)
        ttk.Button(actions, text=tr('error.close'), command=self.close).pack(side='left', padx=4)
        self.status = tk.StringVar()
        ttk.Label(self.window, textvariable=self.status, wraplength=600).pack(side='bottom', fill='x', padx=12)
        self.tabs = ttk.Notebook(self.window)
        self.tabs.pack(fill='both', expand=True, padx=12, pady=12)
        self.tabs.enable_traversal()
        self.overview = self.text_page(tr('data.overview'))
        self.preview_text = self.text_page(tr('data.preview'))
        self.window.bind('<Escape>', lambda event: self.close())
        self.refresh()
        self.timer = self.window.after(100, self.poll)

    def text_page(self, label):
        panel = ttk.Frame(self.tabs)
        self.tabs.add(panel, text=label)
        text = tk.Text(panel, wrap='word', width=1, height=1, padx=12, pady=12, font=(self.app.font, 11))
        scroll = ttk.Scrollbar(panel, command=text.yview)
        scroll.pack(side='right', fill='y')
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill='both', expand=True)
        text_navigation(text)
        return text

    def display(self, widget, value):
        colors = palette_for(self.app)
        widget.configure(state='normal', bg=colors['field'], fg=colors['text'], insertbackground=colors['text'],
                         selectbackground=colors['blue'], selectforeground=colors['accent_text'])
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.configure(state='disabled')

    def refresh(self):
        self.snapshot = None
        self.save_button.configure(state='disabled')
        self.preview_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.status.set(tr('data.scanning'))
        self.display(self.overview, tr('data.policy'))
        self.display(self.preview_text, tr('data.preview_hint'))
        # Snapshot only plain inputs on Tk's thread; workers never touch widgets.
        projects = [item['project'] for item in self.app.items if item.get('project')]
        projects.extend(str(editor.folder) for editor in self.app.editors if editor.window.winfo_exists())
        args = (self.app.store.folder, self.app.cache, self.app.output.get(), projects, self.stop)
        states = [item.get('state') for item in self.app.items]
        offline = self.app.offline.get()
        def run():
            try:
                rows = inventory(*args)
                self.events.put(('inventory', (rows, diagnostic_snapshot(rows, states, offline))))
            except Exception as exc:
                self.events.put(('error', classify(exc, 'disk')))
        threading.Thread(target=run, daemon=True).start()

    def preview(self):
        if not self.snapshot:
            return
        # The entire contents of both ZIP members, not an abbreviated summary.
        self.display(self.preview_text, tr('data.preview_hint')+'\n\nREADME.txt\n'+NOTICE+'\ndiagnostics.json\n'+self.snapshot)
        self.tabs.select(1)
        self.save_button.configure(state='normal')
        self.preview_text.focus_set()

    def save(self):
        if self.saving or not self.snapshot or str(self.save_button['state']) == 'disabled':
            return
        destination = filedialog.asksaveasfilename(parent=self.window, title=tr('data.save'),
            defaultextension='.zip', initialfile='ND-TranskripThor-diagnostics.zip', filetypes=[('ZIP', '*.zip')])
        if not destination:
            return
        snapshot = self.snapshot
        self.saving = True
        self.status.set(tr('data.saving'))
        for button in (self.save_button, self.refresh_button, self.preview_button):
            button.configure(state='disabled')
        def run():
            try:
                save_bundle(destination, snapshot)
                self.events.put(('saved', None))
            except Exception as exc:
                self.events.put(('error', classify(exc, 'disk')))
        threading.Thread(target=run, daemon=False).start()

    def poll(self):
        if not self.window.winfo_exists():
            return
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            self.refresh_button.configure(state='normal')
            if kind == 'inventory':
                self.rows, self.snapshot = value
                lines = [tr('data.policy'), tr('data.sizes')]
                for row in self.rows:
                    lines.append(tr('data.row', kind=tr('data.kind.'+row['kind']), path=row['path'],
                        size=f"{row['bytes']/1024**2:.2f}", state=tr('data.state.'+row['state'])))
                self.display(self.overview, '\n\n'.join(lines))
                self.preview_button.configure(state='normal')
                self.status.set(tr('data.ready'))
            elif kind == 'saved':
                self.saving = False
                self.preview_button.configure(state='normal')
                self.save_button.configure(state='normal')
                self.status.set(tr('data.saved'))
            else:
                self.saving = False
                self.status.set(tr('data.failed'))
                if self.snapshot:
                    self.preview_button.configure(state='normal')
                show_error(self.window, tr('data.title'), value)
        self.timer = self.window.after(100, self.poll)

    def close(self):
        if self.saving:
            self.status.set(tr('data.saving'))
            return
        self.stop.set()
        self.window.after_cancel(self.timer)
        self.window.destroy()
