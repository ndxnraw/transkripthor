"""Deterministic worker-GC regressions; no ignored Tk destructor exceptions."""
import copy
import gc
from pathlib import Path
import sys
import threading
import tkinter as tk
import time
import unittest
import weakref
from unittest.mock import patch

from ndtranskripthor.presentation.tk_lifecycle import TkVariables, collect_retired
from ndtranskripthor.presentation import tk_lifecycle
from ndtranskripthor.projects.project import Project
import test_editor_speakers


class VariableLifetimeTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.scope = TkVariables(self.root)
        self.errors = []
        self.hook = patch.object(sys, 'unraisablehook', lambda details: self.errors.append(
            (details.exc_type.__name__, str(details.exc_value))))
        self.hook.start()
        self.addCleanup(self.hook.stop)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if not self.scope.closed:
            self.root.destroy()
        collect_retired()
        self.assertEqual(self.errors, [])

    def collect_in_worker(self):
        worker = threading.Thread(target=gc.collect)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.errors, [])

    def test_worker_collection_keeps_live_value_and_native_trace_behavior(self):
        value = self.scope.string('Neuložené 日本')
        value.cycle = value
        trace = []
        value.trace_add('write', lambda *_: trace.append('write'))
        reference = weakref.ref(value)
        del value
        before = gc.isenabled()
        self.collect_in_worker()
        value = reference()
        self.assertIs(type(value), tk.StringVar)
        self.assertEqual(value.get(), 'Neuložené 日本')
        value.set('Ďalšia úprava')
        self.assertEqual(trace, ['write'])
        self.assertEqual(gc.isenabled(), before)

    def test_destroy_releases_tcl_variable_and_traces_on_ui_thread(self):
        frame = tk.Frame(self.root)
        scope = TkVariables(frame)
        value = scope.string('Pending')
        value.cycle = value
        name = str(value)
        released = []
        value.trace_add('unset', lambda *_: released.append(threading.get_ident()))
        frame.destroy()
        self.assertEqual(released, [threading.get_ident()])
        self.assertEqual(self.root.tk.call('info', 'exists', name), 0)
        self.assertIsNone(value._tk)
        self.assertIsNone(value._root)
        self.assertEqual(scope.variables, [])
        del value, frame, scope
        self.collect_in_worker()

    def test_repeated_root_close_then_worker_gc_has_no_tk_finalization(self):
        for _ in range(8):
            root = tk.Tk()
            scope = TkVariables(root)
            value = scope.boolean(True)
            value.cycle = value
            root.destroy()
            self.assertIsNone(value._tk)
            del value, scope, root
            self.collect_in_worker()
            collect_retired()

    def test_retired_interpreters_are_released_on_main_thread(self):
        collect_retired()
        baseline = len(tk_lifecycle._retired_interpreters)
        references = []
        def create_and_close():
            root = tk.Tk()
            references.append(weakref.ref(root))
            scope = TkVariables(root)
            scope.string('Temporary').cycle = scope
            root.destroy()
        for _ in range(4):
            create_and_close()
        collect_retired()
        self.assertTrue(all(reference() is None for reference in references))
        self.assertLessEqual(len(tk_lifecycle._retired_interpreters), baseline)

    def test_worker_cannot_create_a_tk_variable(self):
        errors = []
        def create():
            try:
                self.scope.string('Invalid thread')
            except RuntimeError as exc:
                errors.append(str(exc))
        worker = threading.Thread(target=create)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ['Tk variables require the UI thread'])


class EditorLifetimeTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_diagnostic_worker_gc_preserves_unsaved_editor_and_cancelled_close(self):
        e = self.editor
        self.select(0)
        e.text.insert('end', ' Neuložené 日本')
        e.modified()
        e.text.mark_set('insert', '1.4')
        e.text.tag_add('sel', '1.0', '1.4')
        self.root.update()
        field = e.text
        state = (field.get('1.0', 'end-1c'), field.index('insert'),
                 tuple(map(str, field.tag_ranges('sel'))), copy.deepcopy(e.history.__dict__))
        errors = []
        worker_ids = []
        def scan(*args):
            worker_ids.append(threading.get_ident())
            gc.collect()
            return []
        with patch.object(sys, 'unraisablehook', lambda details: errors.append(str(details.exc_value))), \
             patch('ndtranskripthor.presentation.data_dialog.inventory', side_effect=scan):
            for _ in range(4):
                self.app.manage_data()
                dialog = self.app.data_dialog
                deadline = time.monotonic()+5
                while dialog.snapshot is None:
                    self.root.update()
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
                dialog.close()
            self.assertEqual(errors, [])
        self.assertTrue(worker_ids)
        self.assertNotIn(threading.get_ident(), worker_ids)
        self.assertEqual((field.get('1.0', 'end-1c'), field.index('insert'),
                          tuple(map(str, field.tag_ranges('sel'))), e.history.__dict__), state)
        with patch('ndtranskripthor.presentation.editor.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(e.close())
        self.assertFalse(e.variables.closed)
        self.assertIs(e.text, field)
        self.assertTrue(e.dirty)
        self.assertEqual((field.get('1.0', 'end-1c'), field.index('insert'),
                          tuple(map(str, field.tag_ranges('sel')))), state[:3])
        e.undo()
        self.assertEqual(e.text.get('1.0', 'end-1c'), 'Text 0.')
        e.redo()
        self.assertIn('Neuložené 日本', e.text.get('1.0', 'end-1c'))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Text 0.')


if __name__ == '__main__':
    unittest.main()
