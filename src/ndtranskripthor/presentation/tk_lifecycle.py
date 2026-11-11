"""Release Tcl variables and retired interpreters on their owning UI thread."""
import atexit
import gc
import sys
import threading
import tkinter as tk
import weakref


_retired_interpreters = []
_collecting = False


def collect_retired():
    """Keep an interpreter alive until Python's dead widget cycles are gone."""
    global _collecting
    if not _retired_interpreters or _collecting:
        return
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Tk cleanup requires the UI thread')
    _collecting = True
    try:
        gc.collect()
        # One reference in the list, one in this loop, one in getrefcount.
        # Still-reachable widgets must retain the pin until a later UI cleanup.
        for interpreter in tuple(_retired_interpreters):
            if sys.getrefcount(interpreter) == 4:  # iteration tuple adds one
                _retired_interpreters.remove(interpreter)
    finally:
        _collecting = False


atexit.register(collect_retired)


class TkVariables:
    """Native Tk variables live at least as long as their owning window/frame."""
    def __init__(self, owner):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Tk variables require the UI thread')
        collect_retired()
        self.owner = weakref.ref(owner)
        self.variables = []
        self.closed = False
        owner.bind('<Destroy>', self.close, add='+')

    def keep(self, variable):
        if self.closed:
            raise RuntimeError('The Tk variable owner is closed')
        self.variables.append(variable)
        return variable

    def make(self, kind, value):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Tk variables require the UI thread')
        if self.closed:
            raise RuntimeError('The Tk variable owner is closed')
        return self.keep(kind(master=self.owner(), value=value))

    def string(self, value=''):
        return self.make(tk.StringVar, value)

    def boolean(self, value=False):
        return self.make(tk.BooleanVar, value)

    def double(self, value=0.):
        return self.make(tk.DoubleVar, value)

    def close(self, event):
        owner = self.owner()
        if self.closed or event.widget is not owner:
            return
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Tk cleanup requires the UI thread')
        self.closed = True
        if isinstance(owner, tk.Tk):
            _retired_interpreters.append(owner.tk)
        for variable in self.variables:
            # Reuse Tk's real unset/trace cleanup, while its interpreter is alive.
            # Clearing both handles makes the later Python finalizer Tcl-free.
            tk.Variable.__del__(variable)
            variable._tk = None
            variable._root = None
        self.variables.clear()
