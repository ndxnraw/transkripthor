"""Compact Studio presentation; transcription remains in the existing worker."""
from i18n import tr
from i18n import choice_box, LANGUAGES as UI_LANGUAGES
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from responsive import MessageView, FlowFrame


class RecordingList(ttk.Treeview):
    """Structured queue with the index selection contract used by App."""
    def __init__(self, parent, scale):
        super().__init__(parent, columns=('name', 'state'), show='headings', height=3, selectmode='extended')
        self.heading('name', text=tr('ui_layout.init.recording'))
        self.heading('state', text=tr('ui_layout.init.status'))
        self.column('name', width=round(500*scale), minwidth=100)
        self.column('state', width=round(150*scale), minwidth=90, stretch=False)

    def curselection(self):
        selected = set(self.selection())
        return tuple(i for i, key in enumerate(self.get_children()) if key in selected)

    def selection_set(self, *indices):
        children = self.get_children()
        super().selection_set([children[int(i)] if isinstance(i, int) else i for i in indices])

    def selection_clear(self, *_):
        self.selection_remove(self.selection())

    def set_items(self, items):
        keys = {item['id'] for item in items}
        for key in self.get_children():
            if key not in keys:
                self.delete(key)
        for index, item in enumerate(items):
            key = item['id']
            symbols = {'waiting': '○', 'processing': '▶', 'completed': '✓', 'interrupted': 'Ⅱ', 'failed': '!'}
            values = (Path(item['source']).name, f"{symbols.get(item['state'], '•')} {tr('queue.'+item['state'])}")
            if not self.exists(key):
                self.insert('', 'end', iid=key, values=values, tags=(item['state'],))
            elif tuple(self.item(key, 'values')) != values:
                self.item(key, values=values, tags=(item['state'],))
            self.move(key, '', index)


