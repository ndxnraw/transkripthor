"""Deterministic corpus metrics; no inference or network."""
import re
import unicodedata
from difflib import SequenceMatcher

def tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold(), flags=re.UNICODE)


def distance(reference, hypothesis):
    previous = list(range(len(hypothesis)+1))
    for i, token in enumerate(reference, 1):
        current = [i]
        for j, other in enumerate(hypothesis, 1):
            current.append(min(current[-1]+1, previous[j]+1, previous[j-1]+(token != other)))
        previous = current
    return previous[-1]


def metrics(reference, hypothesis, seconds, duration):
    ref = tokens(' '.join(s['text'] for s in reference))
    hyp = tokens(' '.join(s['text'] for s in hypothesis))
    correct = total = 0.0
    for segment in reference:
        length = segment['end'] - segment['start']
        if length <= 0 or segment['language'] not in ('cs','sk','en','hu'):
            raise ValueError('Referencia musí mať platné intervaly a jazyk cs/sk/en/hu.')
        total += length
        intervals = sorted((max(segment['start'], candidate['start']), min(segment['end'], candidate['end']))
                           for candidate in hypothesis if candidate['language'] == segment['language'])
        last = segment['start']
        for start, end in intervals:
            correct += max(0, end - max(start,last))
            last = max(last,end)
    return dict(wer=distance(ref,hyp)/max(1,len(ref)), reference_words=len(ref),
                language_time_accuracy=correct/total if total else None, processing_seconds=seconds,
                audio_seconds=duration, real_time_factor=seconds/max(.001,duration))



def detailed(reference, hypothesis, seconds, duration, entities=(), tolerance=.5):
    result = metrics(reference, hypothesis, seconds, duration)
    ref = tokens(' '.join(s['text'] for s in reference))
    hyp = tokens(' '.join(s['text'] for s in hypothesis))
    a, b = ' '.join(ref), ' '.join(hyp)
    result.update(word_errors=distance(ref,hyp), character_errors=distance(a,b),
                  reference_characters=len(a), cer=distance(a,b)/len(a) if a else None)
    if not ref:
        result['wer'] = None
    result['inserted_words_on_empty_reference'] = len(hyp) if not ref else 0
    for kind in ('name','number'):
        selected = [e for e in entities if e['kind']==kind]
        errors = 0
        for entity in selected:
            text = tokens(' '.join(s['text'] for s in hypothesis
                          if s['end']>entity['start'] and s['start']<entity['end']))
            target = tokens(entity['text'])
            errors += not any(text[i:i+len(target)]==target for i in range(len(text)-len(target)+1))
        result[kind+'_occurrences'] = len(selected)
        result[kind+'_errors'] = errors
        result[kind+'_error_rate'] = errors/len(selected) if selected else None
    def transitions(rows):
        return [(r['start'], prev['language'], r['language']) for prev,r in zip(rows,rows[1:])
                if prev.get('language') != r.get('language') and prev.get('language') and r.get('language')]
    expected, found = transitions(reference), transitions(hypothesis)
    used, deltas = set(), []
    for when, before, after in expected:
        candidates = [(abs(t-when),i) for i,(t,x,y) in enumerate(found)
                      if i not in used and (x,y)==(before,after) and abs(t-when)<=tolerance]
        if candidates:
            delta,i = min(candidates, key=lambda pair: pair[1]); used.add(i); deltas.append(delta)
    result.update(transition_reference=len(expected), transition_predicted=len(found),
                  transition_matched=len(used), transition_tolerance_seconds=tolerance,
                  transition_precision=len(used)/len(found) if found else None,
                  transition_recall=len(used)/len(expected) if expected else None,
                  transition_mae_seconds=sum(deltas)/len(deltas) if deltas else None)
    # Only exact token matches with reviewed word boundaries contribute timing.
    rw = [w for s in reference for w in s.get('words',[])]
    hw = [w for s in hypothesis for w in s.get('words',[])]
    aligned = SequenceMatcher(None, [tuple(tokens(w['word'])) for w in rw],
                             [tuple(tokens(w['word'])) for w in hw], autojunk=False)
    timing=[]
    for block in aligned.get_matching_blocks():
        for i in range(block.size):
            x,y=rw[block.a+i],hw[block.b+i]
            timing.extend([abs(x['start']-y['start']),abs(x['end']-y['end'])])
    result.update(timed_reference_words=len(rw), timed_matched_words=len(timing)//2,
                  word_boundary_mae_seconds=sum(timing)/len(timing) if timing else None)
    return result


def summarize(results):
    groups={}
    for row in results:
        for tag in row.get('tags',[]) or ['untagged']:
            groups.setdefault((row['model'],row['revision'],row['device'],tag),[]).append(row)
    output=[]
    for (model,revision,device,tag),rows in groups.items():
        ok=[r for r in rows if r['status']=='ok']; m=[r['metrics'] for r in ok]
        words=sum(x['reference_words'] for x in m)
        duration=sum(x['audio_seconds'] for x in m)
        output.append(dict(model=model,revision=revision,device=device,scenario=tag,
            attempts=len(rows),successes=len(ok),failures=len(rows)-len(ok),
            wer=sum(x['word_errors'] for x in m)/words if words else None,
            real_time_factor=sum(x['processing_seconds'] for x in m)/duration if duration else None,
            recordings=[r['id'] for r in rows]))
        summary=output[-1]
        for numerator,denominator,key in (
            ('character_errors','reference_characters','cer'),
            ('name_errors','name_occurrences','name_error_rate'),
            ('number_errors','number_occurrences','number_error_rate'),
            ('transition_matched','transition_reference','transition_recall'),
            ('transition_matched','transition_predicted','transition_precision')):
            n,d=sum(x[numerator] for x in m),sum(x[denominator] for x in m)
            summary[key]=dict(numerator=n,denominator=d,rate=n/d if d else None)
        summary['word_timing']=[dict(id=r['id'],matched=r['metrics']['timed_matched_words'],
            reference=r['metrics']['timed_reference_words'],mae_seconds=r['metrics']['word_boundary_mae_seconds']) for r in ok]
        summary['peak_ram_bytes']=max((value for r in ok if (value := r.get('memory',{}).get('final',{}).get('peak_working_set_bytes')) is not None),default=None)
        summary['sampled_vram_bytes']=[r.get('vram',{}).get('sampled_peak_bytes') for r in ok]
    return output
