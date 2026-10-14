"""Native tkdnd targets and a single, COPY-only file intake path."""
from i18n import tr
import os
import tkinter as tk
from pathlib import Path


def create_root():
    # Public constructor for normal startup; keep file-picker startup usable if
    # Tcl/DLL loading fails after tkinter has already created a window.
    candidate = None
    try:
        from tkinterdnd2 import TkinterDnD
        candidate = TkinterDnD.Tk.__new__(TkinterDnD.Tk)
        TkinterDnD.Tk.__init__(candidate)
        return candidate
    except Exception as exc:
        if candidate is not None:
            try:
                candidate.destroy()
            except (tk.TclError, AttributeError):
                pass
        root = tk.Tk()
        root.dnd_failure = f'{type(exc).__name__}: {exc}'
        return root


def path_key(path):
    return os.path.normcase(str(Path(path).resolve()))


class FileDrop:
    def __init__(self, app):
        self.app = app
        self.targets = []
        self.copy, self.refuse = 'copy', 'refuse_drop'
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES, COPY, REFUSE_DROP
            self.copy, self.refuse = COPY, REFUSE_DROP
            if getattr(app.root, 'dnd_failure', None):
                raise RuntimeError(app.root.dnd_failure)
            try:
                version = app.root.tk.call('package', 'present', 'tkdnd')
            except tk.TclError:
                # Embedded/tests may supply a plain Tk. This is the same loader
                # used by TkinterDnD.Tk in the pinned tkinterdnd2 0.4.3.
                version = TkinterDnD._require(app.root)
            self.log(f'load: tkdnd={version}')
            def register(widget):
                widget.drop_target_register(DND_FILES)
                self.targets.append(widget)
                widget.dnd_bind('<<DropEnter>>', self.enter)
                widget.dnd_bind('<<DropPosition>>', self.enter)
                widget.dnd_bind('<<Drop>>', self.drop)
                for child in widget.winfo_children():
                    register(child)
            register(app.file_area)
            self.log(f'register: {len(self.targets)} targets')
            app.drop_hint.set(tr('file_drop.init.drop_files_in_this_recording_area_or_use_add'))
            if os.name == 'nt':
                import ctypes
                elevated = bool(ctypes.windll.shell32.IsUserAnAdmin())
                self.log(f'privilege: elevated={elevated}; manifest=asInvoker')
                if elevated:
                    app.drop_hint.set(tr('file_drop.init.the_application_is_running_as_administrator_run_it_normally'))
        except Exception as exc:
            for widget in self.targets:
                try:
                    widget.drop_target_unregister()
                except tk.TclError:
                    pass
            self.targets = []
            self.log(f'initialization failed: {type(exc).__name__}: {exc}')
            app.drop_hint.set(tr('file_drop.init.drag_and_drop_is_unavailable_use_add_recordings'))

    def log(self, message):
        self.app.events.put(('log', 'DnD: ' + message))
        try:
            from datetime import datetime
            folder = self.app.store.folder
            folder.mkdir(parents=True, exist_ok=True)
            with (folder/'dnd.log').open('a', encoding='utf-8') as stream:
                stream.write(f'{datetime.now().isoformat(timespec="seconds")} {message}\n')
        except OSError:
            pass

    def enter(self, event):
        if self.app.busy:
            self.app.status.set(tr('file_drop.enter.cannot_add_recordings_during_transcription_stop_transcription_first'))
            return self.refuse
        return self.copy

    def drop(self, event):
        try:
            self.log(f'delivered: target={event.widget}')
            if self.enter(event) == self.refuse:
                self.log('refused: busy')
                return self.refuse
            if not isinstance(event.data, str) or not event.data:
                raise ValueError(tr('file_drop.drop.empty_or_invalid_drop_data'))
            paths = self.app.root.tk.splitlist(event.data)
            accepted = self.app.accept_files(paths)
            self.log(f'handled: paths={len(paths)} accepted={accepted}')
            return self.copy if accepted else self.refuse
        except Exception as exc:
            self.app.status.set(tr('file_drop.drop.could_not_add_files_use_add_recordings_see_diagnostics'))
            self.log(f'handler failed: {type(exc).__name__}: {exc}')
            return self.refuse
