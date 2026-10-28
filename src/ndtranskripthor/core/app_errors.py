"""Stable error categories shared by workers and UI; no translated matching."""
import errno
import re
from ndtranskripthor.core.i18n import tr

CATEGORIES = ('input', 'disk', 'permission', 'memory', 'gpu', 'model', 'network', 'conflict', 'unknown')


class ProjectConflict(ValueError):
    pass


class CategorizedError(RuntimeError):
    def __init__(self, category, message):
        super().__init__(message)
        self.category = category


def classify(exc, context='unknown'):
    chain, seen = [], set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    category = 'gpu' if any(type(error).__name__ == 'GPUError' for error in chain) else None
    for error in chain:
        if category:
            break
        name = type(error).__name__
        number = getattr(error, 'errno', None)
        win = getattr(error, 'winerror', None)
        code = getattr(error, 'sqlite_errorcode', 0) & 255
        if name == 'GPUError':
            category = 'gpu'
        elif isinstance(error, ProjectConflict) or name == 'OwnershipError' or code in (5, 6):
            category = 'conflict'
        elif isinstance(error, PermissionError) or number in (errno.EACCES, errno.EPERM, errno.EROFS) or win in (5, 32, 33):
            category = 'permission'
        elif number in (errno.ENOSPC, errno.EDQUOT, errno.EIO) or win in (39, 112) or code in (10, 13):
            category = 'disk'
        elif isinstance(error, MemoryError) or number == errno.ENOMEM or win in (8, 14, 1455) or code == 7:
            category = 'memory'
        elif isinstance(error, RuntimeError) and any(word in str(error).lower() for word in ('out of memory', 'cannot allocate memory', 'not enough memory')):
            category = 'memory'
        elif isinstance(error, (ConnectionError, TimeoutError)) or type(error).__module__.startswith(('requests.', 'urllib3.', 'httpx.')):
            category = 'network'
        elif isinstance(error, FileNotFoundError):
            category = 'model' if context == 'model' else 'input'
        elif isinstance(error, CategorizedError):
            category = error.category
        if category:
            break
    category = category or (context if context in CATEGORIES else 'unknown')
    details = '\n'.join(f'{type(error).__name__}: {error}' for error in chain)
    # Keep technical causes, never credentials or signed download URLs.
    details = re.sub(r'https?://\S+', '[URL]', details)
    details = re.sub(r'\bhf_[A-Za-z0-9]+', '[TOKEN]', details)
    details = re.sub(r'(?i)(authorization|token|password|secret)\s*[:=]\s*\S+', r'\1=[REDACTED]', details)
    return dict(category=category, details=details)


def explanation(issue):
    category = issue.get('category', 'unknown')
    if category not in CATEGORIES:
        category = 'unknown'
    return tr('error.'+category) + '\n' + tr('error.action.'+category)
