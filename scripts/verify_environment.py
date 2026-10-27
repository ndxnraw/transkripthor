"""Reject dependency drift before tests/build; never repair by silently removing packages."""
import argparse
import ast
import importlib.metadata
from pathlib import Path
import re
import sys
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT=Path(__file__).resolve().parents[1]


def pins(path, hashed=True, active=None):
    active=set() if active is None else active
    path=Path(path).resolve()
    if path in active: raise ValueError('Recursive requirements include')
    active.add(path)
    result={}
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            if line.startswith('-r '):
                child=(path.parent/line[3:].strip()).resolve()
                if child.parent != path.parent: raise ValueError('Requirements include outside directory')
                additions=pins(child,hashed,active)
            else:
                pattern=r'([\w.-]+)==([^\s;]+)'+(r' --hash=sha256:([0-9a-f]{64})' if hashed else '')
                match=re.fullmatch(pattern,line)
                if not match: raise ValueError(f'Unpinned or invalid requirement: {path.name}: {line}')
                additions={canonicalize_name(match[1]):match[2]}
            for name,version in additions.items():
                if name in result and result[name]!=version: raise ValueError(f'Conflicting pin: {name}')
                result[name]=version
    finally:
        active.remove(path)
    return result


def validate_locks(root=ROOT):
    req=root/'requirements'
    all_pins=pins(req/'build.lock')
    constraints=pins(req/'constraints.txt',False)
    if all_pins!=constraints: raise ValueError('Constraints differ from the full build closure')
    for mode in ('runtime','speakers','build'):
        locked=pins(req/(mode+'.lock'))
        for name,version in pins(req/(mode+'.in'),False).items():
            if locked.get(name)!=version: raise ValueError(f'Input/lock mismatch: {mode}/{name}')
    tree=ast.parse((root/'src/download_worker.py').read_text(encoding='utf-8-sig'))
    hub=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='HUB_VERSION' for t in n.targets))
    if all_pins.get('huggingface-hub')!=hub: raise ValueError('Hub lock differs from instrumented transport version')
    return all_pins


def check_environment(mode, speakers=False, root=ROOT, installed=None):
    allowed=validate_locks(root)
    allowed.update(pins(root/'requirements/bootstrap.lock'))
    required=pins(root/'requirements'/('build.lock' if mode=='build' else 'runtime.lock'))
    if speakers: required.update(pins(root/'requirements/speakers.lock'))
    required.update(pins(root/'requirements/bootstrap.lock'))
    if installed is None and Path(sys.prefix).resolve() != (root/'.venv').resolve():
        raise ValueError('Use this project .venv, not a shared Python environment')
    distributions=list(importlib.metadata.distributions()) if installed is None else installed
    if installed is None:
        for distribution in distributions:
            if not Path(distribution.locate_file('')).resolve().is_relative_to((root/'.venv').resolve()):
                raise ValueError('Dependency outside project .venv')
    actual={canonicalize_name(d.metadata['Name']):d.version for d in distributions}
    if len(actual)!=len(distributions): raise ValueError('Duplicate installed distributions')
    for name,version in actual.items():
        if allowed.get(name)!=version: raise ValueError(f'Unreviewed installed package/version: {name}=={version}; use a clean locked environment')
    for name,version in required.items():
        if actual.get(name)!=version: raise ValueError(f'Missing locked dependency: {name}=={version}')
    for distribution in distributions:
        for raw in distribution.requires or []:
            dependency=Requirement(raw)
            if dependency.marker and not dependency.marker.evaluate({'extra':''}): continue
            name=canonicalize_name(dependency.name)
            if dependency.url or dependency.extras or name not in actual or actual[name] not in dependency.specifier:
                raise ValueError(f'Unsatisfied/review-required dependency: {distribution.metadata["Name"]}: {dependency}')
    return dict(sorted(actual.items()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('runtime','development','build'),default='build')
    parser.add_argument('--speakers',action='store_true')
    args=parser.parse_args()
    versions=check_environment(args.mode,args.speakers)
    print(f'Locked environment verified: {len(versions)} distributions')
