"""Application UI translations. Never use translated strings as persisted IDs.

The active language is selected once at startup. A settings change only updates
the next-start preference; workers and open editors retain this session's locale.
"""
import json
import logging
import os
from pathlib import Path
from string import Formatter

LANGUAGES = {'en': 'English', 'sk': 'Slovenčina'}
CATALOG_DIR = Path(__file__).with_name('locales')
logger = logging.getLogger('ndtranskripthor.i18n')


def normalize_language(value):
    return value if isinstance(value, str) and value in LANGUAGES else 'en'


def fields(text):
    return {(name, spec, conversion) for _, name, spec, conversion in Formatter().parse(text) if name is not None}


class Translator:
    def __init__(self, language='en', catalogs=None):
        self.language = normalize_language(language)
        self.catalogs = catalogs if catalogs is not None else {
            code: json.loads((CATALOG_DIR/f'{code}.json').read_text(encoding='utf-8'))
            for code in LANGUAGES}
        self.reported = set()

    def warn(self, key, reason):
        if (key, reason) not in self.reported:
            self.reported.add((key, reason))
            # Only keys/reasons: never log transcript contents or parameter values.
            logger.warning('locale=%s key=%s reason=%s', self.language, key, reason)

    def __call__(self, key, **values):
        english = self.catalogs['en'].get(key)
        if english is None:
            self.warn(key, 'missing English key')
            return '['+key+']'
        text = self.catalogs.get(self.language, {}).get(key)
        if text is None:
            self.warn(key, 'missing translation; using English')
            text = english
        try:
            if fields(text) != fields(english):
                self.warn(key, 'invalid placeholders; using English')
                text = english
            return text.format(**values)
        except (ValueError, KeyError, IndexError, TypeError):
            self.warn(key, 'invalid formatting parameters')
            try:
                return english.format(**values)
            except (ValueError, KeyError, IndexError, TypeError):
                return english

    def count(self, key, count, **values):
        suffix = 'one' if count == 1 else 'few' if self.language == 'sk' and count in (2, 3, 4) else 'other'
        return self(key+'.'+suffix, count=count, **values)


_active = None


def set_language(language, diagnostic_dir=None):
    global _active
    _active = Translator(language)
    # A spawned downloader inherits the session language, not the pending choice.
    os.environ['ND_UI_LANGUAGE'] = _active.language
    if diagnostic_dir is not None:
        from logging.handlers import RotatingFileHandler
        close_diagnostics()
        try:
            path = Path(diagnostic_dir)/'i18n.log'
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.addHandler(RotatingFileHandler(path, maxBytes=100_000, backupCount=1, encoding='utf-8'))
        except OSError:
            logger.warning('Cannot open translation diagnostic log')


def close_diagnostics():
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def translator():
    global _active
    if _active is None:
        _active = Translator()
    return _active


def tr(key, **values):
    return translator()(key, **values)


def count_text(key, count):
    return translator().count(key, count)


def choice_box(parent, canonical, labels, **kwargs):
    """Translate display labels without changing legacy ASR settings or IDs."""
    import tkinter as tk
    from tkinter import ttk
    display = tk.StringVar(master=parent)
    reverse = {label: key for key, label in labels.items()}
    def refresh(*_):
        display.set(labels.get(canonical.get(), canonical.get()))
    refresh()
    widget = ttk.Combobox(parent, textvariable=display, values=list(labels.values()), **kwargs)
    widget.bind('<<ComboboxSelected>>', lambda _: canonical.set(reverse[display.get()]))
    token = canonical.trace_add('write', refresh)
    widget.bind('<Destroy>', lambda event: canonical.trace_remove('write', token) if event.widget == widget else None, add='+')
    widget.display_variable = display
    return widget
