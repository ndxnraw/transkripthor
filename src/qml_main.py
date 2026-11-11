"""Qt application launcher with frozen Windows multiprocessing support."""
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    from ndtranskripthor.presentation.qml.main import main
    raise SystemExit(main())
