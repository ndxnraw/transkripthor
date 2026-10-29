"""Separate testing launcher. Never uses the stable application's profile."""
import multiprocessing
from pathlib import Path
import os
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    import argparse
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtCore import QUrl
    from prototype_qml.controller import Controller
    import prototype_qml
    from ndtranskripthor.core.i18n import set_language
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke-output',type=Path)
    parser.add_argument('--profile',type=Path,default=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'NDTranskripThor-QML-Testing')
    args=parser.parse_args()
    stable=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'LokalnyPrepis'
    if args.profile.resolve()==stable.resolve():raise SystemExit('Use a separate testing profile')
    set_language('sk');QQuickStyle.setStyle('Material')
    app=QApplication(sys.argv[:1]);backend=Controller(args.profile)
    engine=QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend',backend)
    engine.rootContext().setContextProperty('queueModel',backend.queue_model)
    engine.rootContext().setContextProperty('segmentModel',backend.segments)
    engine.load(QUrl.fromLocalFile(str(Path(prototype_qml.__file__).with_name('Main.qml'))))
    if not engine.rootObjects():backend.close();return 1
    try:
        if args.smoke_output:
            from prototype_qml.diagnostic import run
            run(app,engine,backend,args.smoke_output)
            return 0
        return app.exec()
    finally:
        import shiboken6
        shiboken6.delete(engine)
        backend.close()

if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
