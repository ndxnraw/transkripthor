"""Data-only tasks. No QObject, QML item or UI database crosses a thread."""
from pathlib import Path
from ndtranskripthor.projects.project import Project, fingerprint
from ndtranskripthor.core.ownership import Lease
from ndtranskripthor.core.i18n import tr


def read_project(folder, events, session):
    lease = Lease(Path(folder)/'.project.lock')
    try:
        with Project(folder) as project:
            problem = project.editor_problem()
            if problem: raise ValueError(problem)
            result = dict(folder=str(folder), rows=project.segments(), source=project.get('source'),
                          fingerprint=project.get('fingerprint'), complete=project.get('complete', False),
                          duration=project.get('samples')/16000 if project.get('samples') is not None else None,
                          subtitles=project.subtitle_options(), next_id=project.next_segment_id(),
                          originals=project.original_available(), revisions=project.revision_ids())
        events.put(('project_opened', (session, result, lease)))
    except BaseException:
        lease.close()
        raise


def load_audio(player, source, digest, folder, events, session):
    if not source or fingerprint(source) != digest:
        raise ValueError(tr('qml.audio_mismatch'))
    length = player.load(source, Path(folder)/'.pcm-cache')
    events.put(('audio_loaded', (session, length)))


def inventory_models(cache, events):
    from ndtranskripthor.models.model_catalog import inventory
    events.put(('model_rows', inventory(cache)))


def model_operation(operation, cache, model, offline, events, stop):
    from ndtranskripthor.models.model_catalog import download, verify_model, remove_model
    emit = lambda kind, value: events.put((kind, value))
    if operation == 'download':
        if offline: raise ValueError('Offline mode: download requires internet access')
        download(cache, model, emit, stop)
    elif operation == 'verify': verify_model(cache, model, offline, emit, stop)
    elif operation == 'remove': remove_model(cache, model)
    else: raise ValueError('Unknown model operation')
    inventory_models(cache, events)


def group_voices(audio, snapshot, path, cache, stop, events, session):
    from ndtranskripthor.asr.speakers import assign_speakers
    with Lease(Path(cache)/'.models.lock'):
        result = assign_speakers(audio, snapshot, path, stop, lambda text: events.put(('status', text)))
    if len(result) != len(snapshot): raise ValueError('Voice result count differs')
    events.put(('voices', (session, dict(zip((row['id'] for row in snapshot), result)))))


def diagnostics(profile, cache, output, projects, states, offline, stop, events):
    from ndtranskripthor.application.local_data import inventory, diagnostic_snapshot
    rows = inventory(profile, cache, output, projects, stop)
    events.put(('diagnostic', (rows, diagnostic_snapshot(rows, states, offline))))
