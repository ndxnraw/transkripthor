"""F08: validate serialized intervals, truthful soft-limit warnings, no text loss."""
import tempfile
import unittest
from i18n import set_language
from project import Project
from subtitles import SubtitleOptions, cues, normalized, render_srt


def segment(start, end, text='Text', words=None):
    return dict(start=start, end=end, text=text, words=words or [])


class SubtitleValidationTest(unittest.TestCase):
    def setUp(self):
        set_language('en')

    def test_short_last_cue_and_available_extension(self):
        result, warnings = cues([segment(0, .1)], audio_duration=.1)
        self.assertEqual(result[0]['end'], .1)
        self.assertTrue(any('0.100 s' in w and 'minimum' in w for w in warnings))
        result, warnings = cues([segment(0, .1)], audio_duration=2)
        self.assertEqual(result[0]['end'], 1)
        self.assertEqual(warnings, [])

    def test_extension_stops_at_next_cue(self):
        result, warnings = cues([segment(0, .1), segment(.2, 1.2)], audio_duration=2)
        self.assertEqual(result[0]['end'], .2)
        self.assertTrue(any('Subtitle 1' in w and 'minimum' in w for w in warnings))

    def test_missing_or_stale_word_times_preserve_text(self):
        text = 'One two three four five six seven eight nine ten eleven twelve'
        for words in ([], [dict(word='Old text', start=0, end=1)],
                      [dict(word=text, start=None, end=8)]):
            result, warnings = cues([segment(0, 8, text, words)], SubtitleOptions(10, 1, 1, 3), audio_duration=8)
            self.assertEqual(len(result), 1)
            self.assertEqual(normalized(result[0]['text']), text)
            self.assertEqual((result[0]['start'], result[0]['end']), (0, 8))
            self.assertTrue(any('maximum' in w for w in warnings))
            self.assertTrue(any('lines exceed' in w for w in warnings))
            self.assertTrue(any('word timing' in w for w in warnings))

    def test_long_hyphenated_word_is_not_split_or_lost(self):
        text = 'before extraordinarily-long-hyphenated-name after'
        result, warnings = cues([segment(0, 3, text)], SubtitleOptions(10, 1), audio_duration=3)
        self.assertEqual(normalized(result[0]['text']), text)
        self.assertTrue(any('longest line' in w for w in warnings))
        self.assertTrue(any('lines exceed' in w for w in warnings))

    def test_aligned_words_split_and_limits_checked(self):
        text = 'First. Second. Third.'
        words = [dict(word=w, start=i*2, end=i*2+1) for i,w in enumerate(text.split())]
        result, warnings = cues([segment(0, 5, text, words)], SubtitleOptions(10, 1, 1, 2), audio_duration=5)
        self.assertEqual(normalized(' '.join(c['text'] for c in result)), text)
        self.assertEqual(len(result), 3)
        self.assertEqual(warnings, [])
        # A single timed word cannot be split safely, even if too long in time.
        _, warnings = cues([segment(0, 8, 'word', [dict(word='word', start=0, end=8)])], audio_duration=8)
        self.assertTrue(any('maximum' in w for w in warnings))

    def test_overlap_partial_full_and_out_of_order_rejected(self):
        for intervals in (((0,2),(1,3)), ((0,3),(1,2)), ((2,3),(0,1))):
            with self.subTest(intervals=intervals), self.assertRaisesRegex(ValueError, 'Subtitle 2'):
                cues([segment(*times) for times in intervals], audio_duration=4)

    def test_audio_boundaries_and_invalid_duration(self):
        for duration in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                cues([segment(0, 1)], audio_duration=duration)
        with self.assertRaisesRegex(ValueError, 'beyond the recording'):
            cues([segment(0, 2)], audio_duration=1)
        with self.assertRaises(ValueError):
            cues([segment(-.1, 1)], audio_duration=1)

    def test_millisecond_rounding_and_audio_floor(self):
        options = SubtitleOptions(min_duration=.001)
        srt, _ = render_srt([segment(.0006, .0026)], options, audio_duration=.0026)
        self.assertIn('00:00:00,001 --> 00:00:00,002', srt)
        with self.assertRaisesRegex(ValueError, 'milliseconds'):
            cues([segment(.0011, .0014)], options, audio_duration=1)
        result, _ = cues([segment(0, 1.0004), segment(1.00049, 2)], options, audio_duration=2)
        self.assertEqual(result[0]['end'], result[1]['start'])

    def test_unknown_duration_and_localized_warnings(self):
        result, warnings = cues([segment(0, .1)])
        self.assertEqual(result[0]['end'], .1)
        self.assertTrue(any('unknown' in w for w in warnings))
        set_language('sk')
        try:
            _, warnings = cues([segment(0, .1)], audio_duration=.1)
            self.assertTrue(any('Titulok 1' in w and 'minimom' in w for w in warnings))
        finally:
            set_language('en')

    def test_project_uses_recording_duration_and_keeps_previous_export_on_error(self):
        with tempfile.TemporaryDirectory() as folder, Project(folder, create=True) as project:
            project.initialize('audio.wav', {}, {}, [], 1600)
            project.commit_chunk(0, [segment(0, .1)], 'sk')
            warnings = project.export(view='original')
            self.assertTrue(any('minimum' in w for w in warnings))
            original = (project.folder/'exporty'/'aktualny.partial.json').read_bytes()
            project.commit_chunk(1, [segment(.1, .2)], 'sk')
            with self.assertRaises(ValueError):
                project.export(view='original')
            self.assertEqual((project.folder/'exporty'/'aktualny.partial.json').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
