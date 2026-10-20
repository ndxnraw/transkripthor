"""Versioned local ASR IPC, bounded acknowledgements and process supervision."""
import atexit
import multiprocessing
import os
import queue
import threading
import time
import uuid
from i18n import tr

VERSION = 1
ACK_SECONDS = 15
CPU_SECONDS = 125
STOP_SECONDS = 10
HEARTBEAT_SECONDS = 60
PROGRESS_SECONDS = 900
_active = set()
_guard = threading.Lock()


def shutdown_all():
    with _guard:
        processes = list(_active)
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join(2)


atexit.register(shutdown_all)


class ProcessTree:
    """Windows kill-on-close job also contains nested download workers."""
    def __init__(self, pid):
        self.handle = None
        if os.name != 'nt':
            return
        import ctypes as c
        from ctypes import wintypes as w
        size = c.c_size_t
        class Basic(c.Structure):
            _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64), ('flags', w.DWORD),
                ('minimum', size), ('maximum', size), ('active', w.DWORD), ('affinity', size),
                ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Extended(c.Structure):
            _fields_ = [('basic', Basic), ('io', c.c_uint64*6), ('process_memory', size),
                ('job_memory', size), ('peak_process', size), ('peak_job', size)]
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        try:
            limits = Extended(); limits.basic.flags = 0x2000
            if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
                raise c.WinError(c.get_last_error())
            process = self.kernel.OpenProcess(0x0101, False, pid)
            try:
                if not process or not self.kernel.AssignProcessToJobObject(self.handle, process):
                    raise c.WinError(c.get_last_error())
            finally:
                if process: self.kernel.CloseHandle(process)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class Channel:
    def __init__(self, connection, run, stop):
        self.connection, self.run, self.stop = connection, run, stop
        self.lock = threading.Lock()
        self.replies = queue.Queue()
        self.closed = threading.Event()
        self.sequence = 0
        threading.Thread(target=self.control, daemon=True).start()
        threading.Thread(target=self.heartbeat, daemon=True).start()

    def send(self, kind, value=None, request=None):
        with self.lock:
            self.sequence += 1
            self.connection.send(dict(version=VERSION, run=self.run, seq=self.sequence,
                                      kind=kind, value=value, request=request))

    def control(self):
        try:
            while not self.closed.is_set():
                message = self.connection.recv()
                if message.get('version') == VERSION and message.get('run') == self.run:
                    self.replies.put(message)
        except (EOFError, OSError):
            self.stop.set()
            # Parent death must also stop an unresponsive native inference.
            if not self.closed.wait(STOP_SECONDS):
                os._exit(70)

    def heartbeat(self):
        while not self.closed.wait(1):
            try:
                self.send('heartbeat')
            except (EOFError, OSError):
                self.stop.set()
                return

    def put(self, event):
        kind, value = event
        if kind not in ('job', 'cpu_request'):
            self.send(kind, value)
            return
        request = uuid.uuid4().hex
        if kind == 'job':
            identifier, changes, ack, result = value
            payload, timeout = (identifier, changes), ACK_SECONDS
        else:
            ack, result = value
            payload, timeout = None, CPU_SECONDS
        self.send(kind, payload, request)
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if kind == 'cpu_request' and self.stop.is_set():
                result.append(False); ack.set(); return
            try:
                response = self.replies.get(timeout=.1)
            except queue.Empty:
                continue
            if response.get('request') == request:
                result.append(response.get('accepted') is True)
                ack.set()
                return
        raise TimeoutError(tr('asr.ack_timeout'))


def worker(connection, config, stop, run, gate):
    if not gate.wait(30):
        return
    from i18n import set_language
    set_language(config.get('ui_language'))
    channel = Channel(connection, run, stop)
    try:
        from asr_batch import BatchRunner
        BatchRunner(config, stop, channel).work(*config['arguments'])
    except BaseException as exc:
        channel.send('error', f'{type(exc).__name__}: {exc}')
    finally:
        channel.closed.set()
        connection.close()


