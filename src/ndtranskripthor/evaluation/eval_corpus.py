"""Strict local reference manifest validation, before loading any ASR model."""
import hashlib
import json
import math
import re
from pathlib import Path
from ndtranskripthor.projects.project import fingerprint

LANGUAGES = ('cs', 'sk', 'en', 'hu')


def interval(row, duration, previous=0):
    a,b=row.get('start'),row.get('end')
    if (type(a) not in (int,float) or type(b) not in (int,float) or
            not math.isfinite(a) or not math.isfinite(b) or not previous <= a < b <= duration):
        raise ValueError('Neplatné, prekryté alebo mimo zvuku ležiace referenčné časy.')
    return b


def validate_manifest(path):
    path=Path(path)
    raw=path.read_bytes()
    data=json.loads(raw)
    if data.get('schema') != 2 or not data.get('recordings'):
        raise ValueError('Vyžaduje sa schema=2 a neprázdny oprávnený referenčný korpus.')
    ids, audio_hashes=set(),set()
    for row in data['recordings']:
        identifier=row.get('id')
        if not isinstance(identifier,str) or not re.fullmatch(r'[\w-]+',identifier) or identifier in ids:
            raise ValueError('ID nahrávky musí byť jedinečné a bez častí cesty.')
        ids.add(identifier)
        if (row.get('kind') != 'real' or row.get('authorized') is not True or
                any(not isinstance(row.get(key),str) or not row[key].strip() for key in ('rights','reviewed_by'))):
            raise ValueError('Chýba oprávnenie, pôvod práv alebo ručná kontrola reálnej nahrávky.')
        if row.get('language') not in (*LANGUAGES,'cs-sk'):
            raise ValueError('Chýba platný jazyk spracovania.')
        if not isinstance(row.get('tags'),list) or not row['tags'] or any(not isinstance(t,str) or not t.strip() for t in row['tags']):
            raise ValueError('Každá nahrávka potrebuje scenáre v tags.')
        if len(set(row['tags'])) != len(row['tags']):
            raise ValueError('Duplicitné scenáre.')
        duration=row.get('duration')
        if type(duration) not in (int,float) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('Chýba kladná konečná dĺžka audia.')
        source=(path.parent/row['audio']).resolve()
        if not source.is_file():
            raise ValueError('Referenčná nahrávka neexistuje.')
        digest=fingerprint(source)
        if digest['sha256'] != row.get('sha256') or digest['sha256'] in audio_hashes:
            raise ValueError('Nesúhlasí SHA-256 alebo korpus obsahuje duplicitné audio.')
        audio_hashes.add(digest['sha256'])
        if not isinstance(row.get('segments'),list):
            raise ValueError('Chýbajú referenčné segmenty (pri tichu použite []).')
        previous=0
        for segment in row['segments']:
            previous=interval(segment,duration,previous)
            if segment.get('language') not in LANGUAGES or not isinstance(segment.get('text'),str) or not segment['text'].strip():
                raise ValueError('Neplatný jazyk alebo text referenčného segmentu.')
            end=segment['start']
            for word in segment.get('words',[]):
                end=interval(word,segment['end'],end)
                if not isinstance(word.get('word'),str) or not word['word'].strip():
                    raise ValueError('Neplatné referenčné slovo.')
            if segment.get('words'):
                from ndtranskripthor.evaluation.eval_metrics import tokens
                if tokens(' '.join(w['word'] for w in segment['words'])) != tokens(segment['text']):
                    raise ValueError('Referenčné slová nezodpovedajú textu.')
        for entity in row.get('entities',[]):
            interval(entity,duration)
            if entity.get('kind') not in ('name','number') or not isinstance(entity.get('text'),str) or not entity['text'].strip():
                raise ValueError('Neplatná referencia mena alebo čísla.')
            from ndtranskripthor.evaluation.eval_metrics import tokens
            target=tokens(entity['text'])
            text=tokens(' '.join(s['text'] for s in row['segments'] if s['end']>entity['start'] and s['start']<entity['end']))
            if not target or not any(text[i:i+len(target)]==target for i in range(len(text)-len(target)+1)):
                raise ValueError('Meno alebo číslo chýba v referencii daného intervalu.')
        row['source']=str(source)
    return data,hashlib.sha256(raw).hexdigest()
