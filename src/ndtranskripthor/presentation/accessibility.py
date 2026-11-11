"""Scoped keyboard helpers and read-only Windows contrast preferences."""
import sys


def traverse(event, backwards=False):
    target = event.widget.tk_focusPrev() if backwards else event.widget.tk_focusNext()
    if target is not None:
        target.focus_set()
    return 'break'


def text_navigation(widget):
    widget.bind('<Tab>', traverse)
    widget.bind('<Shift-Tab>', lambda e: traverse(e, True))
    widget.bind('<Control-Tab>', lambda e: cycle_tab(e, 1))
    widget.bind('<Control-Shift-Tab>', lambda e: cycle_tab(e, -1))
    if sys.platform != 'win32':
        widget.bind('<ISO_Left_Tab>', lambda e: traverse(e, True))


def cycle_tab(event, direction):
    parent = event.widget.master
    while parent is not None:
        if hasattr(parent, 'cycle'):
            return parent.cycle(direction)
        if parent.winfo_class() == 'TNotebook':
            tabs = [tab for tab in parent.tabs() if parent.tab(tab, 'state') == 'normal']
            if tabs:
                current = parent.select()
                position = tabs.index(current) if current in tabs else 0
                parent.select(tabs[(position + direction) % len(tabs)])
                parent.focus_set()
            return 'break'
        parent = parent.master
    return traverse(event, direction < 0)


def editing(widget):
    return widget.winfo_class() in ('Text', 'Entry', 'TEntry', 'TCombobox', 'Spinbox', 'TSpinbox')


def high_contrast_palette():
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes
    class HighContrast(ctypes.Structure):
        _fields_ = [('size', wintypes.UINT), ('flags', wintypes.DWORD), ('scheme', wintypes.LPWSTR)]
    value = HighContrast()
    value.size = ctypes.sizeof(value)
    user = ctypes.windll.user32
    if not user.SystemParametersInfoW(0x0042, value.size, ctypes.byref(value), 0) or not value.flags & 1:
        return None
    def color(index):
        rgb = user.GetSysColor(index)
        return f'#{rgb & 255:02x}{(rgb >> 8) & 255:02x}{(rgb >> 16) & 255:02x}'
    return dict(bg=color(5), card=color(5), field=color(5), text=color(8),
                muted=color(8), border=color(8), blue=color(13), accent_text=color(14),
                info=color(5), disabled=color(15))
