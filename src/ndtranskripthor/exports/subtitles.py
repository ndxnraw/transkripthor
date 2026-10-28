"""Čitateľné titulky. Bez časov slov nikdy nevymýšľať hranice slov."""
from ndtranskripthor.core.i18n import tr
import math
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleOptions:
    characters: int = 42
    lines: int = 2
    min_duration: float = 1.0
    max_duration: float = 7.0

    def __post_init__(self):
        if type(self.characters) is not int or type(self.lines) is not int or \
                not isinstance(self.min_duration, (int, float)) or not isinstance(self.max_duration, (int, float)) or \
                not 10 <= self.characters <= 120 or not 1 <= self.lines <= 4 or \
                not 0 < self.min_duration <= self.max_duration <= 30:
            raise ValueError(tr('subtitles.post_init.subtitles_characters_lines_and_times_of_s_minimum_maximum'))


def timestamp(seconds):
    value = max(0, round(seconds * 1000))
    seconds, ms = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def normalized(text):
    return ' '.join(text.split())


def wrapped(text, characters):
    # Hyphenated names are words too: never insert whitespace into them.
    return textwrap.wrap(text, characters, break_long_words=False, break_on_hyphens=False)


def cues(segments, options=None, *, audio_duration=None):
    options = options or SubtitleOptions()
    result, warnings = [], set()
    if audio_duration is not None:
        if not isinstance(audio_duration, (int, float)) or not math.isfinite(audio_duration) or audio_duration < 0:
            raise ValueError(tr('subtitles.invalid_audio_duration'))
        audio_end_ms = math.floor(audio_duration * 1000 + 1e-9)
    else:
        audio_end_ms = None
        warnings.add(tr('subtitles.unknown_audio_duration'))
    for segment_index, segment in enumerate(segments, 1):
        text = normalized(segment['text'])
        if not text:
            continue
        start, end = float(segment['start']), float(segment['end'])
        if not math.isfinite(start + end) or not 0 <= start < end:
            raise ValueError(tr('subtitles.cues.invalid_subtitle_time_interval'))
        if audio_duration is not None and end > audio_duration:
            raise ValueError(tr('subtitles.outside_audio', index=segment_index, end=end, duration=audio_duration))
        words = segment.get('words') or []
        try:
            aligned = normalized(' '.join(w.get('word', '') for w in words)) == text
            previous = start
            for word in words:
                a, b = word.get('start', -1), word.get('end', -1)
                if not math.isfinite(a + b) or not previous <= a < b <= end:
                    aligned = False
                previous = b
        except (TypeError, ValueError, AttributeError):
            aligned = False
        groups = []
        if aligned and words:
            group = []
            for word in words:
                combined = normalized(' '.join(w['word'] for w in group + [word]))
                full = (len(wrapped(combined, options.characters)) > options.lines or
                        (group and word['end'] - group[0]['start'] > options.max_duration))
                sentence = group and group[-1]['word'].rstrip().endswith(('.', '!', '?')) and \
                    group[-1]['end'] - group[0]['start'] >= options.min_duration
                if group and (full or sentence):
                    groups.append(dict(start=group[0]['start'], end=group[-1]['end'],
                                       text=normalized(' '.join(w['word'] for w in group))))
                    group = []
                group.append(word)
            if group:
                groups.append(dict(start=group[0]['start'], end=group[-1]['end'],
                                   text=normalized(' '.join(w['word'] for w in group))))
        else:
            groups = [dict(start=start, end=end, text=text)]
            if len(wrapped(text, options.characters)) > options.lines or end-start > options.max_duration:
                warnings.add(tr('subtitles.unaligned', index=segment_index))
        if segment.get('manual_timing'):
            for group in groups:
                group['manual_timing'] = True
        result.extend(groups)
    # Validate the actual millisecond intervals written to SRT before publishing.
    for index, cue in enumerate(result, 1):
        cue['start'] = round(cue['start'] * 1000)
        cue['end'] = round(cue['end'] * 1000)
        if audio_end_ms is not None:
            cue['end'] = min(cue['end'], audio_end_ms)
        if cue['start'] >= cue['end']:
            raise ValueError(tr('subtitles.zero_interval', index=index))
        if index > 1 and cue['start'] < result[index-2]['end']:
            raise ValueError(tr('subtitles.overlap', index=index))
    for index, cue in enumerate(result):
        boundary = result[index+1]['start'] if index+1 < len(result) else (audio_end_ms if audio_end_ms is not None else cue['end'])
        if not cue.pop('manual_timing', False):
            cue['end'] = min(max(cue['end'], cue['start'] + math.ceil(options.min_duration * 1000)), boundary)
        duration = (cue['end'] - cue['start']) / 1000
        if duration < options.min_duration:
            warnings.add(tr('subtitles.too_short', index=index+1, actual=duration, limit=options.min_duration))
        if duration > options.max_duration:
            warnings.add(tr('subtitles.too_long', index=index+1, actual=duration, limit=options.max_duration))
        lines = wrapped(cue['text'], options.characters)
        if len(lines) > options.lines:
            warnings.add(tr('subtitles.too_many_lines', index=index+1, actual=len(lines), limit=options.lines))
        longest = max(map(len, lines), default=0)
        if longest > options.characters:
            warnings.add(tr('subtitles.long_line', index=index+1, actual=longest, limit=options.characters))
        cue['text'] = '\n'.join(lines)
    for cue in result:
        cue['start'] /= 1000
        cue['end'] /= 1000
    return result, sorted(warnings)


def render_srt(segments, options=None, *, audio_duration=None):
    items, warnings = cues(segments, options, audio_duration=audio_duration)
    return ''.join(f'{i}\n{timestamp(s["start"])} --> {timestamp(s["end"])}\n{s["text"]}\n\n'
                   for i, s in enumerate(items, 1)), warnings
