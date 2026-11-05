"""Isolated, model-free comparison of real Tk and QML windows (not ASR speed)."""
import time
START=time.perf_counter()
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak','working','paged_peak','paged','nonpaged_peak','nonpaged','pagefile','pagefile_peak','private')]
    value=Counters();value.cb=ctypes.sizeof(value)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'working_mib':round(value.working/2**20,2),'private_mib':round(value.private/2**20,2)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('ui',choices=['tk','qml']);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='Thor compare ') as folder:
        if args.ui=='qml':
            from PySide6.QtWidgets import QApplication
            from PySide6.QtQml import QQmlApplicationEngine
            from PySide6.QtCore import QUrl,QObject,QPointF,QPoint
            from PySide6.QtQuickControls2 import QQuickStyle
            from prototype_qml.controller import Controller
            import shiboken6
            QQuickStyle.setStyle('Material');app=QApplication([]);backend=Controller(Path(folder))
            engine=QQmlApplicationEngine()
            for name,obj in [('backend',backend),('queueModel',backend.queue_model),('segmentModel',backend.segments)]:engine.rootContext().setContextProperty(name,obj)
            warnings=[];engine.warnings.connect(lambda items:warnings.extend(x.toString() for x in items))
            engine.load(QUrl.fromLocalFile(str(ROOT/'src/prototype_qml/Main.qml')))
            if not engine.rootObjects():raise RuntimeError(warnings)
            window=engine.rootObjects()[0];pump=app.processEvents
            window.setScreen(app.primaryScreen())
            window.setPosition(app.primaryScreen().availableGeometry().topLeft()+QPoint(10,10))
            pump()
            startup=time.perf_counter()-START
            pixel_ratio=window.devicePixelRatio()
            for dark in (True,False):
                window.setProperty('dark',dark)
                for width,height in ((480,420),(1000,720)):
                    window.resize(width,height)
                    until=time.monotonic()+.25
                    while time.monotonic()<until:pump();time.sleep(.005)
                    image=window.grabWindow();assert not image.isNull()
                    image.save(str(args.output/f'qml-{os.environ.get("QT_SCALE_FACTOR","1")}-{dark}-{width}.png'))
                    button=window.findChild(QObject,'saveButton')
                    point=button.mapToScene(QPointF(0,0))
                    assert point.y()+button.height()<=window.height()+1,(point.y(),button.height(),window.height())
            assert not warnings,warnings
            def cleanup():
                window.hide();shiboken6.delete(engine);backend.close()
        else:
            import tkinter as tk
            from ndtranskripthor.presentation.prepis import App
            root=tk.Tk();backend=App(root,Path(folder));pump=root.update;pump()
            startup=time.perf_counter()-START
            pixel_ratio=float(root.tk.call('tk','scaling'))*72/96
            def cleanup():root.destroy()
        gaps=[];previous=time.perf_counter();until=previous+2
        while time.perf_counter()<until:
            pump();time.sleep(.01);now=time.perf_counter();gaps.append((now-previous)*1000);previous=now
        report=dict(ui=args.ui,startup_seconds=round(startup,3),scale=os.environ.get('QT_SCALE_FACTOR','1'),device_pixel_ratio=pixel_ratio,
                    memory=memory(),idle_pump_gap_max_ms=round(max(gaps),2),idle_pump_gap_p95_ms=round(sorted(gaps)[int(.95*len(gaps))],2))
        cleanup();(args.output/(args.ui+'-metrics.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
