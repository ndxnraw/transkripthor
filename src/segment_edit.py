"""Pure structural edits; original ASR data is never modified here."""
import math
from i18n import tr


def validate(rows, duration):
    if duration is None or not math.isfinite(duration) or duration < 0:
        raise ValueError(tr('segments.duration_required'))
    previous = 0
    identifiers = set()
    for row in rows:
        a, b, identifier = row['start'], row['end'], row['id']
        if (type(identifier) is not int or identifier < 0 or identifier in identifiers or
                not math.isfinite(a) or not math.isfinite(b) or not previous <= a < b <= duration or
                round(a*1000) >= round(b*1000)):
            raise ValueError(tr('segments.invalid_times'))
        identifiers.add(identifier)
        previous = b


def split(row, offset, seconds, identifier):
    if not 0 < offset < len(row['text']) or not row['start'] < seconds < row['end']:
        raise ValueError(tr('segments.invalid_split'))
    return [dict(row, end=seconds, text=row['text'][:offset], words=[], manual_timing=True),
            dict(row, id=identifier, start=seconds, text=row['text'][offset:], words=[], manual_timing=True)]


def merge(first, second):
    if first.get('speaker', '') != second.get('speaker', ''):
        raise ValueError(tr('segments.different_speakers'))
    separator = '' if not first['text'] or not second['text'] or first['text'][-1].isspace() or second['text'][0].isspace() else ' '
    return dict(first, end=second['end'], text=first['text']+separator+second['text'], words=[], manual_timing=True)
