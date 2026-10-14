from test_io_support import save_editor, export_editor
import unittest
from unittest.mock import patch
import test_editor_speakers
from edit_history import EditHistory
from editor import Editor
from project import Project


class HistoryTest(unittest.TestCase):
    def test_branch_savepoint_and_bounds(self):
        history = EditHistory(max_operations=2, max_bytes=1000)
        for value in range(3):
            history.record([(100, {'text': str(value)}, {'text': str(value+1)})])
        self.assertEqual(len(history.entries), 2)
        history.mark_saved()
        self.assertFalse(history.dirty)
        self.assertEqual(history.step(), [(100, {'text': '2'})])
        self.assertTrue(history.dirty)
        history.step(True)
        self.assertFalse(history.dirty)
        history.step()
        history.record([(100, {'text': '2'}, {'text': 'new'})])
        self.assertIsNone(history.step(True))
        self.assertTrue(history.dirty)
        history.record([(100, {'text': 'new'}, {'text': 'x'*2000})])
        self.assertEqual(history.bytes, 0)
        self.assertEqual(history.entries, [])
        self.assertTrue(history.dirty)

    def test_payload_does_not_alias_live_data(self):
        history = EditHistory()
        after = {'speaker': 'New'}
        history.record([(101, {'speaker': 'Old'}, after)])
        after['speaker'] = 'Changed later'
        history.step()
        self.assertEqual(history.step(True), [(101, {'speaker': 'New'})])


class EditorHistoryTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def replace(self, text):
        self.editor.text.delete('1.0', 'end')
        self.editor.text.insert('1.0', text)
        self.editor.modified()

    def test_segments_pages_search_and_word_alignment(self):
        e = self.editor
        original_words = [dict(word='Text 0.', start=0, end=1)]
        e.segments[0]['words'] = original_words
        self.select(0)
        self.replace('First edit')
        self.select(1)
        self.replace('Second edit')
        e.change_page(1)
        self.select(40)
        self.replace('Third edit')
        e.query.set('nothing matches')
        e.search()
        self.assertEqual(e.matches, [])
        e.undo()
        self.assertEqual(e.current, 40)
        self.assertEqual(e.query.get(), '')
        self.assertEqual(e.text.get('1.0', 'end-1c'), 'Text 40.')
        e.undo()
        self.assertEqual(e.current, 1)
        e.undo()
        self.assertEqual(e.current, 0)
        self.assertEqual(e.segments[0]['words'], original_words)
        self.assertFalse(e.dirty)
        e.redo()
        self.assertEqual(e.segments[0]['text'], 'First edit')
        self.assertEqual(e.segments[0]['words'], [])
        self.assertTrue(e.dirty)

    def test_saved_state_undo_redo_and_reopen(self):
        e = self.editor
        self.select(0)
        self.replace('Saved change')
        with patch('editor.messagebox.showerror', side_effect=AssertionError('Unexpected export error')):
            self.assertTrue(save_editor(e))
        self.assertFalse(e.dirty)
        e.undo()
        self.assertTrue(e.dirty)
        self.assertEqual(e.segments[0]['text'], 'Text 0.')
        e.redo()
        self.assertFalse(e.dirty)
        e.undo()
        with patch('editor.messagebox.showerror', side_effect=AssertionError('Unexpected export error')):
            self.assertTrue(save_editor(e))
        self.assertTrue(e.close())
        reopened = Editor(self.app, self.folder, parent=self.app.editor_page)
        self.assertFalse(reopened.dirty)
        self.assertEqual(reopened.segments[0]['text'], 'Text 0.')
        with Project(self.folder) as project:
            self.assertEqual(project.segments('original')[0]['text'], 'Text 0.')

    def test_manual_speaker_and_batch_rename(self):
        e = self.editor
        self.select(0)
        e.speaker.set('Manual')
        self.select(1)
        e.undo()
        self.assertEqual(e.segments[0]['speaker'], 'Pôvodný')
        e.redo()
        self.assertEqual(e.segments[0]['speaker'], 'Manual')
        self.select(1)
        with patch('editor.simpledialog.askstring', return_value='Renamed'):
            e.rename_speaker()
        self.assertEqual(e.segments[44]['speaker'], 'Renamed')
        e.undo()
        self.assertEqual(e.segments[44]['speaker'], 'Pôvodný')
        self.assertEqual(e.segments[0]['speaker'], 'Manual')
        e.redo()
        self.assertEqual(e.segments[44]['speaker'], 'Renamed')

    def test_async_assignments_and_pending_edit_are_separate(self):
        e = self.editor
        self.select(0)
        token = object()
        baseline = {s['id']: (s['start'], s['end'], 0, s['speaker']) for s in e.segments}
        e.speaker_job = (token, baseline)
        self.replace('Pending text')
        e.apply_speakers(token, {s['id']: 'Voice' for s in e.segments})
        e.undo()
        self.assertEqual(e.segments[0]['text'], 'Pending text')
        self.assertEqual(e.segments[0]['speaker'], 'Pôvodný')
        e.undo()
        self.assertEqual(e.segments[0]['text'], 'Text 0.')
        self.assertFalse(e.dirty)

    def test_keyboard_branch_and_subtitle_dirty_remain_independent(self):
        e = self.editor
        self.select(0)
        self.replace('New text')
        e.text.focus_force()
        self.root.update()
        e.text.event_generate('<Control-z>')
        self.root.update()
        self.assertEqual(e.segments[0]['text'], 'Text 0.')
        e.text.event_generate('<Control-y>')
        self.root.update()
        self.assertEqual(e.segments[0]['text'], 'New text')
        e.undo()
        self.root.update()
        self.assertEqual(self.root.focus_get(), e.text)
        e.text.event_generate('<Control-Shift-Z>')
        self.root.update()
        self.assertEqual(e.segments[0]['text'], 'New text')
        e.undo()
        self.replace('Different branch')
        e.redo()
        self.assertEqual(e.segments[0]['text'], 'Different branch')
        e.cue_values[0].set('55')
        e.undo()
        self.assertTrue(e.dirty)
        self.assertEqual(e.cue_values[0].get(), '55')


if __name__ == '__main__':
    unittest.main()
