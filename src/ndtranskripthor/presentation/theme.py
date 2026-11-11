"""One theme owner per Tk interpreter; Windows contrast overrides saved UI mode."""
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as bootstrap
from ttkbootstrap.style import ThemeDefinition

from ndtranskripthor.core.i18n import tr
from ndtranskripthor.presentation import accessibility
from ndtranskripthor.presentation.window_style import titlebar

PALETTES = {
    'dark': dict(bg='#0c1424', card='#172238', field='#111c30', text='#eef2fa', muted='#b0bacb', border='#354763', blue='#92b5ff', accent_text='#111d36', info='#263955', disabled='#30394a', success='#75d3a6', warning='#f0ca74', danger='#ff9a9a'),
    'light': dict(bg='#eef3fb', card='#ffffff', field='#f8faff', text='#202838', muted='#526076', border='#d5dfef', blue='#245bdb', accent_text='#ffffff', info='#e7efff', disabled='#e0e5ee', success='#146c43', warning='#805300', danger='#b42332'),
}

BASE_STYLES = ('TButton', 'TMenubutton', 'TFrame', 'TLabel', 'TEntry', 'TCombobox',
               'TCheckbutton', 'TRadiobutton', 'TSpinbox', 'TNotebook', 'Treeview',
               'Horizontal.TProgressbar', 'Horizontal.TScale', 'Horizontal.TScrollbar',
               'Vertical.TScrollbar', 'Horizontal.TSeparator')


def palette_for(app):
    return getattr(app, 'contrast_palette', None) or PALETTES[getattr(app, 'theme', 'dark')]


def manager_for(widget):
    """Find the owning application without introducing a global app reference."""
    while widget is not None:
        manager = getattr(widget, '_thor_theme_manager', None)
        if manager is not None:
            return manager
        widget = getattr(widget, 'master', None)
    return None


