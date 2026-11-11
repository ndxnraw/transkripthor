"""Windows Qt Quick entry point; uses the existing profile and project formats."""
from pathlib import Path
import sys


def main():
    import argparse
    from PySide6.QtCore import QUrl, QTimer, qInstallMessageHandler
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from ndtranskripthor.core.ownership import profile_path, ProfileOwner, OwnershipError
    from ndtranskripthor.core.resources import resource_path
    from .controller import Controller
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',type=Path,default=profile_path())
    parser.add_argument('--smoke-output',type=Path)
    parser.add_argument('recordings',nargs='*')
    args=parser.parse_args()
    QQuickStyle.setStyle('Material')
    app=QApplication(sys.argv[:1])
    app.setApplicationName('ND TranskripThor')
    app.setOrganizationName('ND')
    app.setWindowIcon(QIcon(str(resource_path('assets/transkripthor.ico'))))
    try: backend=Controller(args.profile)
    except OwnershipError:
        if args.recordings: ProfileOwner.submit(args.profile,args.recordings)
        else: QMessageBox.information(None,'ND TranskripThor','Program s týmto profilom je už otvorený.')
        return 0
    engine=QQmlApplicationEngine()
    messages=[]
    engine.warnings.connect(lambda items:messages.extend(item.toString() for item in items))
    if args.smoke_output:
        args.smoke_output.mkdir(parents=True,exist_ok=True)
        def capture(kind,context,message):
            messages.append(message)
            with (args.smoke_output/'qml-messages.log').open('a',encoding='utf-8') as stream: stream.write(message+'\n')
        qInstallMessageHandler(capture)
    for name,obj in [('backend',backend),('queueModel',backend.queue_model),('segmentModel',backend.segments),('modelInventory',backend.model_rows)]:
        engine.rootContext().setContextProperty(name,obj)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
    if not engine.rootObjects(): backend.close(); return 1
    if args.recordings: backend.add_paths(args.recordings)
    try:
        if args.smoke_output:
            from .diagnostic import run
            return run(app,engine,backend,args.smoke_output,messages)
        return app.exec()
    finally:
        import shiboken6
        shiboken6.delete(engine)
        if backend.busy:
            backend.stop.set()
            while backend.busy:
                app.processEvents(); backend.poll()
        backend.close()
        qInstallMessageHandler(None)


if __name__=='__main__':
    raise SystemExit(main())
