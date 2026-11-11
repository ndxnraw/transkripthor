"""Compact Studio presentation; transcription remains in the existing worker."""
from ndtranskripthor.core.resources import resource_path
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.core.i18n import LANGUAGES as UI_LANGUAGES
from ndtranskripthor.presentation.choices import choice_box
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from ndtranskripthor.presentation.responsive import MessageView, FlowFrame, ScrollFrame, ViewStack
from ndtranskripthor.presentation.tk_lifecycle import TkVariables


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
            values = (Path(item['source']).name, f"{symbols.get(item['state'], '•')} {tr('result.no_speech') if item.get('outcome') == 'no_speech' else tr('queue.'+item['state'])}")
            if not self.exists(key):
                self.insert('', 'end', iid=key, values=values, tags=(item['state'],))
            elif tuple(self.item(key, 'values')) != values:
                self.item(key, values=values, tags=(item['state'],))
            self.move(key, '', index)


class MenuAction:
    """An existing application action presented as a native menu command."""
    def __init__(self, menu, text, command):
        self.menu = menu
        menu.add_command(label=text, command=command)
        self.index = menu.index('end')

    def configure(self, **options):
        if 'text' in options:
            options['label'] = options.pop('text')
        self.menu.entryconfigure(self.index, **options)

    def __getitem__(self, name):
        return self.menu.entrycget(self.index, 'label' if name == 'text' else name)

    def invoke(self):
        return self.menu.invoke(self.index)


