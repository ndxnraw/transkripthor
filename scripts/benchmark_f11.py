import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
"""Real PyAV decoding, isolated Windows process peak working sets."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import wave


def memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in
            ('peak', 'working', 'paged_peak', 'paged', 'nonpaged_peak', 'nonpaged', 'pagefile', 'pagefile_peak', 'private')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    result = Counters(); result.cb = ctypes.sizeof(result)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(result), result.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return result


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--worker':
    from faster_whisper.audio import decode_audio as legacy
    from ndtranskripthor.audio.pcm_audio import decode_audio
    mode, source = sys.argv[2:]
    baseline = memory().working
    started = time.perf_counter()
    audio = legacy(source) if mode == 'legacy' else decode_audio(source, folder=Path(source).parent/'pcm')
    checksum = 0.
    for start in range(0, len(audio), 30*16000):
        checksum += float(audio[start:start+30*16000].sum())
    measured = memory()
    result = dict(mode=mode, duration_hours=len(audio)/16000/3600, samples=len(audio),
        baseline_mib=round(baseline/2**20,2), peak_mib=round(measured.peak/2**20,2),
        working_mib=round(measured.working/2**20,2), seconds=round(time.perf_counter()-started,3), checksum=checksum)
    if hasattr(audio, 'close'): audio.close()
    print(json.dumps(result))
elif __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix='f11-', dir=None) as folder:
        if shutil.disk_usage(folder).free < 1024**3:
            raise OSError('Benchmark needs 1 GiB free disk space')
        source = Path(folder)/'long.wav'
        for hours in (1, 2):
            with wave.open(str(source), 'wb') as wav:
                wav.setparams((1, 2, 16000, 0, 'NONE', ''))
                block = b'\x01\x00' * (16000*60)
                for _ in range(hours*60): wav.writeframesraw(block)
            for mode in ('legacy', 'pcm'):
                run = subprocess.run([sys.executable, __file__, '--worker', mode, str(source)], capture_output=True, text=True, check=True, timeout=180)
                results.append(json.loads(run.stdout))
                print(run.stdout, flush=True)
    args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
