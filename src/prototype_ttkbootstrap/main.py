"""Runnable UI sample; never opens user profiles, projects or ASR models."""
import argparse
import json
from pathlib import Path
import queue
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog
from types import SimpleNamespace

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ndtranskripthor.core.i18n import Translator, set_language
from ndtranskripthor.core.resources import resource_path
from ndtranskripthor.presentation.accessibility import text_navigation, high_contrast_palette
from ndtranskripthor.presentation.dpi import enable_high_dpi
from ndtranskripthor.presentation.file_drop import create_root, FileDrop, path_key
from ndtranskripthor.presentation.window_style import titlebar
from version import DISPLAY_VERSION


class SampleWindow:
    """Exercise real widgets and existing COPY-only drop intake, in temporary storage."""

    def __init__(self, root, folder, language='sk'):
        self.root = root
        self.tr = Translator(language)
        self.language = language
        self.events = queue.Queue()
        self.store = SimpleNamespace(folder=Path(folder))
        self.busy = False
        self.files = []
        self.errors = []
        original_report = root.report_callback_exception
        def report_error(kind, value, tb):
            self.errors.append(f'{kind.__name__}: {value}')
            original_report(kind, value, tb)
        root.report_callback_exception = report_error
        self.style = ttk.Style(theme='bootstrap-dark')
        # TkinterDnD owns the root, so ttk.App.destroy() never runs. Mirror its
        # 2.2.7 lifecycle cleanup when this root dies; child windows must not reset it.
        root.bind('<Destroy>', self.release_style, add='+')
        self.style.configure('.', font=('Segoe UI', 10))
        root.title('ND TranskripThor — ttkbootstrap')
        root.geometry('1080x740')
        root.minsize(800, 600)
        self.theme = 'dark'
        self.status = tk.StringVar(root)
        self.drop_hint = tk.StringVar(root)
        self.ui = lambda sk, en: sk if language == 'sk' else en

        header = ttk.Frame(root, padding=16)
        header.pack(fill='x')
        with Image.open(resource_path('assets/transkripthor.png')) as image:
            self.logo = ImageTk.PhotoImage(image.resize((40, 40)), master=root)
            self.icon = ImageTk.PhotoImage(image.resize((256, 256)), master=root)
        root.iconphoto(True, self.icon)
        self.logo_label = tk.Label(header, image=self.logo, bd=0)
        self.logo_label.pack(side='left', padx=(0, 12))
        ttk.Label(header, text='ND TranskripThor', font=('Segoe UI', 19, 'bold')).pack(side='left')
        self.theme_button = ttk.Button(header, command=self.toggle_theme)
        self.theme_button.pack(side='right')
        ttk.Label(root, text=self.ui('Ukážka nového rozhrania · bez prepisovania a ukladania projektov',
                                    'Interface preview · transcription and project saving are unavailable'),
                  padding=(16, 0, 16, 10)).pack(fill='x')
        ttk.Label(root, text=f'{DISPLAY_VERSION} · ttkbootstrap 2.2.7', padding=10).pack(side='bottom', fill='x')
        self.tabs = ttk.Notebook(root)
        self.tabs.enable_traversal()
        self.tabs.pack(fill='both', expand=True, padx=16)
        self.pages = {}
        for key, label in (('recordings', 'ui_layout.build_ui.recordings'),
                           ('editor', 'ui_layout.labels.editor'), ('models', 'ui_layout.labels.models'),
                           ('settings', 'ui_layout.labels.settings'), ('details', 'ui_layout.labels.processing_details')):
            page = ttk.Frame(self.tabs, padding=12)
            self.pages[key] = page
            self.tabs.add(page, text=self.tr(label))
        page = self.pages['recordings']
        actions = ttk.Frame(page)
        actions.pack(fill='x', pady=(0, 12))
        self.add_button = ttk.Button(actions, text=self.tr('ui_layout.build_ui.add_recordings'),
                                     command=self.choose_files, bootstyle='primary outline')
        self.add_button.pack(side='left')
        ttk.Button(actions, text=self.ui('Otvoriť skúšobné okno', 'Open sample window'),
                   command=self.open_dialog).pack(side='right')
        self.file_area = ttk.Frame(page, padding=12)
        self.file_area.pack(fill='both', expand=True)
        ttk.Label(self.file_area, textvariable=self.drop_hint, wraplength=680).pack(fill='x', pady=(0, 8))
        self.tree = ttk.Treeview(self.file_area, columns=('file', 'state'), show='headings', height=6)
        self.tree.heading('file', text=self.tr('ui_layout.init.recording'))
        self.tree.heading('state', text=self.tr('ui_layout.init.status'))
        self.tree.column('file', width=560, minwidth=180)
        self.tree.column('state', width=150, minwidth=100, stretch=False)
        scroll = ttk.Scrollbar(self.file_area, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.status_label = ttk.Label(page, textvariable=self.status, wraplength=680)
        self.progress = ttk.Progressbar(page, value=0, bootstyle='primary')
        self.start_button = ttk.Button(page, text=self.ui('Spustiť prepis — nedostupné v ukážke',
                                      'Start transcription — unavailable in preview'), bootstyle='primary', state='disabled')
        # Reserve controls before the flexible list, including large fonts/DPI.
        self.start_button.pack(side='bottom', anchor='e', before=self.file_area)
        self.progress.pack(side='bottom', fill='x', pady=8, before=self.file_area)
        self.status_label.pack(side='bottom', fill='x', pady=8, before=self.file_area)

        self.text = tk.Text(self.pages['editor'], wrap='word', undo=True, font=('Segoe UI', 11), height=10)
        self.text.pack(fill='both', expand=True)
        self.text.insert('1.0', self.ui('Skúšobný text: ľščťžýáíé. Úpravy zostávajú iba v tomto okne.',
                                      'Sample text: ľščťžýáíé. Edits stay in this window only.'))
        text_navigation(self.text)
        settings = self.pages['settings']
        ttk.Label(settings, text=self.tr('ui_layout.build_ui.audio_language')).pack(anchor='w')
        self.choice = ttk.Combobox(settings, values=('Slovenčina', 'English'), state='readonly')
        self.choice.current(0 if language == 'sk' else 1)
        self.choice.pack(anchor='w', pady=8)
        self.offline = tk.BooleanVar(root, value=True)
        ttk.Checkbutton(settings, text=self.ui('Offline režim (ukážka)', 'Offline mode (preview)'),
                        variable=self.offline, bootstyle='round toggle').pack(anchor='w', pady=8)
        ttk.Label(self.pages['models'], text=self.ui('Ukážka nenačítava ani nesťahuje modely.',
                  'The preview does not load or download models.')).pack(anchor='w')
        ttk.Label(self.pages['details'], text=self.ui('Pridané súbory sa neprepisujú ani nekopírujú.',
                  'Added files are neither transcribed nor copied.')).pack(anchor='w')
        self.dialogs = []
        self.drop = FileDrop(self)
        self.set_theme('dark')
        self.update_status()

    def update_status(self):
        self.status.set(self.ui(f'Pridané nahrávky: {len(self.files)} · údaje sa neukladajú',
                                f'Added recordings: {len(self.files)} · data is not saved'))

    def release_style(self, event):
        if event.widget is self.root and ttk.Style.get_instance() is self.style:
            ttk.Style.instance = None
            ttk.Fonts.reset()

    def accept_files(self, paths):
        accepted = 0
        known = {path_key(path) for path in self.files}
        for raw in paths:
            path = Path(raw).resolve()
            if not path.is_file() or path.suffix.lower() not in ('.wav', '.mp3', '.m4a', '.flac', '.ogg', '.mp4', '.wma', '.aac'):
                continue
            key = path_key(path)
            if key in known:
                continue
            known.add(key)
            self.files.append(path)
            self.tree.insert('', 'end', values=(path.name, self.ui('Pridané do ukážky', 'Added to preview')))
            accepted += 1
        self.update_status()
        return accepted

    def choose_files(self):
        paths = filedialog.askopenfilenames(parent=self.root, title=self.tr('ui_layout.build_ui.add_recordings'))
        self.accept_files(paths)

    def set_theme(self, mode):
        self.style.theme_use('bootstrap-' + mode)
        self.theme = mode
        colors = self.style.colors
        self.root.configure(bg=colors.bg)
        self.logo_label.configure(bg=colors.bg)
        self.text.configure(bg=colors.inputbg, fg=colors.inputfg, insertbackground=colors.inputfg,
                            selectbackground=colors.selectbg, selectforeground=colors.selectfg)
        self.theme_button.configure(text=self.ui('Svetlý režim', 'Light mode') if mode == 'dark'
                                    else self.ui('Tmavý režim', 'Dark mode'))
        self.root.after_idle(lambda: titlebar(self.root, self.theme == 'dark', self.style.colors.bg, self.style.colors.fg))
        for window in self.dialogs:
            if window.winfo_exists():
                window.configure(bg=colors.bg)
                titlebar(window, mode == 'dark', colors.bg, colors.fg)

    def toggle_theme(self):
        self.set_theme('light' if self.theme == 'dark' else 'dark')

    def open_dialog(self):
        window = tk.Toplevel(self.root)
        window.title(self.ui('Skúšobné okno', 'Sample window'))
        window.transient(self.root)
        ttk.Label(window, text=self.ui('Vedľajšie okno používa spoločnú tému.',
                  'This window shares the application theme.'), padding=24).pack()
        ttk.Button(window, text=self.ui('Zavrieť', 'Close'), command=window.destroy).pack(pady=(0, 16))
        self.dialogs.append(window)
        self.set_theme(self.theme)
        return window


def smoke(output):
    """Exercise real Tcl widgets; no model/GPU or physical desktop-DPI claim."""
    from types import SimpleNamespace
    from importlib.metadata import version
    checks = []
    with tempfile.TemporaryDirectory(prefix='Thor ttk č ') as folder:
        for cycle in range(3):
            root = create_root()
            try:
                language = 'en' if cycle == 1 else 'sk'
                set_language(language)
                app = SampleWindow(root, folder, language)
                root.update()
                assert app.drop.targets, getattr(root, 'dnd_failure', app.drop_hint.get())
                audio = Path(folder)/'Nahrávka s medzerou 日本.wav'
                audio.write_bytes(b'UI fixture, not real audio')
                event = SimpleNamespace(widget=app.tree, data=root.tk.call('list', str(audio)))
                # tk.call returns a tuple with wantobjects; Drop supplies a Tcl string.
                event.data = root.tk.call('format', '%s', event.data)
                assert app.drop.drop(event) == app.drop.copy
                assert len(app.files) == 1
                assert app.drop.drop(event) == app.drop.refuse
                app.busy = True
                assert app.drop.enter(event) == app.drop.refuse
                app.busy = False
                app.tree.selection_set(app.tree.get_children()[0])
                app.text.insert('end', '\nTest úprav 日本')
                text = app.text.get('1.0', 'end-1c')
                window = app.open_dialog()
                for scale in (1, 1.25, 1.5, 1.75, 2):
                    root.tk.call('tk', 'scaling', 96 / 72 * scale)
                    for mode in ('light', 'dark'):
                        app.set_theme(mode)
                        root.update()
                        assert app.text.get('1.0', 'end-1c') == text
                        assert app.tree.selection()
                        assert app.choice.get() == ('Slovenčina' if language == 'sk' else 'English')
                        assert app.offline.get()
                        assert window.winfo_exists()
                        assert app.start_button.winfo_ismapped(), (cycle, scale, mode, app.tabs.select(), root.state(), app.pages['recordings'].winfo_geometry())
                        assert app.start_button.winfo_y() + app.start_button.winfo_height() <= app.pages['recordings'].winfo_height()
                        app.tabs.select(app.pages['editor'])
                        root.update()
                        app.text.focus_force()
                        root.update()
                        assert root.focus_get() is app.text
                        app.tabs.select(app.pages['recordings'])
                assert ttk.Style.get_instance() is app.style
                window.destroy()
                assert ttk.Style.get_instance() is app.style
                assert not app.errors, app.errors
                checks.append({'cycle': cycle, 'tkdnd': root.tk.call('package', 'present', 'tkdnd'),
                               'drop_targets': len(app.drop.targets)})
            finally:
                root.update()
                root.destroy()
    report = {'status': 'PASS', 'ttkbootstrap': version('ttkbootstrap'), 'cycles': checks,
              'scales': [100, 125, 150, 175, 200], 'high_contrast_active': bool(high_contrast_palette()),
              'scope': 'Real Tk widgets and Tcl drop handler; not physical Explorer drag or system DPI/ASR/GPU'}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-output', type=Path)
    parser.add_argument('--language', choices=('sk', 'en'), default='sk')
    args = parser.parse_args()
    enable_high_dpi()
    set_language(args.language)
    if args.smoke_output:
        smoke(args.smoke_output)
        return
    with tempfile.TemporaryDirectory(prefix='Thor ttk preview ') as folder:
        root = create_root()
        try:
            SampleWindow(root, folder, args.language)
            root.mainloop()
        finally:
            if tk._default_root is root:
                root.destroy()


if __name__ == '__main__':
    main()
