"""F24: literal Unicode positions and real Tk navigation without losing edits."""
import unittest
from unittest.mock import patch
import test_editor_speakers
from transcript_search import occurrences
from test_io_support import save_editor
from project import Project


class SearchLogicTest(unittest.TestCase):
    def test_unicode_positions_and_literal_nonoverlapping_matches(self):
        for text, query, expected in [
            ('Čaj čaj ČAJ', 'čaj', [(0, 3), (4, 7), (8, 11)]),
            ('c\u030caj čaj', 'ČAJ', [(0, 4), (5, 8)]),
            ('Straße STRASSE', 'strasse', [(0, 6), (7, 14)]),
            ('😀 čaj', 'ČAJ', [(2, 5)]),
            ('aaaa', 'aa', [(0, 2), (2, 4)]),
            ('[a] [a]', '[a]', [(0, 3), (4, 7)]),
            ('čaj', 'caj', []), ('čaj', '', []), ('', 'čaj', [])]:
            with self.subTest(text=text, query=query):
                self.assertEqual(occurrences(text, query), expected)


class SearchEditorTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_occurrences_forward_backward_highlights_and_no_playback(self):
        e = self.editor
        self.select(0)
        e.text.delete('1.0', 'end')
        e.text.insert('1.0', '😀 Čaj čaj ČAJ')
        e.query.set('čaj')
        with patch.object(e, 'play_segment') as play:
            e.search()
            self.assertEqual(len(e.hits), 3)
            self.assertEqual(e.matches, [0])
            self.assertIn('1/3', e.page_label.get())
            self.assertEqual(len(e.text.tag_ranges('search_match')), 6)
            for start in (6, 10, 2):
                e.next_match()
                self.assertEqual(e.active_hit[1], start)
            e.next_match(-1)
            self.assertEqual(e.active_hit[1], 10)
            left, right = e.text.tag_ranges('search_active')
            self.assertEqual(e.text.get(left, right), 'ČAJ')
            play.assert_not_called()
        self.assertTrue(save_editor(e))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], '😀 Čaj čaj ČAJ')

    def test_filter_page_and_empty_results_preserve_pending_text(self):
        e = self.editor
        self.select(0)
        e.text.insert('end-1c', ' pending')
        e.query.set('Text')
        e.search()
        self.assertEqual(len(e.hits), 45)
        self.assertEqual(len(e.matches), 45)
        e.change_page(1)
        self.select(40)
        e.text.insert('end-1c', ' preserved')
        e.query.set('missing')
        e.search()
        self.assertEqual(e.hits, [])
        self.assertEqual(e.matches, [])
        self.assertIn('0/0', e.page_label.get())
        e.next_match(-1)
        e.apply_theme()  # No active Text exists for an empty result.
        e.query.set('')
        e.search()
        self.assertEqual(len(e.matches), 45)
        self.assertTrue(save_editor(e))
        with Project(self.folder) as project:
            rows = project.segments()
            self.assertTrue(rows[0]['text'].endswith(' pending'))
            self.assertTrue(rows[40]['text'].endswith(' preserved'))

    def test_long_transcript_navigation_reuses_index(self):
        e = self.editor
        e.segments = [dict(id=i, start=i*2, end=i*2+1, text='čaj čaj', words=[]) for i in range(10000)]
        e.segment_indices = {i: i for i in range(10000)}
        e.query.set('ČAJ')
        e.search()
        self.assertEqual(len(e.hits), 20000)
        self.assertEqual(len(e.matches), 10000)
        with patch('editor.occurrences', wraps=occurrences) as find:
            e.next_match(-1)
            self.assertEqual(e.current, 9999)
            self.assertEqual(e.page, 249)
            e.next_match()
            self.assertEqual(e.current, 0)
            self.assertLess(find.call_count, 10)  # Only active text; no full rescan.

    def test_keyboard_directions_and_menu_preserve_clean_state(self):
        e = self.editor
        e.query.set('Text')
        e.search()
        self.root.update()
        e.text.focus_force()
        e.text.event_generate('<F3>')
        self.root.update()
        self.assertEqual(e.current, 1)
        e.text.focus_force()
        e.text.event_generate('<Shift-F3>')
        self.root.update()
        self.assertEqual(e.current, 0)
        e.match_menu.invoke(1)
        self.assertEqual(e.current, 44)
        e.match_menu.invoke(0)
        self.assertEqual(e.current, 0)
        self.assertFalse(e.dirty)
