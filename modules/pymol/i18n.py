# ---------------------------------------------------------------------
# Internationalization (i18n) support for PyMOL.
#
# This file is part of the Open-Source PyMOL distribution and is
# published under the same BSD-like terms as the rest of this project
# (see the LICENSE file). No warranty of any kind.
# ---------------------------------------------------------------------
"""Centralized, front-end independent internationalization for PyMOL.

This module is pure standard library on purpose: it can be imported
standalone (without the ``pymol._cmd`` extension module) so that it can be
unit tested and so that command line tools can reuse it.

Data layout
-----------
Translation units are plain JSON files in ``data/i18n/``::

    data/i18n/en.json       source language ("en"), always required
    data/i18n/zh_CN.json    Simplified Chinese

Every catalog has the following shape::

    {
      "meta": {
        "language": "zh_CN",
        "native_name": "简体中文",
        "english_name": "Simplified Chinese",
        "source_language": "en",
        "fallback": "en",
        "version": "1.0"
      },
      "strings": {
        "File": "文件",
        "menu.file": "文件"
      }
    }

Keys are either English source strings (so that untranslated strings keep
working and legacy code can be migrated incrementally) or dotted symbolic
keys (recommended for new code, e.g. ``dialog.builder.title``). Both live
in the same flat namespace.

Lookup / fallback
-----------------
``tr("File")`` resolves as: requested language -> source language (``en``)
-> the key itself. A missing translation never raises and never breaks the
UI; it is recorded for ``missing_report()`` when ``PYMOL_I18N_DEBUG`` is
set.

Language resolution
-------------------
Highest priority first:

1. an explicit :func:`set_language` call (the GUI language menu uses it),
2. ``--lang <code>`` on the PyMOL command line (:func:`init`),
3. ``$PYMOL_LANG``,
4. a language saved by a previous session,
5. the operating system's UI locale,
6. :data:`DEFAULT_LANGUAGE` (``"en"``).

Any unsupported locale silently falls back to English, which makes the
default behavior safe on every platform.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

__all__ = [
    'DEFAULT_LANGUAGE',
    'SOURCE_LANGUAGE',
    'available_languages',
    'catalog_meta',
    'catalog_path',
    'get_language',
    'get_search_dirs',
    'has_translation',
    'init',
    'install_command',
    'language_display_name',
    'missing_report',
    'normalize_language',
    'preference_path',
    'reload_catalogs',
    'reset_state',
    'resolve_default_language',
    'set_language',
    'tr',
    'trc',
    'trn',
]

#: Language used when nothing else is requested.
DEFAULT_LANGUAGE = 'en'

#: Language whose catalog holds the untranslated source strings.
SOURCE_LANGUAGE = 'en'

#: Files and directories searched for catalogs, in order.
CATALOG_SUBDIR = ('data', 'i18n')

#: Aliases accepted on the command line, in the environment and in the UI.
LANGUAGE_ALIASES = {
    'en': 'en',
    'en_us': 'en',
    'en-us': 'en',
    'en_gb': 'en',
    'en-gb': 'en',
    'english': 'en',
    'zh': 'zh_CN',
    'zh_cn': 'zh_CN',
    'zh-cn': 'zh_CN',
    'zh_hans': 'zh_CN',
    'zh-hans': 'zh_CN',
    'zh_sg': 'zh_CN',
    'zh-sg': 'zh_CN',
    'chinese': 'zh_CN',
    'chs': 'zh_CN',
    'zh_tw': 'zh_TW',
    'zh-tw': 'zh_TW',
    'zh_hk': 'zh_HK',
    'zh-hk': 'zh_HK',
    'zh_hant': 'zh_TW',
    'zh-hant': 'zh_TW',
    'cht': 'zh_TW',
}

#: Windows LANGID -> BCP-47-ish code (only the languages we ship).
_WIN_LANGIDS = {
    0x0404: 'zh_TW',
    0x0409: 'en',
    0x0804: 'zh_CN',
    0x0C04: 'zh_HK',
    0x1004: 'zh_CN',
}

#: Environment variable to point at a catalog directory (used by tests).
_ENV_CATALOG_DIR = 'PYMOL_I18N_DIR'
#: Environment variable pinning the language (same as ``--lang``).
_ENV_LANGUAGE = 'PYMOL_LANG'
#: Environment variable to override the saved-preference location.
_ENV_PREFERENCE = 'PYMOL_I18N_PREFERENCE'
#: Set to a non-empty value to record missing translations.
_ENV_DEBUG = 'PYMOL_I18N_DEBUG'

_lock = threading.RLock()
_language = None            # type: str | None
_catalogs = {}              # type: dict[str, dict]
_metas = {}                 # type: dict[str, dict]
_search_dirs = None         # type: list[Path] | None
_missing = {}               # type: dict[str, int]
_listeners = []             # type: list
_MISSING = object()


# ---------------------------------------------------------------------------
# search paths and catalog loading
# ---------------------------------------------------------------------------
def get_search_dirs():
    """Return the directories that may contain ``<code>.json`` catalogs.

    The result is ordered by priority and cached. Set ``$PYMOL_I18N_DIR``
    to test alternative catalogs without touching the installation.
    """
    global _search_dirs
    with _lock:
        if _search_dirs is not None:
            return list(_search_dirs)

        candidates = []

        override = os.environ.get(_ENV_CATALOG_DIR)
        if override:
            candidates.extend(override.split(os.pathsep))

        data_home = os.environ.get('PYMOL_DATA')
        if data_home:
            candidates.append(os.path.join(data_home, 'i18n'))

        pymol_home = os.environ.get('PYMOL_PATH')
        if pymol_home:
            candidates.append(os.path.join(pymol_home, *CATALOG_SUBDIR))

        # source checkout:  <repo>/modules/pymol/i18n.py -> <repo>/data/i18n
        here = Path(__file__).resolve().parent
        candidates.append(here.parents[1] / CATALOG_SUBDIR[0] / CATALOG_SUBDIR[1])
        # installed wheel: <site-packages>/pymol/i18n.py + pymol_path/data/i18n
        candidates.append(here / 'pymol_path' / CATALOG_SUBDIR[0] / CATALOG_SUBDIR[1])
        candidates.append(here / 'data' / 'i18n')

        seen = set()
        dirs = []
        for candidate in candidates:
            try:
                path = Path(candidate)
            except TypeError:
                continue
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            if path.is_dir():
                dirs.append(path)

        _search_dirs = dirs
        return list(dirs)


def catalog_path(code):
    """Return the ``Path`` of the catalog for *code*, or ``None``."""
    code = normalize_language(code)
    if not code:
        return None
    for directory in get_search_dirs():
        path = directory / (code + '.json')
        if path.is_file():
            return path
    return None


def _read_catalog_file(path):
    """Parse one catalog file, tolerating malformed input."""
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_catalog(code=None):
    """Return the (cached) ``str -> str`` translation map for *code*.

    Accepts both the documented ``{"meta":..., "strings":...}`` layout and a
    bare flat mapping, so hand written catalogs keep working.
    """
    code = normalize_language(code) or DEFAULT_LANGUAGE
    with _lock:
        if code in _catalogs:
            return _catalogs[code]

        strings = {}
        meta = {'language': code}
        path = catalog_path(code)
        if path is not None:
            data = _read_catalog_file(path)
            if data is not None:
                raw_meta = data.get('meta')
                if isinstance(raw_meta, dict):
                    meta.update({k: v for k, v in raw_meta.items()
                                 if isinstance(k, str)})
                    body = data.get('strings')
                    if isinstance(body, dict):
                        strings = body
                    else:
                        strings = {k: v for k, v in data.items() if k != 'meta'}
                else:
                    strings = data
        meta.setdefault('language', code)
        _metas[code] = meta
        _catalogs[code] = {
            key: value for key, value in strings.items()
            if isinstance(key, str) and (isinstance(value, str)
                                         or isinstance(value, dict))
        }
        return _catalogs[code]


def catalog_meta(code=None):
    """Return a copy of the ``meta`` block of the catalog for *code*."""
    code = normalize_language(code) or DEFAULT_LANGUAGE
    load_catalog(code)
    with _lock:
        return dict(_metas.get(code, {'language': code}))


def reload_catalogs():
    """Drop cached catalogs and search paths (used by tests and by ``lang``)."""
    global _search_dirs
    with _lock:
        _catalogs.clear()
        _metas.clear()
        _missing.clear()
        _search_dirs = None


def reset_state():
    """Forget everything, including the resolved language.

    Intended for tests and for tools that re-read the environment; the GUI
    never calls this.
    """
    global _language
    reload_catalogs()
    with _lock:
        _language = None


def available_languages():
    """Return a sorted list of ``{'code', 'native_name', 'english_name'}``.

    The source language is always first, so that the English entry is
    available even when the installation ships no catalog files at all.
    """
    found = {}
    for directory in get_search_dirs():
        try:
            files = sorted(directory.glob('*.json'))
        except OSError:
            continue
        for path in files:
            code = normalize_language(path.stem)
            if not code or code in found:
                continue
            meta = {}
            data = _read_catalog_file(path)
            if isinstance(data, dict) and isinstance(data.get('meta'), dict):
                meta = data['meta']
            found[code] = {
                'code': code,
                'native_name': str(meta.get('native_name')
                                   or _DEFAULT_NAMES.get(code, code)),
                'english_name': str(meta.get('english_name')
                                    or _DEFAULT_NAMES.get(code, code)),
            }
    found.setdefault(SOURCE_LANGUAGE, {
        'code': SOURCE_LANGUAGE,
        'native_name': 'English',
        'english_name': 'English',
    })
    # make sure that the catalog directory of a language is readable,
    # otherwise it is not really selectable
    selectable = []
    for code in sorted(found, key=lambda c: (c != DEFAULT_LANGUAGE, c)):
        if code == SOURCE_LANGUAGE or catalog_path(code) is not None:
            selectable.append(found[code])
    return selectable


_DEFAULT_NAMES = {
    'en': 'English',
    'zh_CN': '简体中文',
    'zh_TW': '繁體中文',
    'zh_HK': '繁體中文',
}


def language_display_name(code):
    """Human readable (native) name for *code*."""
    code = normalize_language(code) or DEFAULT_LANGUAGE
    for entry in available_languages():
        if entry['code'] == code:
            return entry['native_name']
    return _DEFAULT_NAMES.get(code, code)


# ---------------------------------------------------------------------------
# language normalization and detection
# ---------------------------------------------------------------------------
def normalize_language(code):
    """Map *code* to the canonical form used by catalog file names.

    Unknown input is returned in a best effort canonical form
    (``xx_YY``) and may still be unsupported; callers should verify with
    :func:`language_display_name` / :func:`available_languages`.
    """
    if not code:
        return None
    text = str(code).strip().strip('"\'')
    if not text:
        return None
    # strip encoding and modifier: "zh_CN.UTF-8@euro" -> "zh_CN"
    for separator in ('.', '@'):
        if separator in text:
            text = text.split(separator, 1)[0]
    text = text.strip().replace(' ', '')
    lookup = text.lower().replace('-', '_')
    if lookup in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lookup]
    if '_' not in text and len(text) > 3:
        lookup = text.lower()
        if lookup in LANGUAGE_ALIASES:
            return LANGUAGE_ALIASES[lookup]
    if '_' in text:
        language, region = text.split('_', 1)
        return language.lower() + '_' + region.upper()
    if '-' in text:
        language, region = text.split('-', 1)
        return language.lower() + '_' + region.upper()
    return text.lower()


def _parse_locale_value(value):
    """Best effort conversion of an OS locale value to a language code."""
    if not value:
        return None
    text = str(value).strip()
    lowered = text.lower()
    # Windows: "Chinese (Simplified)_China.936"
    for marker, code in (
            ('chinese (simplified', 'zh_CN'),
            ('chinese (traditional', 'zh_TW'),
            ('chinese', 'zh_CN'),
            ('english', 'en'),
    ):
        if marker in lowered:
            return code
    return normalize_language(text)


def _windows_ui_language():
    """Return the Windows UI language code, or ``None``."""
    if not sys.platform.startswith('win'):
        return None
    try:
        import ctypes
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except Exception:
        return None
    code = _WIN_LANGIDS.get(langid)
    if code:
        return code
    primary = langid & 0x03FF
    return {0x04: 'zh_CN', 0x09: 'en'}.get(primary)


def system_language():
    """Return the desktop UI language of the current user, or ``None``."""
    for variable in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        value = os.environ.get(variable)
        if value and value not in ('C', 'POSIX'):
            code = _parse_locale_value(value)
            if code:
                return code
    code = _windows_ui_language()
    if code:
        return code
    try:
        import locale
        value = locale.getlocale()[0]
    except Exception:
        value = None
    return _parse_locale_value(value)


def preference_path():
    """Location of the persisted language preference.

    Defaults to ``~/.pymol/i18n.json``; ``$PYMOL_I18N_PREFERENCE`` overrides
    it (useful for tests and for portable installations).
    """
    override = os.environ.get(_ENV_PREFERENCE)
    if override:
        return Path(override)
    try:
        home = Path.home()
    except RuntimeError:
        return None
    return home / '.pymol' / 'i18n.json'


def read_preference():
    """Return the language saved by a previous session, or ``None``."""
    path = preference_path()
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if isinstance(data, dict):
        return normalize_language(data.get('language'))
    return None


def save_preference(code):
    """Persist *code* as the language for future sessions.

    Returns ``True`` on success. Failures are silent: writing a user
    preference must never break the application.
    """
    code = normalize_language(code) or DEFAULT_LANGUAGE
    path = preference_path()
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps({'language': code}, indent=2) + '\n',
                       encoding='utf-8')
        os.replace(str(tmp), str(path))
        return True
    except OSError:
        return False


def resolve_default_language():
    """Language to use when the user has not chosen one explicitly."""
    for candidate in (
            os.environ.get(_ENV_LANGUAGE),
            read_preference(),
            system_language(),
    ):
        code = normalize_language(candidate)
        if code and _is_supported(code):
            return code
    return DEFAULT_LANGUAGE


def _is_supported(code):
    if code == SOURCE_LANGUAGE:
        return True
    return catalog_path(code) is not None


# ---------------------------------------------------------------------------
# current language
# ---------------------------------------------------------------------------
def get_language():
    """Return the language currently in effect."""
    global _language
    with _lock:
        if _language is None:
            _language = resolve_default_language()
        return _language


def set_language(code, persist=False):
    """Select the UI language and notify listeners.

    *persist* writes the choice to :func:`preference_path` so that it
    survives a restart. Unsupported languages fall back to the source
    language instead of raising, so a bad ``--lang`` value is harmless.
    """
    global _language
    requested = normalize_language(code)
    effective = requested if requested and _is_supported(requested) \
        else DEFAULT_LANGUAGE
    with _lock:
        changed = effective != _language
        _language = effective
        listeners = list(_listeners)
    # keep $PYMOL_LANG in sync so the C++ side (TextTr in layer1/Text.cpp,
    # used for the internal-GUI HUD) follows the language as well
    try:
        os.environ[_ENV_LANGUAGE] = effective
    except Exception:
        pass
    if persist:
        save_preference(effective)
    if changed:
        for listener in listeners:
            try:
                listener(effective)
            except Exception:
                # a broken listener must not prevent the language change
                if os.environ.get(_ENV_DEBUG):
                    import traceback
                    traceback.print_exc()
    return effective


def add_listener(callback):
    """Register ``callback(code)``, called after the language changes."""
    with _lock:
        if callback not in _listeners:
            _listeners.append(callback)


def remove_listener(callback):
    """Unregister a listener added with :func:`add_listener`."""
    with _lock:
        try:
            _listeners.remove(callback)
        except ValueError:
            pass


def init(argv=None, options=None):
    """Initialize the language from the command line, environment or OS.

    ``argv`` is a PyMOL style argument list (``["--lang", "zh_CN"]``);
    ``options`` may be the parsed ``pymol.invocation.options`` object, whose
    ``lang`` attribute takes precedence. Calling :func:`init` more than once
    is safe.
    """
    explicit = None
    if options is not None:
        explicit = getattr(options, 'lang', None)
    if not explicit and argv:
        explicit = _parse_lang_arg(argv)
    if not explicit:
        explicit = os.environ.get(_ENV_LANGUAGE)
    if explicit:
        return set_language(explicit)
    return set_language(resolve_default_language())


def _parse_lang_arg(argv):
    """Extract ``--lang xx`` / ``--lang=xx`` from *argv*."""
    args = list(argv or ())
    for index, argument in enumerate(args):
        if argument == '--lang' and index + 1 < len(args):
            return args[index + 1]
        if argument.startswith('--lang='):
            return argument.split('=', 1)[1]
    return None


# ---------------------------------------------------------------------------
# translation
# ---------------------------------------------------------------------------
class _SafeMapping(dict):
    """Formatting map that leaves unknown placeholders untouched."""

    def __missing__(self, key):
        return '{' + key + '}'


def _safe_format(text, values):
    try:
        return text.format_map(_SafeMapping(values))
    except (IndexError, ValueError, KeyError):
        return text


def _candidates(text):
    """Possible catalog keys for *text* (exact, mnemonic-stripped, case)."""
    yield text
    if '&' in text:
        yield text.replace('&', '')
    # menu labels are often lowercase while the catalog uses title case
    title = text.title()
    if title != text:
        yield title
    lower = text.lower()
    if lower != text and lower != title:
        yield lower


def _lookup(text):
    """Return the translated string for *text*, or ``_MISSING``."""
    language = get_language()
    catalog = load_catalog(language)
    for candidate in _candidates(text):
        value = catalog.get(candidate, _MISSING)
        if value is not _MISSING:
            return value
    if language != SOURCE_LANGUAGE:
        source = load_catalog(SOURCE_LANGUAGE)
        for candidate in _candidates(text):
            value = source.get(candidate, _MISSING)
            if value is not _MISSING:
                return value
    return _MISSING


def _record_missing(text):
    if not os.environ.get(_ENV_DEBUG):
        return
    with _lock:
        _missing[text] = _missing.get(text, 0) + 1


def tr(text, **values):
    """Translate *text* and interpolate ``{placeholders}``.

    Returns the input unchanged for non-strings, empty strings and unknown
    keys, so it is always safe to wrap user visible text::

        >>> tr('File')
        'File'
        >>> tr('Welcome, {user}', user='Ada')
        'Welcome, Ada'

    A catalog value may also be a mapping ``{"one": ..., "other": ...}`` for
    plural support; :func:`tr` picks ``other`` and :func:`trn` the right form.
    """
    if not isinstance(text, str) or not text:
        return text
    value = _lookup(text)
    if value is _MISSING:
        _record_missing(text)
        return _safe_format(text, values) if values else text
    if isinstance(value, dict):
        value = value.get('other') or value.get('one')
        if not isinstance(value, str):
            _record_missing(text)
            return text
    if values:
        return _safe_format(value, values)
    return value


def trn(singular, plural, count, **values):
    """Translate a plural pair for *count* (English/Chinese rules)."""
    values = dict(values)
    values.setdefault('count', count)
    values.setdefault('n', count)
    if not isinstance(singular, str):
        return singular
    value = _lookup(singular)
    if value is _MISSING and isinstance(plural, str) and plural != singular:
        value = _lookup(plural)
    if isinstance(value, dict):
        form = 'one' if count == 1 else 'other'
        text = value.get(form) or value.get('other') or value.get('one')
        if isinstance(text, str):
            return _safe_format(text, values)
    if isinstance(value, str):
        return _safe_format(value, values)
    _record_missing(singular)
    return _safe_format(singular if count == 1 else plural, values)


def trc(context, text, **values):
    """Translate *text* disambiguated by *context* (gettext ``pgettext``).

    The catalog key is ``"<context>\\x04<text>"``; when no contextual entry
    exists the plain :func:`tr` lookup is used, so contextual overrides are
    purely additive.
    """
    if isinstance(text, str) and text and context:
        value = _lookup('%s\x04%s' % (context, text))
        if value is not _MISSING:
            if isinstance(value, dict):
                value = value.get('other') or value.get('one')
            if isinstance(value, str):
                return _safe_format(value, values) if values else value
    return tr(text, **values)


def has_translation(text, code=None):
    """Return ``True`` when *code* (default: current language) translates *text*."""
    code = normalize_language(code) or get_language()
    if not isinstance(text, str) or not text:
        return False
    if code == SOURCE_LANGUAGE:
        return True
    catalog = load_catalog(code)
    return any(isinstance(catalog.get(candidate), (str, dict))
               for candidate in _candidates(text))


def missing_report():
    """Return ``{text: count}`` for lookups that had no translation.

    Only collected while ``$PYMOL_I18N_DEBUG`` is non-empty.
    """
    with _lock:
        return dict(_missing)


# ---------------------------------------------------------------------------
# PyMOL command
# ---------------------------------------------------------------------------
def _format_language_list(languages=None):
    entries = languages or available_languages()
    current = get_language()
    lines = []
    for entry in entries:
        marker = '*' if entry['code'] == current else ' '
        lines.append(' %s %-8s %s / %s' % (
            marker, entry['code'], entry['native_name'], entry['english_name']))
    return lines


def install_command(cmd):
    """Register the ``lang`` PyMOL command on the *cmd* module.

    ``lang`` without arguments prints the available languages, ``lang
    zh_CN`` switches the interface language and remembers it for the next
    session. Registered lazily so that importing :mod:`pymol.i18n` standalone
    does not pull in the PyMOL API.
    """

    def lang(code=None, quiet=1, _self=cmd):
        """Switch the PyMOL interface language (no argument: list them)"""
        if code in (None, '', 'list', '?'):
            print(' Available languages:')
            for line in _format_language_list():
                print(line)
            print(' Usage: lang <code>   (current: %s)' % get_language())
            return None
        effective = set_language(code, persist=True)
        if effective != normalize_language(code):
            print(' Warning: language "%s" is not available, using "%s"'
                  % (code, effective))
        if not quiet:
            print(' Language set to %s (%s)' % (
                effective, language_display_name(effective)))
        return effective

    try:
        cmd.extend('lang', lang)
    except Exception:
        # already registered (e.g. package reloaded)
        pass
    return lang
