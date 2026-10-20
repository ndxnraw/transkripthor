"""Temporary s16 PCM, bounded decoding/VAD and independently readable slices."""
import os
import shutil
import tempfile
import threading
import time
import errno
import logging
from pathlib import Path
from i18n import tr
from ownership import Lease, OwnershipError

RATE = 16000
RESERVE = 32 * 1024 * 1024


def cleanup(folder):
    """Only our known scratch files; OS leases protect other active readers."""
    folder = Path(folder)
    if not folder.exists():
        return
    for directory in folder.glob('pcm-*'):
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            if time.time() - directory.stat().st_mtime < 86400:
                continue  # Avoid racing a newly created entry before its lease exists.
            with Lease(directory/'.lock', reentrant=False):
                (directory/'audio.s16').unlink(missing_ok=True)
            (directory/'.lock').unlink(missing_ok=True)
            directory.rmdir()
        except (OSError, OwnershipError):
            continue


class DiskAudio:
    def __init__(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        cleanup(folder)
        self.directory = Path(tempfile.mkdtemp(prefix='pcm-', dir=folder))
        self.lease = Lease(self.directory/'.lock')
        self.path = self.directory/'audio.s16'
        self.samples = 0
        self.closed = False
        self.lock = threading.Lock()

    def __len__(self):
        return self.samples

    def __getitem__(self, key):
        import numpy as np
        if not isinstance(key, slice):
            raise TypeError('PCM reads require a slice')
        start, end, step = key.indices(self.samples)
        if step != 1:
            raise ValueError('PCM reads require contiguous samples')
        with self.lock:
            if self.closed:
                raise ValueError('PCM cache is closed')
            with self.path.open('rb') as stream:
                stream.seek(start*2)
                data = np.fromfile(stream, dtype='<i2', count=max(0, end-start))
            if len(data) != max(0, end-start):
                raise OSError(tr('pcm.incomplete'))
        return data.astype(np.float32) / 32768.0

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).warning('PCM scratch cleanup deferred', exc_info=True)
            finally:
                self.lease.close()
            try:
                (self.directory/'.lock').unlink(missing_ok=True)
                self.directory.rmdir()
            except OSError:
                pass  # Next preparation reaps abandoned scratch data.

    def __del__(self):
        if hasattr(self, 'lock'):
            try:
                self.close()
            except OSError:
                pass


def decode_audio(source, sampling_rate=RATE, *, folder=None, stop=None):
    import av
    from faster_whisper.audio import _ignore_invalid_frames, _group_frames, _resample_frames
    if sampling_rate != RATE:
        raise ValueError('Unsupported PCM sampling rate')
    audio = DiskAudio(folder or Path(tempfile.gettempdir())/'nd-transkripthor-pcm')
    try:
        resampler = av.audio.resampler.AudioResampler(format='s16', layout='mono', rate=RATE)
        with av.open(str(source), mode='r', metadata_errors='ignore') as container, audio.path.open('wb') as output:
            # Same sample concatenation, resampling and flush as faster-whisper;
            # no duration-based seeking or rounding of the original timeline.
            frames = _group_frames(_ignore_invalid_frames(container.decode(audio=0)), 500000)
            for frame in _resample_frames(frames, resampler):
                if stop is not None and stop.is_set():
                    raise InterruptedError(tr('pcm.stopped'))
                data = frame.to_ndarray().astype('<i2', copy=False)
                if shutil.disk_usage(audio.directory).free < data.nbytes + RESERVE:
                    raise OSError(errno.ENOSPC, tr('pcm.space', path=str(audio.directory.parent)))
                output.write(data.tobytes())
                audio.samples += data.size
            output.flush()
            os.fsync(output.fileno())
        return audio
    except OSError as exc:
        audio.close()
        if exc.errno == errno.ENOSPC or getattr(exc, 'winerror', None) == 112:
            raise OSError(tr('pcm.space', path=str(audio.directory.parent))) from exc
        raise
    except BaseException:
        audio.close()
        raise


def speech_spans(audio, options, stop):
    """VAD has bounded 60-second inputs, with context on both boundaries."""
    from faster_whisper.vad import get_speech_timestamps
    block, context = 60*RATE, RATE
    result = []
    for begin in range(0, len(audio), block):
        if stop.is_set():
            return []
        left, right = max(0, begin-context), min(len(audio), begin+block+context)
        for span in get_speech_timestamps(audio[left:right], options):
            start, end = max(begin, left+span['start']), min(begin+block, left+span['end'], len(audio))
            if end <= start:
                continue
            if result and start <= result[-1]['end']:
                result[-1]['end'] = max(end, result[-1]['end'])
            else:
                result.append(dict(start=start, end=end))
    return result
