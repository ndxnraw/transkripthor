"""Presentation-independent progress and batch accounting."""
import math


class ProgressClock:
    """ETA only after measurable work; loading/download time is excluded."""
    def __init__(self, now):
        self.started = now
        self.samples = []

    def update(self, fraction, now):
        if not self.samples or fraction > self.samples[-1][1]:
            self.samples.append((now, fraction))
            self.samples = self.samples[-50:]

    def remaining(self, now):
        if len(self.samples) < 3:
            return None
        elapsed = self.samples[-1][0] - self.samples[0][0]
        advance = self.samples[-1][1] - self.samples[0][1]
        if elapsed < 10 or advance < 0.02 or now - self.samples[-1][0] >= 30:
            return None
        # Time passing without new checkpoints is not completed audio.
        return max(0, (1 - self.samples[-1][1]) * elapsed / advance)


class BatchProgress:
    """Audio coverage and queue outcomes are independent measures."""
    def __init__(self, identifiers):
        self.durations = dict.fromkeys(identifiers)
        self.fractions = dict.fromkeys(identifiers, 0.)
        self.states = dict.fromkeys(identifiers, 'waiting')

    def duration(self, identifier, seconds):
        if identifier in self.durations:
            self.durations[identifier] = (float(seconds) if isinstance(seconds, (int, float))
                and math.isfinite(seconds) and seconds >= 0 else None)

    def progress(self, identifier, percent):
        if identifier in self.fractions and math.isfinite(percent):
            self.fractions[identifier] = max(0., min(1., percent / 100))

    def state(self, identifier, state):
        if identifier in self.states:
            self.states[identifier] = state
            if state == 'completed':
                self.fractions[identifier] = 1.

    def fraction(self):
        if not self.durations or any(value is None for value in self.durations.values()):
            return None
        total = sum(self.durations.values())
        if total == 0:
            return None
        return sum(seconds*self.fractions[key] for key, seconds in self.durations.items())/total

    def counts(self):
        return {state: sum(value == state for value in self.states.values())
                for state in ('completed', 'failed', 'interrupted')}
