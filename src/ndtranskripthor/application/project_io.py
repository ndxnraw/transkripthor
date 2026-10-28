"""Project save/export service. No widgets, Tk calls or UI-owned database handle.

The caller captures immutable edit inputs on the UI thread and runs this function
on its IO worker. Events preserve the distinction between a committed revision
and a successfully published export; the UI alone updates dirty state.
"""
from ndtranskripthor.core.app_errors import classify
from ndtranskripthor.core.contracts import EventSink
from ndtranskripthor.projects.project import Project
from ndtranskripthor.exports.export_formats import export_project


def perform_project_io(folder, events: EventSink, *, rows=None, options=None,
                       token=None, structural=False, request=None):
    try:
        with Project(folder) as project:
            if token is not None:
                project.edit(rows, export_options=options, structural=structural)
                events.put(('io_committed', token))
                warnings = []
            elif request:
                _, warnings = export_project(project, request[0], view=request[1], revision=request[2])
            else:
                warnings = project.retry_export()
        events.put(('io_done', warnings))
    except Exception as exc:
        events.put(('io_error', classify(exc, 'disk')))
