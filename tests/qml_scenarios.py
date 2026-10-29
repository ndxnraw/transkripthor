"""Optional QML integration scenarios, invoked explicitly by test-qml.ps1."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import tempfile
import time
import unittest
import wave
import shiboken6
from PySide6.QtCore import QUrl, QObject, qInstallMessageHandler, Qt, QMetaObject, QPoint
from PySide6.QtTest import QTest
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from prototype_qml.controller import Controller
from ndtranskripthor.projects.project import Project, fingerprint

QQuickStyle.setStyle('Material')
APP = QApplication.instance() or QApplication([])

class Scenarios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Thor QML č ')
        self.root = Path(self.temp.name)
        self.backend = Controller(self.root/'profile')
        self.engine = QQmlApplicationEngine()
        self.warnings=[]
        self.engine.warnings.connect(lambda items:self.warnings.extend(x.toString() for x in items))
        for name,obj in [('backend',self.backend),('queueModel',self.backend.queue_model),('segmentModel',self.backend.segments)]:
            self.engine.rootContext().setContextProperty(name,obj)
        self.engine.load(QUrl.fromLocalFile(str(ROOT/'src/prototype_qml/Main.qml')))
        self.assertTrue(self.engine.rootObjects(),self.warnings)
        self.window=self.engine.rootObjects()[0]
        self.window.setScreen(APP.primaryScreen())
        self.window.setPosition(APP.primaryScreen().availableGeometry().topLeft()+QPoint(10,10))
        APP.processEvents()
    def tearDown(self):
        self.window.hide()
        shiboken6.delete(self.engine)
        self.backend.close()
        self.temp.cleanup()
    def wait(self):
        deadline=time.monotonic()+30
        while self.backend.busy:
            APP.processEvents();time.sleep(.005)
            self.assertLess(time.monotonic(),deadline,self.backend.status)
        APP.processEvents()
    def project(self,count=3):
        audio=self.root/'Zvuk č ž.wav'
        with wave.open(str(audio),'wb') as out:
            out.setparams((1,2,16000,0,'NONE','not compressed'));out.writeframes(b'\0\0'*16000*5)
        folder=self.root/'original'
        with Project(folder,create=True) as project:
            project.initialize(audio,fingerprint(audio),{},[],80000)
            project.commit_chunk(0,[dict(start=i/count*4,end=(i+1)/count*4,text=f'Úsek {i} č ž',words=[]) for i in range(count)],'sk')
            project.finish()
        return folder,audio
    def test_queue_persistence_and_busy(self):
        _,audio=self.project()
        self.backend.add_paths([audio,audio,self.root/'missing'])
        self.assertEqual(len(self.backend.store.queue()),1)
        self.backend._busy=True;self.backend.remove(0)
        self.assertEqual(len(self.backend.store.queue()),1)
        self.backend._busy=False;self.backend.remove(0)
        self.assertEqual(self.backend.store.queue(),[]);self.assertTrue(audio.exists())
    def test_edit_save_reopen_original_unchanged(self):
        folder,audio=self.project()
        self.backend.open_project(folder);self.wait()
        self.assertEqual(self.backend.duration,5)
        self.backend.edit(0,'Zmenené č Ž 日本語');self.assertTrue(self.backend.dirty)
        self.assertFalse(self.backend.can_close())
        self.backend.save();self.wait();self.assertFalse(self.backend.dirty,self.backend.status)
        with Project(self.backend.folder) as saved:self.assertEqual(saved.segments()[0]['text'],'Zmenené č Ž 日本語')
        with Project(folder) as original:self.assertEqual(original.segments()[0]['text'],'Úsek 0 č ž')
        self.backend.open_project(self.backend.folder);self.wait()
        self.assertEqual(self.backend.segment_text(0),'Zmenené č Ž 日本語')
    def test_missing_audio_and_large_model(self):
        folder,audio=self.project(10000)
        audio.rename(audio.with_suffix('.moved'))
        self.backend.open_project(folder);self.wait()
        self.assertEqual(self.backend.segments.rowCount(),10000)
        self.assertEqual(self.backend.duration,0)
        self.assertIn('bez prehrávania',self.backend.status)
        self.backend.edit(9999,'Posledný');self.backend.save();self.wait()
        with Project(self.backend.folder) as saved:self.assertEqual(saved.segments()[-1]['text'],'Posledný')
    def test_themes_geometry_and_navigation(self):
        folder,_=self.project()
        self.backend.open_project(folder);self.wait()
        for dark in (True,False):
            self.window.setProperty('dark',dark)
            for width,height in ((480,420),(1000,720)):
                self.window.resize(width,height);APP.processEvents()
                save=self.window.findChild(QObject,'saveButton')
                self.assertGreater(save.property('width'),40)
                self.assertTrue(save.property('visible'))
                if width==480:
                    scroll=self.window.findChild(QObject,'queueScroll')
                    self.assertGreater(scroll.property('contentHeight'),scroll.property('availableHeight'))
        self.assertEqual(self.warnings,[])
    def test_paused_seek_uses_original_timeline(self):
        folder,_=self.project()
        self.backend.open_project(folder);self.wait()
        self.backend.pause();self.backend.seek(2.5)
        self.assertAlmostEqual(self.backend.position,2.5)
        self.assertFalse(self.backend.player.playing)
    def test_keyboard_edit_selection_and_save(self):
        folder,_=self.project()
        self.backend.open_project(folder);self.wait()
        self.window.findChild(QObject,'workspaceTabs').setProperty('currentIndex',1)
        listing=self.window.findChild(QObject,'segmentList')
        editor=self.window.findChild(QObject,'transcriptEditor')
        listing.setProperty('currentIndex',0);APP.processEvents()
        QMetaObject.invokeMethod(editor,'forceActiveFocus')
        QTest.keyClick(self.window,Qt.Key_End)
        QTest.keyClick(self.window,Qt.Key_Space)
        QTest.keyClick(self.window,Qt.Key_X)
        APP.processEvents()
        self.assertIn(' x',self.backend.segment_text(0).lower())
        self.assertFalse(self.backend.player.playing)
        edited=self.backend.segment_text(0)
        listing.setProperty('currentIndex',1);APP.processEvents()
        self.assertEqual(self.backend.segment_text(0),edited)
        self.assertEqual(self.backend.segment_text(1),'Úsek 1 č ž')
        QTest.keyClick(self.window,Qt.Key_S,Qt.ControlModifier);self.wait()
        self.assertFalse(self.backend.dirty)
    def test_process_offline_failure_returns_control(self):
        _,audio=self.project();self.backend.add_paths([audio])
        self.backend.start('sk','tiny',True);self.wait()
        self.assertFalse(self.backend.busy)
        self.assertEqual(self.backend.store.queue()[0]['state'],'failed')
        self.assertTrue(self.backend.store.queue()[0]['error'])
    def test_accessible_editor_role_and_name(self):
        self.window.findChild(QObject,'workspaceTabs').setProperty('currentIndex',1)
        APP.processEvents()
        interface=QAccessible.queryAccessibleInterface(self.window.findChild(QObject,'transcriptEditor'))
        self.assertTrue(interface.isValid())
        self.assertEqual(interface.role(),QAccessible.Role.EditableText)
        self.assertEqual(interface.text(QAccessible.Name),'Text vybraného úseku')

if __name__=='__main__':
    qInstallMessageHandler(lambda kind,context,message: print(message, file=sys.stderr))
    unittest.main()
