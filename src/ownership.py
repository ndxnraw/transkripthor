"""OS-owned leases; stale files are harmless and are never deleted to steal locks."""
from i18n import tr
import json
import os
from pathlib import Path
import threading
import uuid
from state import atomic_text

_guard = threading.RLock()
_held = {}


class OwnershipError(RuntimeError):
    pass


class Lease:
    def __init__(self, path, reentrant=True):
        self.closed = True
        self.key = os.path.normcase(str(Path(path).resolve()))
        with _guard:
            if self.key in _held:
                if not reentrant:
                    raise OwnershipError(tr('ownership.init.another_instance_is_already_using_this_profile_or_resource'))
                _held[self.key][1] += 1
            else:
                Path(self.key).parent.mkdir(parents=True, exist_ok=True)
                if os.name == 'nt':
                    import ctypes
                    import msvcrt
                    from ctypes import wintypes
                    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
                    kernel.CreateFileW.restype = wintypes.HANDLE
                    handle = kernel.CreateFileW(self.key, 0xC0000000, 7, None, 4, 0, None)
                    if handle == ctypes.c_void_p(-1).value:
                        raise ctypes.WinError(ctypes.get_last_error())
                    stream = os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDWR), 'r+b')
                else:
                    stream = open(self.key, 'a+b')
                try:
                    if os.name == 'nt':
                        import msvcrt
                        if stream.seek(0, 2) == 0:
                            stream.write(b'0')
                            stream.flush()
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    stream.close()
                    raise OwnershipError(tr('ownership.init.another_instance_is_using_this_profile_project_or_models')) from exc
                _held[self.key] = [stream, 1]
            self.closed = False

    def close(self):
        with _guard:
            if self.closed:
                return
            self.closed = True
            entry = _held[self.key]
            entry[1] -= 1
            if not entry[1]:
                entry[0].close()  # OS releases the lock, also on process termination.
                del _held[self.key]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


def profile_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LokalnyPrepis'


class ProfileOwner:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.lease = Lease(self.folder/'.instance.lock', reentrant=False)
        self.inbox = self.folder/'incoming'
        self.inbox.mkdir(exist_ok=True)

    @staticmethod
    def submit(folder, paths):
        # Durable handoff; only the owner ever reads/writes queue.json.
        inbox = Path(folder).resolve()/'incoming'
        inbox.mkdir(parents=True, exist_ok=True)
        target = inbox/(uuid.uuid4().hex + '.json')
        atomic_text(target, json.dumps([str(Path(p).resolve()) for p in paths], ensure_ascii=False))
        return target

    def receive(self, accept, persist):
        for path in sorted(self.inbox.glob('*.json'))[:20]:
            try:
                if path.stat().st_size > 1024*1024:
                    raise ValueError(tr('ownership.receive.the_forwarded_file_list_is_too_large'))
                paths = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(paths, list) or any(not isinstance(p, str) or '\0' in p for p in paths):
                    raise ValueError(tr('ownership.receive.invalid_file_list'))
            except (ValueError, UnicodeError):
                path.rename(path.with_suffix('.invalid'))
                continue
            if accept(paths) is False and paths:
                if any(Path(p).is_file() for p in paths):
                    return  # Failed queue write: do not acknowledge lost additions.
                path.rename(path.with_suffix('.rejected'))
                continue
            if not persist():
                return  # Replay after restart is safe: accept_files deduplicates paths.
            path.unlink()

    def close(self):
        self.lease.close()
