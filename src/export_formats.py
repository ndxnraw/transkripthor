"""Explicit exports of one immutable transcript revision, published as a bundle."""
import io
import json
import uuid
import zipfile
from xml.etree import ElementTree as ET
from dataclasses import dataclass, asdict
from state import atomic_text
from subtitles import cues, timestamp
from i18n import tr

FORMATS = ('txt', 'srt', 'vtt', 'docx', 'json')


@dataclass(frozen=True)
class ExportOptions:
    formats: tuple = ('txt', 'srt')
    times: bool = False
    speakers: bool = False

    def __post_init__(self):
        if not self.formats or len(set(self.formats)) != len(self.formats) or any(f not in FORMATS for f in self.formats):
            raise ValueError(tr('exports.formats_required'))


def docx(paragraphs):
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    ET.register_namespace('w', ns)
    document = ET.Element('{'+ns+'}document')
    body = ET.SubElement(document, '{'+ns+'}body')
    for text in paragraphs:
        if any(not (c in '\t\n\r' or 32 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in text):
            raise ValueError(tr('exports.invalid_xml'))
        paragraph = ET.SubElement(body, '{'+ns+'}p')
        run = ET.SubElement(paragraph, '{'+ns+'}r')
        for i, line in enumerate(text.split('\n')):
            if i:
                ET.SubElement(run, '{'+ns+'}br')
            for j, part in enumerate(line.split('\t')):
                if j:
                    ET.SubElement(run, '{'+ns+'}tab')
                node = ET.SubElement(run, '{'+ns+'}t', {'{http://www.w3.org/XML/1998/namespace}space':'preserve'})
                node.text = part
    ET.SubElement(body, '{'+ns+'}sectPr')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml', ET.tostring(document, encoding='utf-8', xml_declaration=True))
    return buffer.getvalue()


def render(rows, options, subtitle_options, duration, metadata):
    from html import escape
    paragraphs, structured = [], []
    for row in rows:
        prefix = f"[{timestamp(row['start'])} – {timestamp(row['end'])}] " if options.times else ''
        if options.speakers and row.get('speaker'):
            prefix += row['speaker']+': '
        paragraphs.append(prefix+row['text'])
        item = dict(id=row['id'], text=row['text'])
        if options.times:
            item.update(start=row['start'], end=row['end'])
        if options.speakers:
            item['speaker'] = row.get('speaker', '')
        if row.get('language'):
            item['language'] = row['language']
        structured.append(item)
    result, warnings = {}, []
    if 'txt' in options.formats:
        result['prepis.txt'] = ('\n'.join(paragraphs)+'\n').encode('utf-8-sig')
    if 'json' in options.formats:
        result['prepis.json'] = json.dumps(dict(schema=1, **metadata, segments=structured), ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    if 'docx' in options.formats:
        result['prepis.docx'] = docx(paragraphs)
    if {'srt', 'vtt'} & set(options.formats):
        subtitle_rows = [dict(row, text=(row.get('speaker', '')+': ' if options.speakers and row.get('speaker') else '')+row['text'],
                              words=[] if options.speakers else row.get('words', [])) for row in rows]
        entries, warnings = cues(subtitle_rows, subtitle_options, audio_duration=duration)
        for format in ('srt', 'vtt'):
            if format not in options.formats:
                continue
            parts = ['WEBVTT\n\n'] if format == 'vtt' else []
            for i, entry in enumerate(entries, 1):
                a, b = timestamp(entry['start']), timestamp(entry['end'])
                if format == 'vtt':
                    a, b = a.replace(',', '.'), b.replace(',', '.')
                parts.append(f"{i}\n{a} --> {b}\n{escape(entry['text'], quote=False)}\n\n")
            result['titulky.'+format] = ''.join(parts).encode('utf-8' if format == 'vtt' else 'utf-8-sig')
    return result, warnings


def publish(folder, files, metadata):
    exports = folder/'exporty'
    generation = exports/uuid.uuid4().hex
    generation.mkdir(parents=True)
    for name, content in files.items():
        with (generation/name).open('xb') as stream:
            stream.write(content)
            stream.flush()
            import os
            os.fsync(stream.fileno())
    # No reader sees a half-written generation. Prior exports remain untouched.
    atomic_text(exports/'aktualny-balik.json', json.dumps(dict(metadata, directory=generation.name, files=list(files)), ensure_ascii=False), 'utf-8')
    return generation.resolve()


def latest_bundle(folder):
    exports = folder/'exporty'
    metadata = json.loads((exports/'aktualny-balik.json').read_text(encoding='utf-8'))
    directory = (exports/metadata['directory']).resolve()
    files = metadata['files']
    allowed = {'prepis.txt', 'prepis.json', 'prepis.docx', 'titulky.srt', 'titulky.vtt'}
    if directory.parent != exports.resolve() or not files or any(name not in allowed or not (directory/name).is_file() for name in files):
        raise ValueError(tr('exports.incomplete'))
    return directory


def export_project(project, options, *, view, revision=None):
    if view not in ('original', 'revision') or (view == 'revision' and revision is None):
        raise ValueError('Export requires an explicit immutable source')
    rows = project.segments(view, revision)
    samples = project.get('samples')
    metadata = dict(view=view, revision=revision)
    request = dict(metadata, options=asdict(options), state='pending')
    with project.db:
        project.put('bundle_export', request)
    files, warnings = render(rows, options, project.subtitle_options(), samples/16000 if samples is not None else None, metadata)
    location = publish(project.folder, files, metadata)
    with project.db:
        project.put('bundle_export', dict(request, state='complete', directory=str(location)))
    return location, warnings