def supervise(config, stop, events, run, *, target=worker, ack_seconds=ACK_SECONDS,
              stop_seconds=STOP_SECONDS, heartbeat_seconds=HEARTBEAT_SECONDS,
              progress_seconds=PROGRESS_SECONDS, outcome=None):
    """Runs on a bridge thread; only serializable data crosses the pipe."""
    def emit(kind, value):
        events.put(('asr', (run, kind, value)), timeout=1)
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    child_stop, gate = ctx.Event(), ctx.Event()
    process = ctx.Process(target=target, args=(child, config, child_stop, run, gate))
    tree = None
    finished = False
    reason = None
    last_seq = 0
    started = False
    try:
        process.start(); started = True
        child.close()
        with _guard:
            _active.add(process)
            # Run before multiprocessing's own non-daemon child join handler.
            atexit.unregister(shutdown_all)
            atexit.register(shutdown_all)
        tree = ProcessTree(process.pid)
        gate.set()
        emit('log', f'ASR protocol={VERSION} run={run} pid={process.pid}')
        last_heartbeat = last_progress = time.monotonic()
        stopping = None
        while True:
            now = time.monotonic()
            if stop.is_set() and stopping is None:
                child_stop.set(); stopping = now
            if stopping is not None and now-stopping > stop_seconds:
                reason = reason or tr('asr.forced_stop'); break
            if stopping is None and (now-last_heartbeat > heartbeat_seconds or now-last_progress > progress_seconds):
                reason = tr('asr.unresponsive')
                child_stop.set(); stopping = now
                emit('status', reason)
            try:
                available = parent.poll(.1)
            except (EOFError, BrokenPipeError):
                break  # Windows reports a closed peer as ERROR_BROKEN_PIPE.
            if not available:
                if not process.is_alive(): break
                continue
            try:
                message = parent.recv()
            except (EOFError, BrokenPipeError):
                break
            if not isinstance(message, dict) or message.get('version') != VERSION or message.get('run') != run:
                raise ValueError('Invalid ASR protocol envelope')
            sequence = message.get('seq')
            if not isinstance(sequence, int) or sequence <= last_seq:
                raise ValueError('Invalid ASR sequence')
            last_seq = sequence
            kind, value = message['kind'], message.get('value')
            last_heartbeat = time.monotonic()
            if kind == 'heartbeat': continue
            last_progress = time.monotonic()
            if kind == 'finished':
                finished = True
                # Await real process exit before allowing the next run.
                stopping = time.monotonic()
                continue
            if kind in ('job', 'cpu_request'):
                if not isinstance(message.get('request'), str):
                    raise ValueError('ASR request identifier missing')
                if kind == 'job' and (not isinstance(value, (list, tuple)) or len(value) != 2 or
                        value[0] not in config['batch_ids'] or not isinstance(value[1], dict) or
                        not set(value[1]).issubset({'state', 'project', 'error', 'error_category', 'outcome', 'segment_count'})):
                    raise ValueError('Invalid ASR job update')
                ack, answer = threading.Event(), []
                emit(kind, (*value, ack, answer) if kind == 'job' else (ack, answer))
                deadline = time.monotonic()+(ack_seconds if kind == 'job' else CPU_SECONDS)
                while not ack.wait(.05):
                    if stop.is_set() or time.monotonic() > deadline or not process.is_alive(): break
                accepted = bool(ack.is_set() and answer and answer[0])
                parent.send(dict(version=VERSION, run=run, request=message['request'], accepted=accepted))
                last_progress = last_heartbeat = time.monotonic()
                if not ack.is_set():
                    reason = tr('asr.ack_timeout')
                    child_stop.set(); stopping = time.monotonic()
            else:
                emit(kind, value)
        process.join(1)
        if (not finished or process.exitcode not in (0, None)) and reason is None:
            reason = tr('asr.crashed', code=process.exitcode)
    except Exception as exc:
        reason = reason or f'{tr("asr.failed")}: {type(exc).__name__}: {exc}'
    finally:
        child_stop.set()
        if started:
            if process.is_alive(): process.terminate()
            process.join(2)
            if process.is_alive():
                process.kill(); process.join(2)
        if tree: tree.close()
        parent.close(); child.close()
        with _guard: _active.discard(process)
        delivered = False
        try:
            if reason:
                emit('process_exit', (reason, stop.is_set()))
            emit('finished', None)
            delivered = True
        except queue.Full:
            pass  # Completion has a separate nonblocking channel to Tk.
        finally:
            if outcome is not None:
                outcome.update(reason=reason, done=True, delivery_failed=not delivered)
