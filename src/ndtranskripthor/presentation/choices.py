"""Localized Tk choices with stable persisted identifiers."""
def choice_box(parent, canonical, labels, **kwargs):
    """Translate display labels without changing legacy ASR settings or IDs."""
    import tkinter as tk
    from tkinter import ttk
    display = tk.StringVar(master=parent)
    reverse = {label: key for key, label in labels.items()}
    def refresh(*_):
        display.set(labels.get(canonical.get(), canonical.get()))
    refresh()
    widget = ttk.Combobox(parent, textvariable=display, values=list(labels.values()), **kwargs)
    widget.bind('<<ComboboxSelected>>', lambda _: canonical.set(reverse[display.get()]))
    token = canonical.trace_add('write', refresh)
    widget.bind('<Destroy>', lambda event: canonical.trace_remove('write', token) if event.widget == widget else None, add='+')
    widget.display_variable = display
    return widget
