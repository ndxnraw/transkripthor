"""Local audio playback with seek/pause; decoding stays off the Tk thread."""
from i18n import tr
import threading
from pathlib import Path
from speech_models import SAMPLE_RATE

RATES = (.75, 1., 1.25, 1.5)


def tempo_blocks(audio, start, end, rate):
    """Bounded PCM reads, pitch-preserving tempo; never copies the recording."""
    import av
    import numpy as np
    from fractions import Fraction
    graph = av.filter.Graph()
    source = graph.add_abuffer(sample_rate=SAMPLE_RATE, format='flt', layout='mono',
                              time_base=Fraction(1, SAMPLE_RATE))
    tempo = graph.add('atempo', str(rate))
    sink = graph.add('abuffersink')
    source.link_to(tempo); tempo.link_to(sink); graph.configure()
    for offset in range(start, end, 4096):
        samples = np.asarray(audio[offset:min(offset+4096, end)], dtype=np.float32)
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format='flt', layout='mono')
        frame.sample_rate = SAMPLE_RATE
        frame.time_base, frame.pts = Fraction(1, SAMPLE_RATE), offset-start
        graph.push(frame)
        while True:
            try:
                yield graph.pull().to_ndarray().reshape(-1)
            except (av.BlockingIOError, av.EOFError):
                break
    graph.push(None)
    while True:
        try:
            yield graph.pull().to_ndarray().reshape(-1)
        except (av.BlockingIOError, av.EOFError):
            break


def output_devices():
    import sounddevice as sd
    hosts = sd.query_hostapis()
    return [(index, device['name'], device['hostapi'], hosts[device['hostapi']]['name'])
            for index, device in enumerate(sd.query_devices()) if device['max_output_channels'] > 0]


class Player:
    def __init__(self):
        self.audio = None
        self.position = 0
        self.limit = 0
        self.stream = None
        self.lock = threading.Lock()
        self.closed = False
        self.stop = threading.Event()
        self.rate = 1.
        self.device = None
        self.error = None
        self.ended = False

    @property
    def playing(self):
        return self.stream is not None and bool(self.stream.active) and not self.ended

    def seek(self, seconds, resume=None):
        running = self.playing if resume is None else resume
        self.pause()
        if self.audio is not None:
            self.position = min(len(self.audio), max(0, round(seconds*SAMPLE_RATE)))
            self.limit = len(self.audio)
            if running:
                self.play()

    def configure(self, rate, device):
        if rate not in RATES:
            raise ValueError('Unsupported playback rate')
        running = self.playing
        self.pause()
        self.rate, self.device = rate, device
        if running:
            self.play(end=self.limit/SAMPLE_RATE)

    def poll_error(self):
        if self.stream is not None and not self.stream.active and not self.ended:
            self.error = self.error or tr('playback.disconnected')
        error, self.error = self.error, None
        if error:
            self.pause()
        return error

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
        self.ended, self.error = False, None
        device_index = None
        if self.device is not None:
            matches = [d for d in output_devices() if d[:3] == self.device[:3]]
            if not matches:
                raise ValueError(tr('playback.disconnected'))
            device_index = matches[0][0]
        blocks = iter(tempo_blocks(self.audio, self.position, self.limit, self.rate)) if self.rate != 1 else None
        pending = next(blocks, None) if blocks is not None else None
        origin, rendered = self.position, 0
        def callback(outdata, frames, timing, status):
            nonlocal pending, rendered
            with self.lock:
                if blocks is not None:
                    outdata.fill(0)
                    filled = 0
                    try:
                        while filled < frames:
                            if pending is None or not len(pending):
                                pending = next(blocks)
                            count = min(frames-filled, len(pending))
                            outdata[filled:filled+count, 0] = pending[:count]
                            pending = pending[count:]
                            filled += count
                        rendered += filled
                        self.position = min(self.limit, origin+round(rendered*self.rate))
                    except StopIteration:
                        self.position, self.ended = self.limit, True
                        raise sd.CallbackStop
                    except Exception as exc:
                        self.error = str(exc)
                        raise sd.CallbackAbort
                    return
                count = max(0, min(frames, self.limit - self.position))
                outdata.fill(0)
                outdata[:count, 0] = self.audio[self.position:self.position + count]
                self.position += count
                if count < frames:
                    self.ended = True
                    raise sd.CallbackStop
        try:
            self.stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                                          device=device_index, blocksize=1024, callback=callback)
            self.stream.start()
        except Exception:
            self.pause()
            raise

    def pause(self):
        if self.stream is not None:
            stream = self.stream
            self.stream = None
            try:
                stream.stop()
            except Exception as exc:
                self.error = str(exc)
            finally:
                try:
                    stream.close()
                except Exception as exc:
                    self.error = str(exc)

    def close(self):
        self.stop.set()
        self.pause()
        with self.lock:
            self.closed = True
            if hasattr(self.audio, 'close'):
                self.audio.close()
            self.audio = None
