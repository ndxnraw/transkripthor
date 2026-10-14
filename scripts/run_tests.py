"""All Windows regression tests; missing or skipped coverage is a failure."""
import faulthandler
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Run the required suite on Windows, not WSL/Linux.')
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
    faulthandler.dump_traceback_later(120, repeat=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test*.py')
    count = suite.countTestCases()
    print(f'Discovered {count} tests', flush=True)
    if count < 196:
        raise SystemExit('Regression coverage was lost (expected at least 196 tests).')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    faulthandler.cancel_dump_traceback_later()
    raise SystemExit(not result.wasSuccessful() or bool(result.skipped) or result.testsRun != count)
