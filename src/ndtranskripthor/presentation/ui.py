"""Spoločné moderné rozhranie pre Windows."""
from ndtranskripthor.core.i18n import count_text, tr

from version import DISPLAY_VERSION as VERSION
AUTHOR = 'Created by Daniel Návojský (ndxnraw) using Codex | 2026'
from ndtranskripthor.presentation.theme import PALETTES, palette_for
from ndtranskripthor.presentation.ui_layout import build_ui


def clear_logs(app):
    for widget in app.text_widgets:
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.configure(state='disabled')

def update_files(app):
    count = len(app.files)
    app.file_count.set(count_text('recordings.count', count))
    if count:
        app.empty.pack_forget()
        app.queue_tools.pack(side='bottom', fill='x', pady=(6, 0), before=app.file_area)
        app.queue_hint.pack(fill='x', pady=(0, 6))
        app.queue_heading.pack(fill='x', pady=(0, 8), before=app.queue_hint)
        app.add.pack(in_=app.queue_heading, side='right', padx=(8, 0))
        app.add.configure(style='Secondary.TButton', padding=(12, 5))
        app.run_panel.pack(side='bottom', fill='x', pady=(8, 0), before=app.quick_settings)
        if app.busy or getattr(app, 'processing_started', False):
            app.processing_panel.pack(side='bottom', fill='x', pady=(8, 0), before=app.queue_tools)
        else:
            app.processing_panel.pack_forget()
        app.queue_scroll.pack(side='right', fill='y')
        app.listbox.pack(fill='both', expand=True)
    else:
        app.listbox.pack_forget()
        app.queue_scroll.pack_forget()
        app.queue_heading.pack_forget()
        app.queue_hint.pack_forget()
        app.run_panel.pack_forget()
        app.processing_panel.pack_forget()
        app.queue_tools.pack_forget()
        app.empty.pack(fill='both', expand=True)
        app.add.pack(in_=app.empty_body, pady=(0, 14), before=app.empty_hint)
        app.add.configure(style='Accent.TButton', padding=(24, 12))
    # The button's logical parent is the shared queue surface; keep it above
    # its descendant packing container when switching between empty/list views.
    app.add.lift()

def apply_theme(app, theme):
    """Compatibility entry point; all appearance is owned by ThemeManager."""
    app.theme_manager.apply(theme)


def update_workspace_state(app, phase):
    """Present the existing worker phase; never infer a successful ASR result."""
    app.workspace_state.set(tr('progress.phase.' + phase))
    app.processing_started = True
    if app.items and app.queue_tools.winfo_manager():
        app.processing_panel.pack(side='bottom', fill='x', pady=(8, 0), before=app.queue_tools)
