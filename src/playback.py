"""Local audio playback with seek/pause; decoding stays off the Tk thread."""
from i18n import tr
import threading
from pathlib import Path
from speech_models import SAMPLE_RATE


class Player:
    def __init__(self):
        self.audio = None
        self.position = 0
        self.limit = 0
        self.stream = None
        self.lock = threading.Lock()
        self.closed = False
        self.stop = threading.Event()

    def load(self, source, folder=None):
        from pcm_audio import decode_audio
        before = Path(source).stat()
        audio = decode_audio(str(source), sampling_rate=SAMPLE_RATE, folder=folder, stop=self.stop)
        try:
            after = Path(source).stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(tr('pcm.source_changed'))
        except BaseException:
            if hasattr(audio, 'close'):
                audio.close()
            raise
        with self.lock:
            if not self.closed:
                if hasattr(self.audio, 'close'):
                    self.audio.close()
                self.audio = audio
                self.position, self.limit = 0, len(audio)
            elif hasattr(audio, 'close'):
                audio.close()
        return len(audio) / SAMPLE_RATE

    def play(self, start=None, end=None):
        import sounddevice as sd
        self.pause()
        if self.audio is None:
            raise ValueError(tr('playback.play.audio_is_still_being_prepared'))
        with self.lock:
            if start is not None:
                self.position = min(len(self.audio), max(0, round(start * SAMPLE_RATE)))
            self.limit = min(len(self.audio), round(end * SAMPLE_RATE)) if end is not None else len(self.audio)
        def callback(outdata, frames, timing, status):
            with self.lock:
                count = max(0, min(frames, self.limit - self.position))
                outdata.fill(0)
                outdata[:count, 0] = self.audio[self.position:self.position + count]
                self.position += count
                if count < frames:
                    raise sd.CallbackStop
        self.stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=callback)
        self.stream.start()

    def pause(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def close(self):
        self.stop.set()
        self.pause()
        with self.lock:
            self.closed = True
            if hasattr(self.audio, 'close'):
                self.audio.close()
            self.audio = None