class ThemeManager:
    def __init__(self, app, root):
        self.app, self.root = app, root
        self.closed = False
        self.poll_timer = None
        self.applying = False
        self.listeners = {}
        self.titlebar_timers = {}
        self.bootstrap = bootstrap.Style(theme='bootstrap-dark')
        if self.bootstrap.master is not root:
            raise RuntimeError('The application theme requires a single Tk root')
        # Stock ttk widgets retain their existing semantic style names. This view
        # and ttkbootstrap address the same Tcl style database, without global API patches.
        self.style = ttk.Style(root)
        root._thor_theme_manager = self
        self.app.contrast_palette = None
        for mode, p in PALETTES.items():
            self.bootstrap.register_theme(ThemeDefinition('thor-' + mode, dict(
                primary=p['blue'], secondary=p['muted'], success=p['success'], info=p['blue'],
                warning=p['warning'], danger=p['danger'], light=PALETTES['light']['bg'],
                dark=PALETTES['dark']['bg'], bg=p['bg'], fg=p['text'],
                selectbg=p['blue'], selectfg=p['accent_text'], border=p['border'],
                inputfg=p['text'], inputbg=p['field'], active=p['info']), mode=mode))
        root.bind('<Destroy>', self.close, add='+')
        root.bind_all('<Map>', self.on_map, add='+')
        root.bind_all('<FocusIn>', self.on_focus, add='+')
        self.poll_timer = root.after(1000, self.poll_system)

    @property
    def palette(self):
        return palette_for(self.app)

    def apply(self, mode, *, persist=True):
        if self.closed or self.applying:
            return
        self.applying = True
        try:
            self.app.theme = mode if mode in PALETTES else 'dark'
            self.app.contrast_palette = accessibility.high_contrast_palette()
            if self.app.contrast_palette:
                # Never let the Bootstrap image recipes draw over system colors.
                self.style.theme_use('clam')
            else:
                # ttkbootstrap also changes legacy Text padding and borders.
                # Our bounded MessageViews and editor fields own their geometry.
                geometry = [(widget, {option: widget.cget(option) for option in
                             ('padx', 'pady', 'borderwidth', 'highlightthickness')})
                            for widget in self.widgets(self.root) if isinstance(widget, tk.Text)]
                self.bootstrap.theme_use('thor-' + self.app.theme)
                for widget, options in geometry:
                    widget.configure(**options)
                for name in BASE_STYLES:
                    self.bootstrap.configure(name)
            configure_styles(self.app)
            self.repaint(self.root)
            for window, callback in tuple(self.listeners.items()):
                if window.winfo_exists():
                    callback()
            if hasattr(self.app, 'theme_button'):
                self.app.theme_button.configure(text=tr('ui.apply_theme.light_mode')
                    if self.app.theme == 'dark' else tr('ui.apply_theme.dark_mode'))
            if persist and hasattr(self.app, 'persist_timer'):
                self.app.schedule_save()
        finally:
            self.applying = False

    def refresh_system(self):
        if accessibility.high_contrast_palette() != self.app.contrast_palette:
            self.apply(self.app.theme, persist=False)

    def watch(self, window, callback):
        """Refresh semantic decorations without reconstructing an editor's data/widgets."""
        self.listeners[window] = callback
        window.bind('<Destroy>', lambda event: self.listeners.pop(window, None)
                    if event.widget is window else None, add='+')

    def poll_system(self):
        self.poll_timer = None
        if not self.closed:
            self.refresh_system()
            self.poll_timer = self.root.after(1000, self.poll_system)

    def on_focus(self, event):
        if manager_for(event.widget) is self and isinstance(event.widget, (tk.Tk, tk.Toplevel)):
            self.refresh_system()

    def on_map(self, event):
        if manager_for(event.widget) is self:
            self.style_widget(event.widget)
            if isinstance(event.widget, (tk.Tk, tk.Toplevel)):
                self.refresh_system()

    def style_text(self, widget, surface='field'):
        widget._thor_surface = surface
        p = self.palette
        widget.configure(bg=p[surface], fg=p['text'], insertbackground=p['text'],
                         selectbackground=p['blue'], selectforeground=p['accent_text'],
                         highlightbackground=p[surface] if surface in ('bg', 'card') else p['border'],
                         highlightcolor=p['blue'])

    def style_menu(self, widget):
        p = self.palette
        widget.configure(bg=p['field'], fg=p['text'], activebackground=p['blue'],
                         activeforeground=p['accent_text'], selectcolor=p['blue'],
                         disabledforeground=p['muted'], font=(self.app.font, 10))

    def style_widget(self, widget):
        if not isinstance(widget, tk.Misc) or not widget.winfo_exists():
            return
        p = self.palette
        if isinstance(widget, ttk.Combobox):
            # Tk 8.6 popdowns are Tcl-owned windows, outside winfo_children().
            popup = widget.tk.call('ttk::combobox::PopdownWindow', widget._w)
            widget.tk.call(str(popup) + '.f.l', 'configure', '-background', p['field'],
                           '-foreground', p['text'], '-selectbackground', p['blue'],
                           '-selectforeground', p['accent_text'])
        elif isinstance(widget, ttk.Widget):
            # ttk.Entry/Spinbox also inherit the classic Tk classes in Python,
            # but their colors belong to ttk styles, not Tk's bg/fg options.
            return
        elif isinstance(widget, tk.Text):
            self.style_text(widget, getattr(widget, '_thor_surface', 'field'))
        elif isinstance(widget, tk.Menu):
            self.style_menu(widget)
        elif isinstance(widget, (tk.Tk, tk.Toplevel)):
            widget.configure(bg=p['bg'])
            self.request_titlebar(widget)
        elif isinstance(widget, (tk.Entry, tk.Spinbox, tk.Listbox)):
            widget.configure(bg=p['field'], fg=p['text'], selectbackground=p['blue'],
                             selectforeground=p['accent_text'], highlightcolor=p['blue'],
                             highlightbackground=p['border'])
            if isinstance(widget, (tk.Entry, tk.Spinbox)):
                widget.configure(insertbackground=p['text'], readonlybackground=p['field'],
                                 disabledbackground=p['disabled'], disabledforeground=p['muted'])
        elif isinstance(widget, (tk.Button, tk.Checkbutton, tk.Radiobutton)):
            widget.configure(bg=p['field'], fg=p['text'], activebackground=p['info'],
                             activeforeground=p['text'], disabledforeground=p['muted'],
                             highlightbackground=p['border'], highlightcolor=p['blue'])
            if isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                widget.configure(selectcolor=p['field'])
        elif isinstance(widget, (tk.Frame, tk.Canvas, tk.Label)):
            widget.configure(bg=p['bg'])
            if isinstance(widget, tk.Label):
                widget.configure(fg=p['text'])

    def request_titlebar(self, window):
        if window in self.titlebar_timers or self.closed:
            return
        def update():
            self.titlebar_timers.pop(window, None)
            if not self.closed and window.winfo_exists():
                self.style_titlebar(window)
        # The root owns this callback: quickly closing a child must not delete
        # its pending Tcl command while the application's event loop continues.
        self.titlebar_timers[window] = self.root.after_idle(update)

    def style_titlebar(self, window):
        p = self.palette
        if self.app.contrast_palette:
            # Restore Windows' default caption colors in contrast mode.
            titlebar(window, False, None, None)
        else:
            titlebar(window, self.app.theme == 'dark', p['bg'], p['text'])

    def repaint(self, widget):
        for child in self.widgets(widget):
            self.style_widget(child)

    def widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self.widgets(child)

    def close(self, event):
        if event.widget is not self.root:
            return
        self.closed = True
        for timer in self.titlebar_timers.values():
            self.root.after_cancel(timer)
        self.titlebar_timers.clear()
        self.listeners.clear()
        if self.poll_timer is not None:
            self.root.after_cancel(self.poll_timer)
            self.poll_timer = None
        # Same lifecycle cleanup as ttk.App.destroy(), for TkinterDnD/plain Tk roots.
        if bootstrap.Style.get_instance() is self.bootstrap:
            bootstrap.Style.instance = None
            bootstrap.Fonts.reset()


