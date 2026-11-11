"""Bounded, scrollable messages and wrapping control rows for small viewports."""
import tkinter as tk
from tkinter import ttk


class ViewStack(ttk.Frame):
    """One visible workspace; secondary tools open explicitly and return home."""
    def __init__(self, parent):
        super().__init__(parent)
        self.views = []
        self.current = None

    def add(self, view, **_):
        self.views.append(view)
        if self.current is None:
            self.current = view
            view.pack(fill='both', expand=True)

    def select(self, view=None):
        if view is None:
            return str(self.current) if self.current is not None else ''
        chosen = next(item for item in self.views if str(item) == str(view))
        if chosen is not self.current:
            self.current.pack_forget()
            self.current = chosen
            chosen.pack(fill='both', expand=True)
            self.event_generate('<<NotebookTabChanged>>', when='tail')

    def cycle(self, direction=1):
        # Keyboard navigation stays within the productive recording/editor flow.
        if len(self.views) > 1:
            self.select(self.views[0] if self.current is self.views[1] else self.views[1])
            self.focus_set()
        return 'break'

    def enable_traversal(self):
        self.bind('<Control-Tab>', lambda event: self.cycle())
        self.bind('<Control-Shift-Tab>', lambda event: self.cycle(-1))


class MessageView(ttk.Frame):
    def __init__(self, parent, app, text='', textvariable=None, lines=2, surface='bg', **kwargs):
        super().__init__(parent, style='Card.TFrame' if surface == 'card' else 'TFrame')
        self.text = tk.Text(self, height=lines, width=1, wrap='word', relief='flat',
                            font=(app.font, 10), padx=0, pady=0, state='disabled', takefocus=True, highlightthickness=1)
        from ndtranskripthor.presentation.accessibility import text_navigation
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
        if not hasattr(app, 'message_widgets'):
            app.message_widgets = []
        app.message_widgets.append(self.text)
        def dispose(event):
            if event.widget is self:
                if textvariable is not None:
                    textvariable.trace_remove('write', token)
                app.message_widgets.remove(self.text)
        self.bind('<Destroy>', dispose)
        app.theme_manager.style_text(self.text, surface)

    def configure(self, **kwargs):
        kwargs.pop('wraplength', None)  # Text wraps to the actual viewport.
        if kwargs:
            super().configure(**kwargs)


class ScrollFrame(ttk.Frame):
    """A form can grow vertically while its outer page keeps actions visible."""
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, width=1, height=1)
        self.scroll = ttk.Scrollbar(self, command=self.canvas.yview)
        self.scroll.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(fill='both', expand=True)
        self.body = ttk.Frame(self.canvas)
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.canvas.bind('<Configure>', self.resize)
        self.body.bind('<Configure>', self.resize)
        self.owner = self.winfo_toplevel()
        self.focus_binding = self.owner.bind('<FocusIn>', self.reveal_focus, add='+')
        self.wheel_binding = self.owner.bind('<MouseWheel>', self.wheel, add='+')
        self.bind('<Destroy>', self.dispose)

    def resize(self, event):
        self.canvas.itemconfigure(self.body_id, width=self.canvas.winfo_width(),
                                  height=max(self.body.winfo_reqheight(), self.canvas.winfo_height()))
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def contains(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, 'master', None)
        return False

    def reveal_focus(self, event):
        if self.contains(event.widget) and event.widget not in (self.canvas, self.scroll):
            top = event.widget.winfo_rooty()-self.body.winfo_rooty()
            bottom = top+event.widget.winfo_height()
            visible = self.canvas.canvasy(0)
            height = self.canvas.winfo_height()
            if top < visible or bottom > visible+height:
                target = top if top < visible else bottom-height
                self.canvas.yview_moveto(max(0, target)/max(1, self.body.winfo_height()))

    def wheel(self, event):
        # Text fields and native choices retain their own wheel behavior.
        if self.contains(event.widget) and event.widget.winfo_class() not in ('Text', 'TCombobox', 'TSpinbox', 'TScrollbar'):
            self.canvas.yview_scroll(-int(event.delta/120), 'units')
            return 'break'

    def dispose(self, event):
        if event.widget is self:
            self.owner.unbind('<FocusIn>', self.focus_binding)
            self.owner.unbind('<MouseWheel>', self.wheel_binding)


class FlowFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.pending = None
        self.stretch = None
        self.bind('<Configure>', self.schedule)
        self.bind('<Map>', self.schedule)
        self.bind('<<ThemeChanged>>', self.schedule)
        self.bind('<Destroy>', self.dispose)

    def dispose(self, event):
        if event.widget is self and self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None

    def schedule(self, event=None):
        if self.pending is None:
            self.pending = self.after_idle(self.layout)

    def layout(self):
        self.pending = None
        width = self.winfo_width()
        if width < 100:
            return
        y = used = row_height = 0
        children = self.winfo_children()
        spare = max(0, width - sum(min(width, child.winfo_reqwidth()+8) for child in children))
        for widget in self.winfo_children():
            if widget.winfo_manager() == 'pack':
                widget.pack_forget()
        for widget in self.winfo_children():
            extra = spare if widget is self.stretch else 0
            needed = min(width, widget.winfo_reqwidth()+8+extra)
            if used and used+needed > width:
                y += row_height+4
                used = row_height = 0
            widget.place(x=used, y=y+2, width=min(widget.winfo_reqwidth()+extra, width), height=widget.winfo_reqheight())
            row_height = max(row_height, widget.winfo_reqheight())
            used += needed
        self.configure(height=y+row_height+4)


class DialogPanel(ttk.Frame):
    """Shared themed shell; callers keep ownership of data, validation and close."""
    def __init__(self, window, title):
        super().__init__(window, style='Card.TFrame', padding=12)
        self.window = window
        window.dialog_panel = self
        self.pack(fill='both', expand=True)
        self.actions = FlowFrame(self, style='Card.TFrame')
        self.actions.pack(side='bottom', fill='x', pady=(12, 0))
        self.heading = ttk.Label(self, text=title, style='Section.TLabel', wraplength=520)
        self.heading.pack(fill='x', pady=(0, 12))
        self.content = ttk.Frame(self, style='Card.TFrame')
        self.content.pack(fill='both', expand=True)
        self.messages = []
        self.content.bind('<Configure>', self.wrap_messages)
        def resize(event):
            width = max(160, event.width-24)
            if int(self.heading.cget('wraplength')) != width:
                self.heading.configure(wraplength=width)
        self.bind('<Configure>', resize)

    def message(self, text):
        """Explanatory text follows the available width, including after resize."""
        label = ttk.Label(self.content, text=text, style='CardMuted.TLabel', wraplength=520)
        self.messages.append(label)
        return label

    def wrap_messages(self, event):
        width = max(1, event.width)
        for label in self.messages:
            if label.winfo_exists() and int(label.cget('wraplength')) != width:
                label.configure(wraplength=width)

    def fit(self):
        # Let Tk settle requested sizes in its normal event loop. Synchronously
        # draining idle callbacks while opening a window can reenter layout.
        self.window.maxsize(max(200, self.window.winfo_screenwidth()-60),
                            max(120, self.window.winfo_screenheight()-80))
