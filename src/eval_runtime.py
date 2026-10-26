"""Windows measurement metadata, without usernames, hostnames or network access."""
import ctypes
from ctypes import wintypes
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import subprocess


def memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in
            ('peak','working','paged_peak','paged','nonpaged_peak','nonpaged','pagefile','pagefile_peak','private')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    result=Counters(); result.cb=ctypes.sizeof(result)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(result),result.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(peak_working_set_bytes=result.peak,working_set_bytes=result.working,private_bytes=result.private)


def environment():
    root=Path(__file__).resolve().parent
    versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.py'))}
    physical_ram=None
    cpu=platform.processor()
    if os.name=='nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
        total=ctypes.c_ulonglong()
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetPhysicallyInstalledSystemMemory.argtypes=[ctypes.POINTER(ctypes.c_ulonglong)]
        if kernel.GetPhysicallyInstalledSystemMemory(ctypes.byref(total)): physical_ram=total.value*1024
    gpu=None
    try:
        run=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader,nounits'],
                           capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        if run.returncode==0: gpu=run.stdout.strip().splitlines()
    except (OSError,subprocess.TimeoutExpired):
        pass
    return dict(python=platform.python_version(),os=platform.platform(),architecture=platform.machine(),
        cpu=cpu,logical_cpus=os.cpu_count(),installed_ram_bytes=physical_ram,gpu_inventory=gpu,libraries=versions,
        execution_environment={key:os.environ.get(key) for key in ('CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        source_sha256=sources,normalization='NFC + casefold + Unicode word tokens; CER joins tokens with spaces')

class GpuMemorySampler:
    """Sample NVIDIA per-process used VRAM, not total GPU utilization or torch-only allocations."""
    def __init__(self, enabled):
        import threading
        self.stop=threading.Event()
        self.peak=None
        self.samples=0
        self.thread=threading.Thread(target=self.run,daemon=True) if enabled else None

    def run(self):
        while not self.stop.is_set():
            try:
                run=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],
                    capture_output=True,text=True,timeout=2,creationflags=subprocess.CREATE_NO_WINDOW)
                values=[]
                if run.returncode==0:
                    for line in run.stdout.splitlines():
                        pid,amount=(p.strip() for p in line.split(',',1))
                        if pid==str(os.getpid()): values.append(int(amount)*1024**2)
                if values:
                    self.peak=max(self.peak or 0,sum(values)); self.samples+=1
            except (OSError,ValueError,subprocess.TimeoutExpired):
                pass
            self.stop.wait(1)

    def __enter__(self):
        if self.thread: self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set()
        if self.thread: self.thread.join(4)

    def result(self):
        return dict(sampled_peak_bytes=self.peak,samples=self.samples,interval_seconds=1,
            scope='NVIDIA per-process memory across GPUs; sampled lower bound, WDDM may not expose it',
            status='measured' if self.samples else 'unavailable')
