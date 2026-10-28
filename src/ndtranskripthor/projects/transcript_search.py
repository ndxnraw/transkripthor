"""Literal Unicode search with offsets in the unchanged original text."""
import unicodedata


def folded(text):
    parts, spans = [], []
    start = 0
    for end in range(1, len(text)+1):
        if end < len(text) and unicodedata.combining(text[end]):
            continue
        part = unicodedata.normalize('NFC', text[start:end]).casefold()
        parts.append(part)
        spans.extend([(start, end)] * len(part))
        start = end
    return ''.join(parts), spans


def occurrences(text, query):
    needle = unicodedata.normalize('NFC', query).casefold()
    if not needle:
        return []
    normalized = unicodedata.normalize('NFC', text)
    haystack = normalized.casefold()
    # Most transcripts preserve code-point offsets; avoid per-character maps.
    spans = None
    if normalized != text or len(haystack) != len(text):
        haystack, spans = folded(text)
    result, offset = [], 0
    while (offset := haystack.find(needle, offset)) >= 0:
        end = offset + len(needle)
        match = (spans[offset][0], spans[end-1][1]) if spans is not None else (offset, end)
        if not result or match[0] >= result[-1][1]:
            result.append(match)
        offset = end
    return result
