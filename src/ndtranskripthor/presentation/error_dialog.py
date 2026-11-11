"""Tk adapter for categorized application errors."""
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.core.app_errors import explanation


def show_error(parent, title, issue):
    """Technical details are opt-in, read-only and scrollable."""
    import tkinter as tk
    from tkinter import ttk
    from ndtranskripthor.presentation.responsive import DialogPanel
    from ndtranskripthor.presentation.accessibility import text_navigation
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent)
    panel = DialogPanel(window, title)
    panel.message(explanation(issue)).pack(fill='x')
    body = ttk.Frame(panel.content, style='Card.TFrame')
    text = tk.Text(body, width=60, height=8, wrap='word', font=('Segoe UI', 10), padx=8, pady=8)
    window.details_text = text
    text_navigation(text)
    scroll = ttk.Scrollbar(body, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.insert('1.0', issue.get('details', ''))
    text.configure(state='disabled')
    text.pack(side='left', fill='both', expand=True)
    scroll.pack(side='right', fill='y')
    def toggle():
        body.pack_forget() if body.winfo_manager() else body.pack(fill='both', expand=True)
        panel.fit()
    window.details_button = ttk.Button(panel.actions, text=tr('error.details'), command=toggle)
    window.details_button.pack(side='left')
    button = ttk.Button(panel.actions, text=tr('error.close'), style='Accent.TButton', command=window.destroy)
    button.pack(side='left')
    button.focus_set()
    window.bind('<Escape>', lambda event: window.destroy())
    panel.fit()
    return window
