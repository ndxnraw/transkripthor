"""Current documentation links and localized version/author information."""
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from ndtranskripthor.core.i18n import set_language
from ndtranskripthor.presentation.ui_layout import show_about
from ndtranskripthor.presentation.ui import AUTHOR
from version import DISPLAY_VERSION, VERSION

ROOT = Path(__file__).resolve().parents[1]

class InformationTest(unittest.TestCase):
    def test_about_uses_authoritative_version_and_exact_author_both_languages(self):
        try:
            for language in ('en', 'sk'):
                set_language(language)
                with patch('ndtranskripthor.presentation.ui_layout.messagebox.showinfo') as show:
                    show_about(None)
                body = show.call_args.args[1]
                for value in (DISPLAY_VERSION, VERSION, AUTHOR, 'TXT', 'SRT', 'VTT', 'DOCX', 'JSON'):
                    self.assertIn(value, body)
                self.assertTrue(body.endswith('Created by Daniel Návojský (ndxnraw) using Codex | 2026'))
        finally:
            set_language('en')

    def test_current_documentation_links_resolve(self):
        for name in ('README.md', 'docs/NAVOD.md', 'docs/DEVELOPMENT.md', 'docs/RELEASE-NOTES.md'):
            path = ROOT/name
            content = path.read_text(encoding='utf-8-sig')
            for target in re.findall(r'\]\(([^)]+)\)', content):
                if '://' not in target and not target.startswith('#'):
                    self.assertTrue((path.parent/target.split('#')[0]).exists(), (name,target))
            self.assertNotIn('outputs/zdroj', content)
            self.assertNotIn('release210', content)