def configure_styles(app):
    p = palette_for(app)
    s = app.style
    s.configure('.', font=(app.font, 10), background=p['bg'], foreground=p['text'], bordercolor=p['border'], lightcolor=p['border'], darkcolor=p['border'], troughcolor=p['field'])
    s.configure('TFrame', background=p['bg'])
    s.configure('Card.TFrame', background=p['card'], relief='flat', borderwidth=0)
    s.configure('Field.TFrame', background=p['field'])
    s.configure('Selected.TFrame', background=p['card'], bordercolor=p['blue'], lightcolor=p['blue'], darkcolor=p['blue'], relief='solid', borderwidth=1)
    for name, bg, fg in [('TLabel', p['bg'], p['text']), ('Muted.TLabel', p['bg'], p['muted']), ('CardMuted.TLabel', p['card'], p['muted']), ('CardBold.TLabel', p['card'], p['text']), ('FieldMuted.TLabel', p['field'], p['muted']), ('Empty.TLabel', p['field'], p['text']), ('Info.TLabel', p['info'], p['muted']), ('Footer.TLabel', p['bg'], p['muted'])]:
        s.configure(name, background=bg, foreground=fg)
    s.configure('Title.TLabel', font=(app.font, 18, 'bold'))
    s.configure('Hero.TLabel', font=(app.font, 24, 'bold'), background=p['card'], foreground=p['text'])
    s.configure('Eyebrow.TLabel', font=(app.font, 9, 'bold'), background=p['card'], foreground=p['blue'])
    s.configure('CardBold.TLabel', font=(app.font, 10, 'bold'))
    s.configure('Transcript.TLabel', font=(app.font, 11), background=p['card'], foreground=p['text'])
    s.configure('Focus.Transcript.TLabel', background=p['blue'], foreground=p['accent_text'])
    s.configure('Empty.TLabel', font=(app.font, 12, 'bold'))
    s.configure('Footer.TLabel', font=(app.font, 9))
    s.configure('Section.TLabel', font=(app.font, 11, 'bold'), background=p['card'], foreground=p['text'])
    s.configure('Status.TLabel', background=p['card'], foreground=p['blue'], padding=(8, 3),
                relief='solid', borderwidth=1, bordercolor=p['border'])
    s.configure('FieldTitle.TLabel', font=(app.font, 12, 'bold'), background=p['field'], foreground=p['text'])
    s.configure('Quiet.TButton', padding=(8, 4))
    s.configure('Secondary.TButton', foreground=p['blue'])
    s.map('Secondary.TButton', foreground=[('disabled', p['muted']), ('!disabled', p['blue'])])
    s.configure('Stop.TButton', foreground=p.get('danger', p['text']))
    s.map('Stop.TButton', foreground=[('disabled', p['muted']), ('!disabled', p.get('danger', p['text']))])
    s.configure('TButton', padding=(12, 5), background=p['field'], foreground=p['text'], bordercolor=p['border'], focuscolor=p['blue'])
    s.map('TButton', background=[('disabled', p['disabled']), ('active', p['info'])], foreground=[('disabled', p['muted'])])
    s.configure('Accent.TButton', background=p['blue'], foreground=p['accent_text'], focuscolor=p['accent_text'], font=(app.font, 10, 'bold'))
    s.configure('TMenubutton', padding=(12, 5), background=p['field'], foreground=p['text'], focuscolor=p['blue'])
    s.map('TMenubutton', background=[('active', p['info'])], foreground=[('disabled', p['muted'])])
    for name in ['TEntry', 'TCombobox']:
        s.configure(name, fieldbackground=p['field'], foreground=p['text'], background=p['field'], arrowcolor=p['muted'], padding=4, insertcolor=p['text'])
        s.map(name, fieldbackground=[('disabled', p['card']), ('readonly', p['field'])], foreground=[('disabled', p['muted']), ('readonly', p['text'])])
    s.map('TCheckbutton', background=[('active', p['card'])], foreground=[('disabled', p['muted'])])
    s.configure('Horizontal.TProgressbar', background=p['blue'], troughcolor=p['field'], borderwidth=0, thickness=10)
    s.configure('TNotebook', background=p['card'], borderwidth=0)
    s.configure('TNotebook.Tab', background=p['card'], foreground=p['muted'], padding=(16, 8))
    s.configure('Treeview', background=p['field'], fieldbackground=p['field'], foreground=p['text'], rowheight=round(28 * app.root.winfo_fpixels('1i') / 96))
    s.configure('Treeview.Heading', background=p['card'], foreground=p['text'])
    s.configure('TNotebook.Tab', focuscolor=p['blue'])
    app.root.option_add('*TCombobox*Listbox.background', p['field'])
    app.root.option_add('*TCombobox*Listbox.foreground', p['text'])
    app.root.option_add('*TCombobox*Listbox.selectBackground', p['blue'])
    app.root.option_add('*TCombobox*Listbox.selectForeground', p['accent_text'])
    # Explicit state colors are shared by Bootstrap and the image-free contrast theme.
    s.configure('Panel.TFrame', background=p['card'], relief='solid', borderwidth=1, bordercolor=p['border'])
    for name in ('TButton', 'TMenubutton', 'TEntry', 'TCombobox', 'TSpinbox'):
        s.map(name, bordercolor=[('focus', p['blue']), ('!focus', p['border'])])
    for name in ('TEntry', 'TCombobox', 'TSpinbox'):
        s.configure(name, selectbackground=p['blue'], selectforeground=p['accent_text'])
    s.map('Accent.TButton', background=[('disabled', p['disabled']), ('!disabled', p['blue'])],
          foreground=[('disabled', p['muted']), ('!disabled', p['accent_text'])])
    s.map('Treeview', background=[('selected', p['blue'])], foreground=[('selected', p['accent_text'])])
    s.map('TNotebook.Tab', background=[('selected', p['field']), ('active', p['info'])],
          foreground=[('selected', p['blue']), ('!selected', p['text'])])
    for name in ('TRadiobutton', 'TCheckbutton'):
        s.configure(name, background=p['card'], foreground=p['text'], focuscolor=p['blue'])
        s.map(name, foreground=[('disabled', p['muted']), ('!disabled', p['text'])])
    s.configure('TSpinbox', fieldbackground=p['field'], foreground=p['text'],
                background=p['field'], arrowcolor=p['text'], insertcolor=p['text'])
    if app.contrast_palette:
        # Clam's inherited disabled/hover/unfocused maps contain fixed gray
        # colors. Replace them too, not only the widgets' normal colors.
        s.configure('.', selectbackground=p['blue'], selectforeground=p['accent_text'])
        s.map('.', background=[('disabled', p['bg']), ('active', p['bg'])],
              foreground=[('disabled', p['text'])],
              selectbackground=[('!focus', p['blue'])],
              selectforeground=[('!focus', p['accent_text'])])
        for name in ('TEntry', 'TCombobox', 'TSpinbox'):
            s.map(name, background=[('active', p['field']), ('pressed', p['field'])],
                  arrowcolor=[('disabled', p['text']), ('active', p['text'])])
        s.layout('Accent.TButton', s.layout('TButton'))
        for name in ('TRadiobutton', 'TCheckbutton'):
            s.configure(name, indicatorbackground=p['field'], indicatorforeground=p['text'],
                        upperbordercolor=p['border'], lowerbordercolor=p['border'],
                        indicatorsize=round(12 * app.root.winfo_fpixels('1i') / 96))
            s.map(name, indicatorbackground=[('selected', p['blue'])],
                  indicatorforeground=[('selected', p['accent_text'])])
        for name in ('Horizontal.TScale', 'Vertical.TScrollbar', 'Horizontal.TScrollbar'):
            s.configure(name, background=p['field'], troughcolor=p['bg'], bordercolor=p['border'],
                        arrowcolor=p['text'], lightcolor=p['border'], darkcolor=p['border'])
