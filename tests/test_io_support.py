"""Wait for real background writes while continuing to dispatch Tk events."""
import time


def wait_io(editor, timeout=30):
    deadline = time.monotonic() + timeout
    while editor.io_busy:
        editor.app.root.update()
        if time.monotonic() > deadline:
            raise AssertionError('Background save/export timed out')
        time.sleep(.005)


def save_editor(editor):
    if not editor.save():
        return False
    wait_io(editor)
    return editor.io_saved


def export_editor(editor):
    if not editor.retry_export():
        return False
    wait_io(editor)
    return editor.io_success
