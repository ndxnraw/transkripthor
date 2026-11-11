"""Production Qt Quick regressions; run separately from the Tk interpreter."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import patch
import shiboken6
from PySide6.QtCore import QUrl, QObject, Qt, QMetaObject
from PySide6.QtTest import QTest
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from ndtranskripthor.presentation.qml.controller import Controller
from ndtranskripthor.projects.project import Project, fingerprint
from ndtranskripthor.core.i18n import set_language

QQuickStyle.setStyle('Material')
APP = QApplication.instance() or QApplication([])


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Thor Qt č ')
        self.root = Path(self.temp.name).resolve()
        self.backend = Controller(self.root/'profil č')
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda items:self.warnings.extend(x.toString() for x in items))
        for name,obj in [('backend',self.backend),('queueModel',self.backend.queue_model),
                         ('segmentModel',self.backend.segments),('modelInventory',self.backend.model_rows)]:
            self.engine.rootContext().setContextProperty(name,obj)
        self.engine.load(QUrl.fromLocalFile(str(ROOT/'src/ndtranskripthor/presentation/qml/Main.qml')))
        self.assertTrue(self.engine.rootObjects(),self.warnings)
        self.window = self.engine.rootObjects()[0]
        APP.processEvents()

    def tearDown(self):
        if self.backend.busy: self.backend.cancel(); self.wait()
        self.window.hide()
        shiboken6.delete(self.engine)
        self.backend.close()
        self.temp.cleanup()
        set_language('en')

    def wait(self):
        deadline = time.monotonic()+45
        while self.backend.busy:
            APP.processEvents(); time.sleep(.005)
            self.assertLess(time.monotonic(),deadline,self.backend.status)
        APP.processEvents()

    def project(self, name='projekt č', count=3):
        audio = self.root/(name+'.wav')
        with wave.open(str(audio),'wb') as out:
            out.setparams((1,2,16000,0,'NONE','not compressed')); out.writeframes(b'\0\0'*16000*6)
        folder = self.root/name
        with Project(folder,create=True) as project:
            project.initialize(audio,fingerprint(audio),{},[],96000)
            project.commit_chunk(0,[dict(start=i/count*5,end=(i+1)/count*5,text=f'Úsek {i} č ž',words=[]) for i in range(count)],'sk')
            project.finish()
        return folder,audio

    def opened(self):
        folder,audio = self.project()
        self.backend.open_project(folder); self.wait()
        self.assertEqual(self.backend.view,'editor')
        return folder,audio

    def test_home_has_no_tabs_and_direct_choices(self):
        self.assertEqual(self.backend.view,'home')
        self.assertTrue(self.window.findChild(QObject,'addFilesButton').property('visible'))
        self.assertIsNone(self.window.findChild(QObject,'workspaceTabs'))
        self.assertIsNotNone(self.window.findChild(QObject,'qualityChoice'))
        for name,key in [('languageChoice','language'),('qualityChoice','model')]:
            choice=self.window.findChild(QObject,name)
            self.assertTrue(choice.property('displayText'),(name,choice.property('count'),choice.property('currentIndex'),self.backend.settings[key]))
        self.assertNotIn('tkinter',sys.modules)
        self.assertEqual(self.warnings,[])

    def test_queue_persistence_reorder_duplicates_and_remove_preserves_audio(self):
        _,one=self.project('prvá'); _,two=self.project('druhá')
        self.assertTrue(self.backend.add_paths([one,two,one,self.root/'missing']))
        self.assertEqual(self.backend.queueCount,2)
        self.backend.move(0,1)
        self.assertEqual(self.backend.store.queue()[0]['source'],str(two))
        self.backend.remove(1)
        self.assertEqual(self.backend.queueCount,1)
        self.assertTrue(one.exists())

    def test_local_url_drop_and_remote_url_rejected(self):
        _,audio=self.project()
        self.assertFalse(self.backend.add_urls([QUrl('https://example.com/file.wav')]))
        self.assertTrue(self.backend.add_urls([QUrl.fromLocalFile(str(audio))]))
        self.assertEqual(self.backend.queueCount,1)

    def test_real_project_edit_save_original_is_immutable(self):
        folder,_=self.opened()
        self.assertEqual(Path(self.backend.folder),folder)
        self.backend.edit_active('Zmenené č Ž 日本語')
        self.assertTrue(self.backend.dirty)
        self.backend.save(); self.wait()
        self.assertFalse(self.backend.dirty,self.backend.status)
        with Project(folder) as project:
            self.assertEqual(project.segments()[0]['text'],'Zmenené č Ž 日本語')
            self.assertEqual(project.segments("original")[0]['text'],'Úsek 0 č ž')

    def test_user_typing_selection_and_keyboard_save(self):
        self.opened()
        editor=self.window.findChild(QObject,'transcriptEditor')
        self.window.requestActivate(); QTest.qWait(80)
        QMetaObject.invokeMethod(editor,'forceActiveFocus')
        QTest.keyClick(self.window,Qt.Key_End)
        QTest.keyClick(self.window,Qt.Key_Space); QTest.keyClick(self.window,Qt.Key_X)
        APP.processEvents()
        self.assertIn(' x',self.backend.activeSegment['text'].lower())
        edited=self.backend.activeSegment['text']
        self.backend.select(1); APP.processEvents()
        self.assertEqual(self.backend.segments.rows[0]['text'],edited)
        self.assertEqual(self.backend.activeSegment['text'],'Úsek 1 č ž')
        QTest.keyClick(self.window,Qt.Key_S,Qt.ControlModifier); self.wait()
        self.assertFalse(self.backend.dirty)

    def test_undo_redo_and_back_preserve_unsaved(self):
        self.opened(); self.backend.edit_active('Nové')
        self.backend.show('home'); self.backend.show('editor')
        self.assertEqual(self.backend.activeSegment['text'],'Nové')
        self.backend.undo(); self.assertEqual(self.backend.activeSegment['text'],'Úsek 0 č ž')
        self.backend.redo(); self.assertEqual(self.backend.activeSegment['text'],'Nové')

    def test_unicode_search_returns_qml_utf16_offsets(self):
        self.opened(); self.backend.edit_active('😀 Ahoj č Č')
        self.backend.search('č',False)
        self.assertEqual((self.backend.selectionStart,self.backend.selectionEnd),(8,9))
        self.backend.search('č',False)
        self.assertEqual((self.backend.selectionStart,self.backend.selectionEnd),(10,11))

    def test_close_cancel_discard_and_save(self):
        folder,_=self.opened(); closed=[]
        self.backend.closeReady.connect(lambda:closed.append(True))
        self.backend.edit_active('Zachovať')
        self.assertFalse(self.backend.request_close())
        self.backend.resolve_dirty('cancel')
        self.assertTrue(self.backend.dirty); self.assertEqual(closed,[])
        self.backend.request_close(); self.backend.resolve_dirty('save'); self.wait()
        self.assertEqual(closed,[True])
        with Project(folder) as project:self.assertEqual(project.segments()[0]['text'],'Zachovať')
        self.backend.edit_active('Zahodiť'); self.backend.request_close(); self.backend.resolve_dirty('discard')
        self.assertFalse(self.backend.dirty)
        self.assertEqual(self.backend.activeSegment['text'],'Zachovať')

    def test_project_switch_waits_for_dirty_decision(self):
        folder,_=self.opened(); second,_=self.project('iný projekt')
        self.backend.edit_active('Rozpracované'); self.backend.open_project(second)
        self.assertEqual(Path(self.backend.folder),folder)
        self.backend.resolve_dirty('cancel'); self.assertTrue(self.backend.dirty)
        self.backend.open_project(second); self.backend.resolve_dirty('save'); self.wait()
        self.assertEqual(Path(self.backend.folder),second)
        with Project(folder) as project:self.assertEqual(project.segments()[0]['text'],'Rozpracované')

    def test_edits_during_save_remain_dirty_and_second_save_persists(self):
        folder,_=self.opened(); self.backend.edit_active('Prvá verzia')
        entered,release=threading.Event(),threading.Event()
        from ndtranskripthor.application.project_io import perform_project_io
        def blocked(*args,**kwargs):
            entered.set(); release.wait(10); perform_project_io(*args,**kwargs)
        with patch('ndtranskripthor.presentation.qml.controller.perform_project_io',blocked):
            self.backend.save(); self.assertTrue(entered.wait(3))
            self.backend.edit_active('Druhá verzia'); release.set(); self.wait()
        self.assertTrue(self.backend.dirty)
        with Project(folder) as project:self.assertEqual(project.segments()[0]['text'],'Prvá verzia')
        self.backend.save(); self.wait(); self.assertFalse(self.backend.dirty)
        with Project(folder) as project:self.assertEqual(project.segments()[0]['text'],'Druhá verzia')

    def test_failed_save_does_not_close_or_lose_changes(self):
        self.opened(); closed=[]; self.backend.closeReady.connect(lambda:closed.append(True))
        self.backend.edit_active('Dôležité'); self.backend.request_close()
        with patch('ndtranskripthor.presentation.qml.controller.perform_project_io',side_effect=OSError('disk full')):
            self.backend.resolve_dirty('save'); self.wait()
        self.assertEqual(closed,[]); self.assertTrue(self.backend.dirty)
        self.assertEqual(self.backend.activeSegment['text'],'Dôležité')

    def test_split_merge_timing_undo_and_save(self):
        folder,_=self.opened(); self.backend.structure('split',4,.8,0)
        self.assertEqual(self.backend.segmentCount,4,self.backend.status)
        identifiers=[row['id'] for row in self.backend.segments.rows]
        self.assertEqual(len(set(identifiers)),4)
        self.backend.structure('merge',0,0,0); self.assertEqual(self.backend.segmentCount,3)
        self.backend.undo(); self.assertEqual(self.backend.segmentCount,4)
        self.backend.redo(); self.assertEqual(self.backend.segmentCount,3)
        self.backend.structure('times',0,.1,1.6)
        self.backend.save(); self.wait()
        with Project(folder) as project:self.assertEqual(project.segments()[0]['start'],.1)

    def test_speaker_rename_and_subtitle_options(self):
        folder,_=self.opened(); self.backend.speaker('Jana',True)
        self.assertTrue(all(row['speaker']=='Jana' for row in self.backend.segments.rows))
        self.backend.subtitles(36,2,.7,7.)
        self.backend.save(); self.wait()
        with Project(folder) as project:
            self.assertEqual(project.subtitle_options().characters,36)
            self.assertTrue(all(row['speaker']=='Jana' for row in project.segments()))

    def test_export_all_formats_saved_and_original(self):
        folder,_=self.opened(); self.backend.edit_active('Upravený prepis'); self.backend.save(); self.wait()
        self.backend.export_files(['txt','srt','vtt','docx','json'],True,True,str(self.backend.revisions[-1])); self.wait()
        from ndtranskripthor.exports.export_formats import latest_bundle
        bundle=latest_bundle(folder)
        self.assertEqual({p.suffix for p in bundle.iterdir() if p.suffix!='.json'},{'.txt','.srt','.vtt','.docx'})
        self.assertTrue(any('Upravený prepis' in p.read_text(encoding='utf-8-sig') for p in bundle.glob('*.txt')))
        self.backend.export_files(['txt'],False,False,'original'); self.wait()
        self.assertTrue(any('Úsek 0' in p.read_text(encoding='utf-8-sig') for p in latest_bundle(folder).glob('*.txt')))

    def test_missing_audio_still_edits_and_saves(self):
        folder,audio=self.project(); audio.rename(audio.with_suffix('.moved'))
        self.backend.open_project(folder); self.wait()
        self.assertFalse(self.backend.audioReady); self.assertTrue(self.backend.editable)
        self.backend.edit_active('Text bez zvuku'); self.backend.save(); self.wait()
        with Project(folder) as project:self.assertEqual(project.segments()[0]['text'],'Text bez zvuku')

    def test_seek_rate_without_playing(self):
        self.opened(); self.assertTrue(self.backend.audioReady,self.backend.status)
        self.backend.seek(2.5); self.assertAlmostEqual(self.backend.position,2.5)
        self.assertFalse(self.backend.playing)
        self.backend.audio_devices(); self.backend.configure_audio(1.5,0)
        self.assertEqual(self.backend.playbackRate,1.5)

    def test_offline_start_offers_download_in_place(self):
        _,audio=self.project(); self.backend.add_paths([audio]); self.backend.option('offline',True)
        self.backend.start(); self.assertEqual(self.backend.question[0],'online')
        self.assertEqual(self.backend.view,'home'); self.assertFalse(self.backend.busy)
        self.backend.answer('online',False); self.assertFalse(self.backend.busy)

    def test_real_asr_child_offline_failure_acknowledges_queue(self):
        _,audio=self.project(); self.backend.add_paths([audio]); self.backend.option('offline',True)
        # Bypass only the friendly preflight; run the real isolated ASR worker.
        with patch('ndtranskripthor.models.model_catalog.cached_path',return_value=Path('absent')):
            self.backend.start(); self.wait()
        self.assertEqual(self.backend.store.queue()[0]['state'],'failed',self.backend.status)
        self.assertTrue(self.backend.store.queue()[0]['error'])

    def test_models_inventory_and_diagnostic_privacy(self):
        self.backend.show('models'); self.wait(); self.assertGreater(self.backend.model_rows.rowCount(),0)
        self.backend.inspect_data(); self.wait()
        self.assertTrue(self.backend.diagnostic); self.assertFalse(self.backend.diagnosticPreviewed)
        self.assertEqual(self.backend.diagnosticPreview,'')
        self.backend.preview_diagnostic(); self.assertTrue(self.backend.diagnosticPreviewed)
        self.assertIn('diagnostics.json',self.backend.diagnosticPreview)

    def test_themes_high_contrast_geometry_and_accessibility(self):
        self.opened()
        for theme in ('light','dark'):
            self.backend.option('theme',theme)
            for width,height in ((560,480),(1120,800)):
                self.window.resize(width,height); APP.processEvents()
                self.assertTrue(self.window.findChild(QObject,'saveButton').property('visible'))
                self.assertGreater(self.window.findChild(QObject,'transcriptEditor').property('width'),100)
        system=dict(bg='#000000',card='#000000',field='#000000',text='#ffffff',muted='#ffffff',border='#ffffff',blue='#ffff00',accent_text='#000000')
        with patch('ndtranskripthor.presentation.qml.controller.high_contrast_palette',return_value=system):
            self.backend.poll(); self.assertTrue(self.backend.colors['contrast']); APP.processEvents()
        interface=QAccessible.queryAccessibleInterface(self.window.findChild(QObject,'transcriptEditor'))
        self.assertEqual(interface.role(),QAccessible.Role.EditableText)
        self.assertTrue(interface.text(QAccessible.Name))
        self.assertEqual(self.warnings,[])


if __name__=='__main__':
    unittest.main(verbosity=2)