def build_ui(app, root, languages, models, output, cache):
    from ui import VERSION, AUTHOR, apply_theme, clear_logs
    from window_style import titlebar
    from ui import palette_for
    root.title('ND TranskripThor')
    scale = max(1, root.winfo_fpixels('1i') / 96)
    app.theme, app.cache = 'dark', cache
    app.style = ttk.Style(root)
    app.style.theme_use('clam')
    app.font = 'Segoe UI'
    app.text_widgets, app.surfaces = [], []
    app.language = tk.StringVar(value='Slovenčina')
    app.quality = tk.StringVar(value=next(iter(models)))
    app.output = tk.StringVar(value=str(output))
    app.offline = tk.BooleanVar(value=False)
    app.autoplay = tk.BooleanVar(value=False)
    footer = ttk.Frame(root, padding=(16, 6))
    footer.pack(side='bottom', fill='x')
    footer.columnconfigure(1, weight=1)
    app.version_label = ttk.Label(footer, text=tr('ui_layout.build_ui.version', p0=VERSION), style='Footer.TLabel')
    app.version_label.grid(row=0, column=0, sticky='sw', padx=(0, 16))
    app.author_label = ttk.Label(footer, text=AUTHOR, style='Footer.TLabel', justify='right', anchor='e')
    app.author_label.grid(row=0, column=1, sticky='e')
    def wrap_author(event):
        available = max(80, event.width-app.version_label.winfo_reqwidth()-48)
        if int(app.author_label.cget('wraplength') or 0) != available:
            app.author_label.configure(wraplength=available)
    footer.bind('<Configure>', wrap_author)
    header = ttk.Frame(root, padding=(16, 6))
    header.pack(fill='x')
    with Image.open(Path(__file__).parent/'assets/transkripthor.png') as logo:
        app.logo_image = ImageTk.PhotoImage(logo.resize((round(36*scale), round(36*scale)), Image.Resampling.LANCZOS), master=root)
        app.window_icon = ImageTk.PhotoImage(logo.resize((256, 256)), master=root)
    root.iconphoto(True, app.window_icon)
    app.icon = tk.Label(header, image=app.logo_image, bd=0)
    app.icon.pack(side='left', padx=(0, 12))
    brand = ttk.Frame(header)
    brand.pack(side='left')
    ttk.Label(brand, text='ND TranskripThor', style='Title.TLabel').pack(anchor='w')
    app.theme_button = ttk.Button(header, command=lambda: apply_theme(app, 'light' if app.theme == 'dark' else 'dark'))
    app.theme_button.pack(side='right')
    app.workspace_tabs = ttk.Notebook(root)
    app.workspace_tabs.enable_traversal()
    app.workspace_tabs.pack(fill='both', expand=True, padx=16)
    app.pages = {}
    for key, name in [('recordings',tr('ui_layout.build_ui.recordings')), ('editor',tr('ui_layout.labels.editor')), ('models',tr('ui_layout.labels.models')), ('settings',tr('ui_layout.labels.settings')), ('details',tr('ui_layout.labels.processing_details'))]:
        page = ttk.Frame(app.workspace_tabs, padding=10)
        app.workspace_tabs.add(page, text=name)
        app.pages[key] = page
    app.editor_page, app.models_page = app.pages['editor'], app.pages['models']
    app.editor_empty = ttk.Label(app.editor_page, text=tr('ui_layout.build_ui.select_a_completed_or_interrupted_recording_and_open_its'), style='Muted.TLabel')
    app.editor_empty.pack(pady=24)
    app.workspace_tabs.bind('<<NotebookTabChanged>>', app.page_changed)
    page = app.pages['recordings']
    # Reserve controls before any flexible content consumes vertical space.
    run = ttk.Frame(page)
    run.pack(side='bottom', fill='x', pady=4)
    toolbar = ttk.Frame(page)
    toolbar.pack(fill='x', pady=(0, 8))
    app.add = ttk.Button(toolbar, text=tr('ui_layout.build_ui.add_recordings'), command=app.add_files)
    app.add.pack(side='left')
    ttk.Button(toolbar, text=tr('ui_layout.build_ui.transcription_settings'), command=lambda: app.workspace_tabs.select(app.pages['settings'])).pack(side='left', padx=8)
    app.file_count = tk.StringVar()
    ttk.Label(toolbar, textvariable=app.file_count, style='Muted.TLabel').pack(side='right')
    app.drop_hint = tk.StringVar(value=tr('ui_layout.build_ui.use_add_recordings_to_select_one_or_more_files'))
    area = ttk.Frame(page, style='Panel.TFrame', padding=8)
    area.pack(fill='both', expand=True)
    app.file_area = area
    ttk.Label(area, textvariable=app.drop_hint, style='CardMuted.TLabel', wraplength=850).pack(fill='x')
    app.listbox = RecordingList(area, scale)
    app.queue_scroll = ttk.Scrollbar(area, command=app.listbox.yview)
    app.listbox.configure(yscrollcommand=app.queue_scroll.set)
    app.listbox.bind('<<TreeviewSelect>>', lambda event: app.update_selection())
    app.listbox.bind('<Double-Button-1>', lambda event: app.context_action())
    app.listbox.bind('<Return>', lambda event: app.context_action())
    app.empty = ttk.Frame(area, style='Field.TFrame', padding=12)
    app.empty.pack(fill='both', expand=True)
    ttk.Label(app.empty, text=tr('ui_layout.build_ui.start_by_adding_a_recording'), style='Empty.TLabel').pack(pady=4)
    actions = FlowFrame(page)
    actions.pack(fill='x', pady=6)
    app.context_button = ttk.Button(actions, text=tr('ui_layout.build_ui.open_transcript'), command=app.context_action)
    app.context_button.pack(side='left')
    app.info_button = ttk.Button(actions, text=tr('ui_layout.build_ui.details'), command=app.show_item_info)
    app.info_button.pack(side='left')
    app.remove = ttk.Button(actions, text=tr('ui_layout.build_ui.remove'), command=app.remove_files)
    app.remove.pack(side='left', padx=4)
    app.move_up = ttk.Button(actions, text=tr('ui_layout.build_ui.move_up'), command=lambda: app.move_item(-1))
    app.move_up.pack(side='left')
    app.move_down = ttk.Button(actions, text=tr('ui_layout.build_ui.move_down'), command=lambda: app.move_item(1))
    app.move_down.pack(side='left', padx=4)
    app.more_button = ttk.Menubutton(actions, text=tr('ui_layout.build_ui.more_options'))
    app.queue_menu = tk.Menu(app.more_button, tearoff=False)
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.open_partial_transcript'), command=app.open_editor)
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.new_transcription_from_start'), command=lambda: app.start('new'))
    app.more_button.configure(menu=app.queue_menu)
    app.more_button.pack(side='right')
    app.selection_info = tk.StringVar(value=tr('ui_layout.build_ui.select_a_recording_for_more_options'))
    app.selection_label = MessageView(page, app, textvariable=app.selection_info, lines=1)
    app.selection_label.pack(fill='x', pady=(0, 6))
    setup = ttk.Frame(app.pages['settings'], style='Panel.TFrame', padding=10)
    setup.pack(fill='x')
    ttk.Label(setup, text=tr('ui_layout.build_ui.for_new_transcriptions'), style='CardBold.TLabel').pack(anchor='w')
    row = ttk.Frame(setup, style='Card.TFrame')
    row.pack(fill='x', pady=6)
    row.columnconfigure(1, weight=1)
    row.columnconfigure(3, weight=1)
    ttk.Label(row, text=tr('ui_layout.build_ui.audio_language'), style='CardMuted.TLabel').grid(row=0, column=0, padx=(0, 6))
    app.lang_box = choice_box(row, app.language, {label: tr('language.'+(code or 'auto')) for label, code in languages.items()}, state='readonly', width=18)
    app.lang_box.grid(row=0, column=1, sticky='ew')
    ttk.Label(row, text=tr('ui_layout.build_ui.model'), style='CardMuted.TLabel').grid(row=0, column=2, padx=8)
    app.model_box = choice_box(row, app.quality, {label: tr('model.'+code) for label, code in models.items()}, state='readonly', width=22)
    app.model_box.grid(row=0, column=3, sticky='ew')
    from speech_models import DEVICES
    app.device_choice = tk.StringVar(value=next(iter(DEVICES)))
    ttk.Label(row, text=tr('ui_layout.build_ui.device'), style='CardMuted.TLabel').grid(row=1, column=0, padx=(0, 6), pady=(6, 0))
    app.device_box = choice_box(row, app.device_choice, {label: tr('device.'+code) for label, code in DEVICES.items()}, state='readonly', width=24)
    app.device_box.grid(row=1, column=1, columnspan=3, sticky='ew', pady=(6, 0))
    app.offline_box = ttk.Checkbutton(row, text=tr('ui_layout.build_ui.offline_only'), variable=app.offline)
    app.offline_box.grid(row=0, column=4, padx=(8, 0))
    path = ttk.Frame(setup, style='Card.TFrame')
    path.pack(fill='x')
    ttk.Label(path, text=tr('ui_layout.build_ui.save_to'), style='CardMuted.TLabel').pack(side='left', padx=(0, 8))
    app.output_entry = ttk.Entry(path, textvariable=app.output)
    app.output_entry.pack(side='left', fill='x', expand=True)
    app.browse = ttk.Button(path, text=tr('ui_layout.build_ui.browse'), command=app.choose_folder)
    app.browse.pack(side='left', padx=(8, 0))
    app.readiness = tk.StringVar()
    app.readiness_label = MessageView(page, app, textvariable=app.readiness, lines=1)
    app.readiness_label.pack(fill='x', pady=6)
    app.start_button = ttk.Button(run, text=tr('ui_layout.build_ui.start_transcription'), style='Accent.TButton', command=app.start)
    app.start_button.pack(side='left')
    app.stop_button = ttk.Button(run, text=tr('ui_layout.build_ui.stop'), command=app.cancel, state='disabled')
    app.stop_button.pack(side='left', padx=8)
    ttk.Button(run, text=tr('ui_layout.build_ui.open_results'), command=app.open_results).pack(side='right')
    status = ttk.Frame(page, padding=(0, 6, 0, 0))
    status.pack(fill='x')
    app.status = tk.StringVar(value=tr('ui_layout.build_ui.add_a_recording_and_start_transcription'))
    app.status_view = MessageView(status, app, textvariable=app.status, lines=2)
    app.status_view.pack(fill='x')
    bar = ttk.Frame(status)
    bar.pack(fill='x', pady=3)
    ttk.Label(bar, text=tr('ui_layout.build_ui.recording'), style='Muted.TLabel', width=10).pack(side='left')
    app.progress = ttk.Progressbar(bar, maximum=100)
    app.progress.pack(side='left', fill='x', expand=True)
    app.percent = tk.StringVar(value='0 %')
    ttk.Label(bar, textvariable=app.percent, width=5, anchor='e').pack(side='right')
    batch = ttk.Frame(status)
    batch.pack(fill='x')
    ttk.Label(batch, text=tr('ui_layout.build_ui.batch'), style='Muted.TLabel', width=10).pack(side='left')
    app.batch_progress = ttk.Progressbar(batch, maximum=100)
    app.batch_progress.pack(fill='x')
    app.timing = tk.StringVar(value=tr('ui_layout.build_ui.batch_time_will_be_estimated_during_transcription'))
    app.timing_label = MessageView(status, app, textvariable=app.timing, lines=1)
    app.timing_label.pack(fill='x')
    app.device_status = tk.StringVar(value=tr('ui_layout.build_ui.device_waiting_for_model_loading'))
    app.device_label = MessageView(status, app, textvariable=app.device_status, lines=1)
    app.device_label.pack(fill='x')
    settings = app.pages['settings']
    locale_row = ttk.Frame(settings)
    locale_row.pack(fill='x', pady=4)
    ttk.Label(locale_row, text=tr('settings.ui_language')).pack(side='left', padx=(0, 8))
    app.ui_language = tk.StringVar(value=app.active_ui_language)
    app.ui_language_box = choice_box(locale_row, app.ui_language, UI_LANGUAGES, state='readonly', width=14)
    app.ui_language_box.pack(side='left')
    MessageView(settings, app, text=tr('settings.restart'), lines=2).pack(fill='x')
    ttk.Label(settings, text=tr('ui_layout.build_ui.settings_and_help'), style='Title.TLabel').pack(anchor='w', pady=4)
    ttk.Checkbutton(settings, text=tr('ui_layout.build_ui.play_audio_automatically_when_selecting_an_editor_segment'), variable=app.autoplay).pack(anchor='w', pady=8)
    help_actions = ttk.Frame(settings)
    help_actions.pack(side='bottom', fill='x', pady=4, before=setup)
    reset = ttk.Button(help_actions, text=tr('ui_layout.build_ui.reset_defaults'), command=app.reset_settings)
    reset.pack(side='left')
    ttk.Button(help_actions, text=tr('accessibility.shortcuts'), command=lambda: messagebox.showinfo(
        tr('accessibility.shortcuts'), tr('accessibility.help'), parent=root)).pack(side='left', padx=8)
    MessageView(settings, app, text=tr('ui_layout.build_ui.set_the_language_model_device_and_folder_for_pending'), lines=3).pack(fill='both', expand=True, pady=4)
    details = app.pages['details']
    app.clear_button = ttk.Button(details, text=tr('ui_layout.build_ui.clear_preview_and_messages'), command=lambda: clear_logs(app))
    app.clear_button.pack(anchor='e', pady=(0, 6))
    app.result_tabs = ttk.Notebook(details)
    app.result_tabs.enable_traversal()
    app.result_tabs.pack(fill='both', expand=True)
    for label, attr in [(tr('ui_layout.build_ui.transcript_preview'), 'preview'), (tr('ui_layout.build_ui.activity_log'), 'activity')]:
        panel = ttk.Frame(app.result_tabs)
        app.result_tabs.add(panel, text=label)
        text = tk.Text(panel, wrap='word', height=4, state='disabled', font=(app.font, 11), relief='flat', padx=12, pady=10)
        from accessibility import text_navigation
        text_navigation(text)
        scrollbar = ttk.Scrollbar(panel, command=text.yview)
        scrollbar.pack(side='right', fill='y')
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(fill='both', expand=True)
        setattr(app, attr, text)
        app.text_widgets.append(text)
    apply_theme(app, 'dark')
    def resized(event):
        if event.widget == root:
            width = max(200, page.winfo_width()-24)
            app.selection_label.configure(wraplength=width)
            app.readiness_label.configure(wraplength=width)
    root.bind('<Configure>', resized, add='+')
    # Refresh system contrast colors when returning from Windows settings.
    def contrast_changed(event):
        if event.widget == root:
            from accessibility import high_contrast_palette
            if high_contrast_palette() != getattr(app, 'contrast_palette', None):
                apply_theme(app, app.theme)
            if event.type == tk.EventType.Map:
                palette = palette_for(app)
                root.after_idle(lambda: titlebar(root, app.theme == 'dark', palette['bg'], palette['text']))
    root.bind('<FocusIn>', contrast_changed, add='+')
    root.bind('<Map>', contrast_changed, add='+')
    root.update_idletasks()
    width = min(round(1040*scale), root.winfo_screenwidth()-40)
    height = min(round(740*scale), root.winfo_screenheight()-80)
    root.minsize(width, height)
    root.geometry(f'{width}x{height}+20+20')
    root.protocol('WM_DELETE_WINDOW', app.close)
    root.after(100, app.poll)
