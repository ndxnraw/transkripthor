"""Tk adapter for categorized application errors."""
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.core.app_errors import explanation


def show_error(parent, title, issue):
    """Technical details are opt-in, read-only and scrollable."""
    import tkinter as tk
    from tkinter import ttk
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent)
    ttk.Label(window, text=explanation(issue), wraplength=520, padding=16).pack(fill='x')
    body = ttk.Frame(window)
    text = tk.Text(body, width=70, height=10, wrap='word')
    scroll = ttk.Scrollbar(body, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.insert('1.0', issue.get('details', ''))
    text.configure(state='disabled')
    text.pack(side='left', fill='both', expand=True)
    scroll.pack(side='right', fill='y')
    def toggle():
        body.pack_forget() if body.winfo_manager() else body.pack(fill='both', expand=True)
    ttk.Button(window, text=tr('error.details'), command=toggle).pack(padx=16, pady=4)
    button = ttk.Button(window, text=tr('error.close'), command=window.destroy)
    button.pack(padx=16, pady=12)
    button.focus_set()
    window.bind('<Escape>', lambda event: window.destroy())
