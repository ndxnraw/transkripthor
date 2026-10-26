import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from project import Project
from segment_edit import split, merge, validate
from export_formats import ExportOptions, FORMATS, export_project, latest_bundle, render, docx
from subtitles import SubtitleOptions
import test_editor_speakers
from test_io_support import save_editor, wait_io


class SegmentDataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'projekt č 日本'
        self.rows = [dict(start=0, end=2, text='Žluťoučký 🦊 & <hlas>\n 日本', speaker='Eva', words=[]),
                     dict(start=3, end=4, text='Ďalší úsek.', speaker='Eva', words=[])]
        with Project(self.folder, create=True) as project:
            project.initialize('audio.wav', {}, {}, [], 160000)
            project.commit_chunk(0, self.rows, 'sk')
            project.finish()

    def test_structural_revision_backup_original_and_reopen(self):
        with Project(self.folder) as p:
            rows = p.segments()
            baseline = p.edit(rows)
            left, right = split(rows[0], 10, 1, 2)
            revision = p.edit([left,right], structural=True)
            self.assertEqual([s['id'] for s in p.segments('revision', revision)], [0,2,1])
            self.assertEqual(p.segments('revision', baseline), rows)
            self.assertEqual(p.segments('original'), rows)
            merged = merge(left, right)
            final = p.edit([merged, dict(id=2, deleted=True)], structural=True)
            self.assertEqual(len(p.segments('revision', final)), 2)
            self.assertEqual(p.db.execute('SELECT version FROM transcript_storage').fetchone(), (2,))
        self.assertEqual(len(list(self.folder.glob('zaloha-pred-upravou-usekov-*'))), 1)
        with Project(self.folder) as p:
            self.assertEqual(len(p.segments()), 2)
            self.assertEqual(p.segments('original')[0]['text'], rows[0]['text'])
            self.assertEqual(len(p.segments('revision', revision)), 3)

    def test_invalid_times_rollback_and_clear_word_alignment(self):
        with Project(self.folder) as p:
            rows = p.segments()
            for start,end in ((-1,1),(1,1),(0,11),(0,float('nan')),(0,3.1),(0,.0001)):
                with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                    p.edit([dict(rows[0],start=start,end=end)], structural=True)
                self.assertEqual(p.segments(), rows)
            p.edit([dict(rows[0],start=.1,words=[dict(start=0,end=1,word='fake')])], structural=True)
            self.assertEqual(p.segments()[0]['words'], [])
            self.assertEqual(p.segments('original'), rows)

    def test_split_text_unicode_exact_and_speaker_conflict(self):
        row = dict(self.rows[0], id=0)
        for offset in range(1,len(row['text'])):
            left,right = split(row,offset,1,2)
            self.assertEqual(left['text']+right['text'],row['text'])
        with self.assertRaises(ValueError):
            merge(row,dict(row,speaker='Other'))
        with self.assertRaises(ValueError):
            split(row,0,1,2)
        with self.assertRaises(ValueError):
            validate([row],None)

    def test_all_formats_unicode_explicit_options_and_package_validity(self):
        with Project(self.folder) as p:
            revision = p.edit(p.segments())
            directory, warnings = export_project(p, ExportOptions(FORMATS,True,True), view='revision', revision=revision)
            self.assertEqual(latest_bundle(self.folder), directory)
            self.assertEqual(len(list(directory.iterdir())),5)
            data=json.loads((directory/'prepis.json').read_text(encoding='utf-8'))
            self.assertEqual(data['segments'][0]['text'],self.rows[0]['text'])
            self.assertEqual(data['segments'][0]['speaker'],'Eva')
            self.assertEqual(data['revision'],revision)
            self.assertIn('00:00:00,000', (directory/'prepis.txt').read_text(encoding='utf-8-sig'))
            vtt=(directory/'titulky.vtt').read_text(encoding='utf-8')
            self.assertTrue(vtt.startswith('WEBVTT\n\n'))
            self.assertIn('00:00:00.000 --> 00:00:02.000',vtt)
            self.assertIn('&lt;hlas&gt;',vtt)
            self.assertIn('00:00:00,000 --> 00:00:02,000',(directory/'titulky.srt').read_text(encoding='utf-8-sig'))
            with zipfile.ZipFile(directory/'prepis.docx') as z:
                self.assertIsNone(z.testzip())
                for name in ('[Content_Types].xml','_rels/.rels','word/document.xml'):
                    ET.fromstring(z.read(name))
                text=''.join(ET.fromstring(z.read('word/document.xml')).itertext())
                self.assertIn('Žluťoučký 🦊 & <hlas>',text)
            files,_=render(p.segments(),ExportOptions(('txt','json','docx')),SubtitleOptions(),10,{})
            plain=json.loads(files['prepis.json'])['segments'][0]
            self.assertNotIn('start',plain); self.assertNotIn('speaker',plain)
            self.assertEqual(plain['text'],self.rows[0]['text'])
            self.assertEqual(files['prepis.txt'].decode('utf-8-sig'), '\n'.join(r['text'] for r in self.rows)+'\n')

    def test_failed_bundle_never_replaces_previous_and_export_does_not_edit(self):
        with Project(self.folder) as p:
            revision=p.edit(p.segments())
            directory,_=export_project(p,ExportOptions(),view='revision',revision=revision)
            before=p.segments('revision',revision)
            with patch('os.fsync',side_effect=OSError('disk full')),self.assertRaises(OSError):
                export_project(p,ExportOptions(FORMATS),view='original')
            self.assertEqual(latest_bundle(self.folder),directory)
            self.assertEqual(p.segments('revision',revision),before)
            self.assertEqual(p.segments('original'),before)
        with self.assertRaises(ValueError):
            docx(['bad\x00text'])


class SegmentEditorTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_split_merge_times_undo_save_reopen_and_no_implicit_export(self):
        from editor import Editor
        e=self.editor
        with Project(self.folder) as p:
            p.finish()
        e.structure_ready=True
        self.select(0)
        text='Český slovenský 日本 🦊'
        e.text.delete('1.0','end'); e.text.insert('1.0',text)
        e.change_structure('split',offset=6,seconds=.5)
        self.assertEqual(len(e.segments),46)
        self.assertEqual(e.segments[0]['text']+e.segments[1]['text'],text)
        e.undo(); self.assertEqual(len(e.segments),45)
        e.redo(); self.assertEqual(len(e.segments),46)
        self.assertTrue(save_editor(e))
        self.assertFalse((self.folder/'exporty').exists())
        self.assertFalse(e.dirty)
        e.change_structure('merge')
        self.assertEqual(len(e.segments),45)
        e.change_structure('times',start=.1,end=.9)
        self.assertEqual(e.segments[0]['words'],[])
        self.assertTrue(save_editor(e))
        e.undo(); self.assertTrue(e.dirty)
        e.redo(); self.assertFalse(e.dirty)
        with Project(self.folder) as p:
            revision=p.get('editor_export')['revision']
            directory,warnings=export_project(p,ExportOptions(('srt','vtt')),view='revision',revision=revision)
            self.assertIn('00:00:00,100 --> 00:00:00,900',(directory/'titulky.srt').read_text(encoding='utf-8-sig'))
            self.assertTrue(warnings)
        e.player.audio=None; self.assertTrue(e.close())
        reopened=Editor(self.app,self.folder,parent=self.app.editor_page)
        self.assertEqual(reopened.segments[0]['text'],text)
        self.assertEqual((reopened.segments[0]['start'],reopened.segments[0]['end']),(.1,.9))
        self.assertEqual(len(reopened.segments),45)
        reopened.close()

    def test_incomplete_or_inflight_structure_is_refused(self):
        e=self.editor; self.select(0)
        with self.assertRaises(ValueError):
            e.change_structure('split',offset=2,seconds=.5)
        e.structure_ready=True; e.speaker_busy=True
        with self.assertRaises(ValueError):
            e.change_structure('merge')
        e.speaker_busy=False
        self.assertEqual(len(e.segments),45)

    def test_export_dialog_uses_saved_revision_and_explicit_format_choices(self):
        import tkinter as tk
        from tkinter import ttk
        e=self.editor; self.select(0)
        e.text.insert('end',' Čerstvé 日本')
        e.export_dialog()
        self.assertIn('Save changes',e.status.get())
        self.assertTrue(save_editor(e))
        e.export_dialog()
        window=next(w for w in e.window.winfo_children() if isinstance(w,tk.Toplevel))
        widgets=window.winfo_children()[0].winfo_children()
        for widget in widgets:
            if isinstance(widget,ttk.Checkbutton) and widget.cget('text') in ('VTT','DOCX','JSON','Include speaker labels','Include times in TXT, DOCX and JSON'):
                widget.invoke()
        next(w for w in widgets if isinstance(w,ttk.Button)).invoke()
        wait_io(e)
        self.assertTrue(e.io_success)
        data=json.loads((latest_bundle(self.folder)/'prepis.json').read_text(encoding='utf-8'))
        self.assertEqual(data['view'],'revision')
        self.assertIn('Čerstvé 日本',data['segments'][0]['text'])
        self.assertIn('start',data['segments'][0])
        self.assertIn('speaker',data['segments'][0])
        self.assertFalse(e.dirty)

    def test_prerelease_label_keeps_numeric_windows_identity(self):
        import version
        self.assertEqual(version.DISPLAY_VERSION,'Pre-release')
        self.assertIn('Pre-release',self.app.version_label.cget('text'))
        self.assertEqual(version.WINDOWS_VERSION,(2,1,3,1))