def build_ui(app, root, languages, models, output, cache):
    from ndtranskripthor.presentation.ui import VERSION, AUTHOR, apply_theme, clear_logs
    root.title('ND TranskripThor')
    scale = max(1, root.winfo_fpixels('1i') / 96)
    app.theme, app.cache = 'dark', cache
    app.font = 'Segoe UI'
    from ndtranskripthor.presentation.theme import ThemeManager
    app.theme_manager = ThemeManager(app, root)
    app.style = app.theme_manager.style
    app.text_widgets, app.surfaces = [], []
    app.variables = TkVariables(root)
    app.language = app.variables.string(value='Slovenčina')
    app.quality = app.variables.string(value=next(iter(models)))
    app.output = app.variables.string(value=str(output))
    app.offline = app.variables.boolean(value=False)
    app.autoplay = app.variables.boolean(value=False)
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
    with Image.open(resource_path('assets/transkripthor.png')) as logo:
        app.logo_image = ImageTk.PhotoImage(logo.resize((round(36*scale), round(36*scale)), Image.Resampling.LANCZOS), master=root)
        app.window_icon = ImageTk.PhotoImage(logo.resize((256, 256)), master=root)
    root.iconphoto(True, app.window_icon)
    app.icon = tk.Label(header, image=app.logo_image, bd=0)
    app.icon.pack(side='left', padx=(0, 12))
    brand = ttk.Frame(header)
    brand.pack(side='left')
    ttk.Label(brand, text='ND TranskripThor', style='Title.TLabel').pack(anchor='w')
    app.utility_button = ttk.Menubutton(header, style='Quiet.TMenubutton', text=tr('studio.options'))
    app.utility_button.pack(side='right')
    app.utility_menu = tk.Menu(app.utility_button, tearoff=False)
    app.utility_button.configure(menu=app.utility_menu)
    app.theme_button = MenuAction(app.utility_menu, '', lambda: apply_theme(app, 'light' if app.theme == 'dark' else 'dark'))
    app.open_project_button = ttk.Button(header, width=0, style='Quiet.TButton', text=tr('project.open'), command=app.choose_project)
    app.open_project_button.pack(side='right', padx=4)
    app.back_bar = ttk.Frame(root, padding=(16, 4))
    app.back_button = ttk.Button(app.back_bar, text=tr('studio.back'), style='Quiet.TButton', command=lambda: app.workspace_tabs.select(app.pages['recordings']))
    app.back_button.pack(side='left')
    app.section_title = app.variables.string()
    ttk.Label(app.back_bar, textvariable=app.section_title).pack(side='left', padx=12)
    app.workspace_tabs = ViewStack(root)
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
    def navigation(event=None):
        current = app.workspace_tabs.select()
        if current == str(app.pages['recordings']):
            app.back_bar.pack_forget()
        else:
            app.section_title.set(next(name for key, name in (
                ('editor', tr('ui_layout.labels.editor')), ('models', tr('ui_layout.labels.models')),
                ('settings', tr('ui_layout.labels.settings')), ('details', tr('ui_layout.labels.processing_details'))
            ) if current == str(app.pages[key])))
            app.back_bar.pack(fill='x', before=app.workspace_tabs)
    app.workspace_tabs.bind('<<NotebookTabChanged>>', navigation, add='+')
    root.bind('<Alt-Home>', lambda event: app.workspace_tabs.select(app.pages['recordings']))
    app.utility_menu.add_separator()
    def open_tool(key):
        if key == 'models':
            app.manage_models()
            if app.model_dialog is None or not app.model_dialog.window.winfo_exists():
                return
        app.workspace_tabs.select(app.pages[key])
    for key, label in (('settings', tr('studio.advanced')), ('models', tr('ui_layout.labels.models')),
                       ('details', tr('ui_layout.labels.processing_details'))):
        action = MenuAction(app.utility_menu, label, lambda page=key: open_tool(page))
        if key == 'models':
            app.models_action = action
    app.utility_menu.add_separator()
    app.utility_menu.add_command(label=tr('ui_layout.build_ui.open_results'), command=app.open_results)
    app.utility_menu.add_command(label=tr('about.title'), command=lambda: show_about(root))
    page = app.pages['recordings']
    # Reserve controls before any flexible content consumes vertical space.
    app.run_panel = ttk.Frame(page, style='Card.TFrame', padding=8)
    app.run_panel.pack(side='bottom', fill='x', pady=(4, 0))
    run = FlowFrame(app.run_panel, style='Card.TFrame')
    app.readiness = app.variables.string()
    app.readiness_label = MessageView(run, app, textvariable=app.readiness, lines=1, surface='card')
    app.readiness_label.configure(width=140)
    app.readiness_label.pack(side='left')
    run.stretch = app.readiness_label
    run.pack(fill='x')
    # Processing and actions are reserved before the queue gets remaining space.
    app.processing_panel = ttk.Frame(page, style='Card.TFrame', padding=8)
    app.processing_panel.pack(side='bottom', fill='x', pady=(4, 0))
    app.file_count = app.variables.string()
    app.drop_hint = app.variables.string(value=tr('ui_layout.build_ui.use_add_recordings_to_select_one_or_more_files'))
    area = ttk.Frame(page, style='Panel.TFrame', padding=12)
    area.pack(fill='both', expand=True)
    app.file_area = area
    queue_heading = app.queue_heading = ttk.Frame(area, style='Card.TFrame')
    queue_heading.pack(fill='x', pady=(0, 6))
    ttk.Label(queue_heading, text=tr('workspace.queue'), style='Section.TLabel').pack(side='left')
    ttk.Label(queue_heading, textvariable=app.file_count, style='CardMuted.TLabel').pack(side='left', padx=12)
    app.add = ttk.Button(area, style='Secondary.TButton', text=tr('ui_layout.build_ui.add_recordings'), command=app.add_files)
    app.queue_hint = ttk.Label(area, textvariable=app.drop_hint, style='CardMuted.TLabel', wraplength=850)
    app.queue_hint.pack(fill='x', pady=(0, 6))
    app.listbox = RecordingList(area, scale)
    app.queue_scroll = ttk.Scrollbar(area, command=app.listbox.yview)
    app.listbox.configure(yscrollcommand=app.queue_scroll.set)
    app.listbox.bind('<<TreeviewSelect>>', lambda event: app.update_selection())
    app.listbox.bind('<Double-Button-1>', lambda event: app.context_action())
    app.listbox.bind('<Return>', lambda event: app.context_action())
    app.empty = ttk.Frame(area, style='Card.TFrame', padding=16)
    app.empty.pack(fill='both', expand=True)
    app.empty.columnconfigure(0, weight=1)
    app.empty.rowconfigure(0, weight=1)
    app.empty_body = ttk.Frame(app.empty, style='Card.TFrame')
    app.empty_body.grid(row=0, column=0)
    app.empty_heading = ttk.Label(app.empty_body, text=tr('studio.title'), style='Hero.TLabel', justify='center', anchor='center', wraplength=720)
    app.empty_heading.pack(fill='x', pady=(0, 10))
    app.empty_description = ttk.Label(app.empty_body, text=tr('studio.description'), style='CardMuted.TLabel', justify='center', anchor='center', wraplength=640)
    app.empty_description.pack(fill='x', pady=(0, 20))
    app.add.pack(in_=app.empty_body, pady=(0, 14))
    app.empty_hint = ttk.Label(app.empty_body, textvariable=app.drop_hint, style='CardMuted.TLabel', justify='center', anchor='center', wraplength=640)
    app.empty_hint.pack(fill='x')
    def wrap_empty(event):
        width = max(160, event.width-48)
        for label in (app.empty_heading, app.empty_description, app.empty_hint):
            if int(label['wraplength']) != width:
                label.configure(wraplength=width)
    app.empty.bind('<Configure>', wrap_empty)
    actions = app.queue_tools = FlowFrame(page)
    actions.pack(side='bottom', fill='x', pady=(6, 0), before=area)
    app.context_button = ttk.Button(actions, text=tr('ui_layout.build_ui.open_transcript'), command=app.context_action)
    app.context_button.pack(side='left')
    app.more_button = ttk.Menubutton(actions, text=tr('ui_layout.build_ui.more_options'))
    app.queue_menu = tk.Menu(app.more_button, tearoff=False)
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.open_partial_transcript'), command=app.open_editor)
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.new_transcription_from_start'), command=lambda: app.start('new'))
    app.queue_menu.add_separator()
    app.info_button = MenuAction(app.queue_menu, tr('ui_layout.build_ui.details'), app.show_item_info)
    app.remove = MenuAction(app.queue_menu, tr('workspace.remove_from_queue'), app.remove_files)
    app.queue_menu.add_separator()
    app.move_up = MenuAction(app.queue_menu, tr('ui_layout.build_ui.move_up'), lambda: app.move_item(-1))
    app.move_down = MenuAction(app.queue_menu, tr('ui_layout.build_ui.move_down'), lambda: app.move_item(1))
    app.queue_menu.add_separator()
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.open_results'), command=app.open_results)
    app.queue_menu.add_command(label=tr('ui_layout.build_ui.transcription_settings'), command=lambda: app.workspace_tabs.select(app.pages['settings']))
    app.more_button.configure(menu=app.queue_menu)
    app.more_button.pack(side='right')
    app.selection_info = app.variables.string(value=tr('ui_layout.build_ui.select_a_recording_for_more_options'))
    app.selection_label = MessageView(actions, app, textvariable=app.selection_info, lines=1)
    app.selection_label.configure(width=160)
    app.selection_label.pack(side='left')
    actions.stretch = app.selection_label
    app.settings_scroll = ScrollFrame(app.pages['settings'])
    app.settings_scroll.pack(fill='both', expand=True)
    app.quick_settings = ttk.Frame(page, style='Card.TFrame', padding=8)
    app.quick_settings.pack(side='bottom', fill='x', pady=(6, 0), before=app.processing_panel)
    row = ttk.Frame(app.quick_settings, style='Card.TFrame')
    row.pack(fill='x')
    row.columnconfigure(1, weight=1)
    row.columnconfigure(3, weight=1)
    ttk.Label(row, text=tr('ui_layout.build_ui.audio_language'), style='CardMuted.TLabel').grid(row=0, column=0, padx=(0, 6))
    app.lang_box = choice_box(row, app.language, {label: tr('language.'+(code or 'auto')) for label, code in languages.items()}, state='readonly', width=14)
    app.lang_box.grid(row=0, column=1, sticky='ew')
    ttk.Label(row, text=tr('studio.quality'), style='CardMuted.TLabel').grid(row=0, column=2, padx=8)
    app.model_box = choice_box(row, app.quality, {label: tr('quality.'+('kinit' if code.startswith('kinit/') else code)) for label, code in models.items()}, state='readonly', width=14)
    app.model_box.grid(row=0, column=3, sticky='ew')
    setup = ttk.Frame(app.settings_scroll.body, style='Panel.TFrame', padding=10)
    setup.pack(fill='x')
    ttk.Label(setup, text=tr('studio.advanced'), style='CardBold.TLabel').pack(anchor='w')
    row = ttk.Frame(setup, style='Card.TFrame')
    row.pack(fill='x', pady=6)
    row.columnconfigure(1, weight=1)
    from ndtranskripthor.asr.speech_models import DEVICES
    app.device_choice = app.variables.string(value=next(iter(DEVICES)))
    ttk.Label(row, text=tr('ui_layout.build_ui.device'), style='CardMuted.TLabel').grid(row=0, column=0, padx=(0, 6))
    app.device_box = choice_box(row, app.device_choice, {label: tr('device.'+code) for label, code in DEVICES.items()}, state='readonly', width=24)
    app.device_box.grid(row=0, column=1, sticky='ew')
    app.offline_box = ttk.Checkbutton(row, text=tr('ui_layout.build_ui.offline_only'), variable=app.offline)
    app.offline_box.grid(row=1, column=0, columnspan=2, sticky='w', pady=(6, 0))
    path = ttk.Frame(setup, style='Card.TFrame')
    path.pack(fill='x')
    ttk.Label(path, text=tr('ui_layout.build_ui.save_to'), style='CardMuted.TLabel').pack(side='left', padx=(0, 8))
    app.output_entry = ttk.Entry(path, textvariable=app.output)
    app.output_entry.pack(side='left', fill='x', expand=True)
    app.browse = ttk.Button(path, text=tr('ui_layout.build_ui.browse'), command=app.choose_folder)
    app.browse.pack(side='left', padx=(8, 0))
    app.start_button = ttk.Button(run, text=tr('ui_layout.build_ui.start_transcription'), style='Accent.TButton', command=app.start)
    app.start_button.pack(side='left')
    app.stop_button = ttk.Button(run, style='Stop.TButton', text=tr('ui_layout.build_ui.stop'), command=app.cancel, state='disabled')
    app.stop_button.pack(side='left', padx=8)
    status = app.processing_panel
    progress_heading = ttk.Frame(status, style='Card.TFrame')
    progress_heading.pack(fill='x', pady=(0, 4))
    app.workspace_state = app.variables.string(value=tr('workspace.ready'))
    app.workspace_badge = ttk.Label(progress_heading, textvariable=app.workspace_state, style='Status.TLabel')
    app.workspace_badge.pack(side='right')
    app.status = app.variables.string(value=tr('ui_layout.build_ui.add_a_recording_and_start_transcription'))
    app.status_view = MessageView(progress_heading, app, textvariable=app.status, lines=1, surface='card')
    app.status_view.pack(side='left', fill='x', expand=True, padx=(0, 8))
    bars = ttk.Frame(status, style='Card.TFrame')
    bars.pack(fill='x', pady=3)
    bars.columnconfigure(0, weight=1, uniform='progress')
    bars.columnconfigure(1, weight=1, uniform='progress')
    bar = ttk.Frame(bars, style='Card.TFrame')
    bar.grid(row=0, column=0, sticky='ew', padx=(0, 12))
    app.progress_label = app.variables.string(value=tr('ui_layout.build_ui.recording'))
    ttk.Label(bar, textvariable=app.progress_label, style='CardMuted.TLabel', width=12).pack(side='left')
    app.progress = ttk.Progressbar(bar, maximum=100)
    app.progress.pack(side='left', fill='x', expand=True)
    app.percent = app.variables.string(value='0 %')
    ttk.Label(bar, textvariable=app.percent, style='CardBold.TLabel', width=5, anchor='e').pack(side='right')
    batch = ttk.Frame(bars, style='Card.TFrame')
    batch.grid(row=0, column=1, sticky='ew')
    ttk.Label(batch, text=tr('ui_layout.build_ui.batch'), style='CardMuted.TLabel', width=12).pack(side='left')
    app.batch_progress = ttk.Progressbar(batch, maximum=100)
    app.batch_progress.pack(side='left', fill='x', expand=True)
    app.timing = app.variables.string(value=tr('ui_layout.build_ui.batch_time_will_be_estimated_during_transcription'))
    app.timing_label = MessageView(status, app, textvariable=app.timing, lines=1, surface='card')
    app.timing_label.pack(fill='x')
    app.device_status = app.variables.string(value=tr('ui_layout.build_ui.device_waiting_for_model_loading'))
    settings = app.settings_scroll.body
    preferences = ttk.Frame(settings, style='Card.TFrame', padding=(8, 4))
    preferences.pack(fill='x', pady=(4, 0))
    locale_row = ttk.Frame(preferences, style='Card.TFrame')
    locale_row.pack(fill='x', pady=4)
    ttk.Label(locale_row, text=tr('settings.ui_language'), style='CardMuted.TLabel').pack(side='left', padx=(0, 8))
    app.ui_language = app.variables.string(value=app.active_ui_language)
    app.ui_language_box = choice_box(locale_row, app.ui_language, UI_LANGUAGES, state='readonly', width=14)
    app.ui_language_box.pack(side='left')
    app.autoplay_box = ttk.Checkbutton(preferences, text=tr('ui_layout.build_ui.play_audio_automatically_when_selecting_an_editor_segment'), variable=app.autoplay)
    app.autoplay_box.pack(anchor='w', pady=4)
    MessageView(settings, app, text=tr('settings.restart'), lines=1).pack(fill='x')
    help_actions = FlowFrame(app.pages['settings'])
    help_actions.pack(side='bottom', fill='x', pady=4, before=app.settings_scroll)
    ttk.Button(help_actions, text=tr('data.title'), command=app.manage_data).pack(side='left', padx=(0, 8))
    ttk.Button(help_actions, text=tr('about.title'), command=lambda: show_about(root)).pack(side='left', padx=(0, 8))
    reset = ttk.Button(help_actions, text=tr('ui_layout.build_ui.reset_defaults'), command=app.reset_settings)
    reset.pack(side='left')
    ttk.Button(help_actions, text=tr('accessibility.shortcuts'), command=lambda: messagebox.showinfo(
        tr('accessibility.shortcuts'), tr('accessibility.help'), parent=root)).pack(side='left', padx=8)
    MessageView(settings, app, text=tr('ui_layout.build_ui.set_the_language_model_device_and_folder_for_pending'), lines=1).pack(fill='both', expand=True, pady=4)
    details = app.pages['details']
    app.clear_button = ttk.Button(details, text=tr('ui_layout.build_ui.clear_preview_and_messages'), command=lambda: clear_logs(app))
    app.clear_button.pack(anchor='e', pady=(0, 6))
    app.device_label = MessageView(details, app, textvariable=app.device_status, lines=1)
    app.device_label.pack(fill='x', pady=(0, 6))
    app.result_tabs = ttk.Notebook(details)
    app.result_tabs.enable_traversal()
    app.result_tabs.pack(fill='both', expand=True)
    for label, attr in [(tr('ui_layout.build_ui.transcript_preview'), 'preview'), (tr('ui_layout.build_ui.activity_log'), 'activity')]:
        panel = ttk.Frame(app.result_tabs)
        app.result_tabs.add(panel, text=label)
        text = tk.Text(panel, wrap='word', height=4, state='disabled', font=(app.font, 11), relief='flat', padx=12, pady=10)
        from ndtranskripthor.presentation.accessibility import text_navigation
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
    # ThemeManager owns system contrast refresh for the root and every dialog.
    root.update_idletasks()
    width = min(round(1040*scale), root.winfo_screenwidth()-40)
    height = min(round(740*scale), root.winfo_screenheight()-80)
    root.minsize(width, height)
    root.geometry(f'{width}x{height}+20+20')
    root.protocol('WM_DELETE_WINDOW', app.close)
    app.poll_timer = root.after(100, app.poll)


def show_about(root):
    from version import DISPLAY_VERSION, VERSION
    from ndtranskripthor.presentation.ui import AUTHOR
    messagebox.showinfo(tr('about.title'),
        tr('about.body', channel=DISPLAY_VERSION, version=VERSION, author=AUTHOR), parent=root)
