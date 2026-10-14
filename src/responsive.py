"""Bounded, scrollable messages and wrapping control rows for small viewports."""
import tkinter as tk
from tkinter import ttk


class MessageView(ttk.Frame):
    def __init__(self, parent, app, text='', textvariable=None, lines=2, **kwargs):
        super().__init__(parent)
        self.text = tk.Text(self, height=lines, width=1, wrap='word', relief='flat',
                            font=(app.font, 10), padx=0, pady=0, state='disabled', takefocus=True, highlightthickness=1)
        from accessibility import text_navigation
        text_navigation(self.text)
        scroll = ttk.Scrollbar(self, command=self.text.yview)
        def scrolled(first, last):
            scroll.set(first, last)
            if float(first) > 0 or float(last) < 1:
                if not scroll.winfo_manager():
                    scroll.pack(side='right', fill='y', before=self.text)
            elif scroll.winfo_manager():
                scroll.pack_forget()
        self.text.configure(yscrollcommand=scrolled)
        self.text.pack(fill='both', expand=True)
        self.configure(height=self.text.winfo_reqheight())
        self.pack_propagate(False)
        self.variable = textvariable
        def update(*_):
            self.text.configure(state='normal')
            self.text.delete('1.0', 'end')
            self.text.insert('1.0', textvariable.get() if textvariable is not None else text)
            self.text.configure(state='disabled')
        update()
        if textvariable is not None:
            token = textvariable.trace_add('write', update)
            self.bind('<Destroy>', lambda e: textvariable.trace_remove('write', token) if e.widget == self else None)
        if not hasattr(app, 'message_widgets'):
            app.message_widgets = []
        app.message_widgets.append(self.text)
        from ui import palette_for
        palette = palette_for(app)
        self.text.configure(bg=palette['bg'], fg=palette['text'], insertbackground=palette['text'],
                            highlightbackground=palette['bg'], highlightcolor=palette['blue'])

    def configure(self, **kwargs):
        kwargs.pop('wraplength', None)  # Text wraps to the actual viewport.
        if kwargs:
            super().configure(**kwargs)


class FlowFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.pending = None
        self.bind('<Configure>', self.schedule)
        self.bind('<Map>', self.schedule)

    def schedule(self, event=None):
        if self.pending is None:
            self.pending = self.after_idle(self.layout)

    def layout(self):
        self.pending = None
        width = self.winfo_width()
        if width < 100:
            return
        y = used = row_height = 0
        for widget in self.winfo_children():
            if widget.winfo_manager() == 'pack':
                widget.pack_forget()
        for widget in self.winfo_children():
            needed = min(width, widget.winfo_reqwidth()+8)
            if used and used+needed > width:
                y += row_height+4
                used = row_height = 0
            widget.place(x=used, y=y+2, width=min(widget.winfo_reqwidth(), width), height=widget.winfo_reqheight())
            row_height = max(row_height, widget.winfo_reqheight())
            used += needed
        self.configure(height=y+row_height+4)
