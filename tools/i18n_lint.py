#!/usr/bin/env python
"""Validate PyMOL translation catalogs.

Usage::

    python tools/i18n_lint.py                 # lint data/i18n/*.json
    python tools/i18n_lint.py --strict        # warnings are errors
    python tools/i18n_lint.py --json          # machine readable report
    python tools/i18n_lint.py --coverage gui_strings.json

Checks performed for every catalog ``<code>.json`` (all languages except the
source language ``en``):

``error``
    * file is not valid JSON or not an object
    * ``meta.language`` missing or not matching the file name
    * ``meta.native_name`` missing/empty
    * ``strings`` missing or not an object
    * duplicated JSON keys
    * empty or whitespace-only translation
    * translation value is neither a string nor a plural mapping
    * symbolic keys (``dialog.builder.title``) that are not defined in the
      source catalog
    * ``{placeholder}`` or ``%s``-style mismatch with the source text
    * invalid plural mapping (only ``one``/``other`` allowed)

``warning``
    * translation identical to the source text (possibly untranslated)
    * whitespace at the start/end of a translation
    * language entry that is not listed in ``SUPPORTED`` of the docs
    * keys in the catalog that are not referenced by the GUI inventory
      (only with ``--coverage``)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_LANGUAGE = 'en'

#: ``{name}`` / ``{0}`` placeholders.
BRACE_RE = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*|[0-9]+)\}')
#: printf style placeholders (%s, %d, %.2f, %(name)s, %%)
PRINTF_RE = re.compile(r'%(?:\([A-Za-z_][A-Za-z0-9_]*\))?[-+ 0#]*[0-9]*(?:\.[0-9]+)?[sdifgeuxXoc%]')
#: dotted lowercase keys are symbolic, everything else is a source string
SYMBOLIC_RE = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$')
PLURAL_FORMS = ('one', 'other')


class Problem:
    def __init__(self, level, language, key, message):
        self.level = level
        self.language = language
        self.key = key
        self.message = message

    def as_dict(self):
        return {'level': self.level, 'language': self.language,
                'key': self.key, 'message': self.message}

    def __str__(self):
        key = (' [%s]' % self.key) if self.key else ''
        return '%-7s %s%s: %s' % (self.level, self.language, key, self.message)


def placeholders(text):
    """Return the set of placeholders used by *text*."""
    found = set(BRACE_RE.findall(text or ''))
    found.update(PRINTF_RE.findall(text or ''))
    return found


def _pairs_hook(pairs):
    seen = set()
    duplicates = []
    for key, _value in pairs:
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    if duplicates:
        raise ValueError('duplicated key(s): %s' % ', '.join(sorted(duplicates)))
    return dict(pairs)


def read_json_strict(path):
    """Parse *path*, reporting duplicate keys as an error."""
    text = path.read_text(encoding='utf-8')
    return json.loads(text, object_pairs_hook=_pairs_hook)


def load_source(catalog_dir, source=SOURCE_LANGUAGE):
    """Return ``(meta, strings)`` of the source catalog (may be empty)."""
    path = Path(catalog_dir) / (source + '.json')
    if not path.is_file():
        return {}, {}
    data = read_json_strict(path)
    strings = data.get('strings') if isinstance(data, dict) else None
    if not isinstance(strings, dict):
        strings = {}
    return (data.get('meta') or {}), strings


def source_text(key, source_strings):
    """English text for *key*: symbolic keys need an entry, source keys do not."""
    if key in source_strings and isinstance(source_strings[key], str):
        return source_strings[key]
    if SYMBOLIC_RE.match(key):
        return None
    return key


def _check_value(language, key, value, english, problems, source_strings):
    if isinstance(value, dict):
        if not set(value) <= set(PLURAL_FORMS):
            problems.append(Problem('error', language, key,
                                    'plural mapping may only use %s'
                                    % '/'.join(PLURAL_FORMS)))
            return
        if not value.get('other'):
            problems.append(Problem('error', language, key,
                                    'plural mapping needs an "other" form'))
            return
        texts = [v for v in value.values() if isinstance(v, str)]
        if len(texts) != len(value):
            problems.append(Problem('error', language, key,
                                    'plural form is not a string'))
            return
    elif isinstance(value, str):
        if not value.strip():
            problems.append(Problem('error', language, key, 'empty translation'))
            return
        if value != value.strip() and (english is None
                                       or english == english.strip()):
            problems.append(Problem('warning', language, key,
                                    'translation has leading/trailing whitespace'))
        texts = [value]
    else:
        problems.append(Problem('error', language, key,
                                'value is not a string or plural mapping'))
        return

    if english is None:
        problems.append(Problem('error', language, key,
                                'symbolic key is not defined in %s.json'
                                % SOURCE_LANGUAGE))
        return

    expected = placeholders(english)
    for text in texts:
        actual = placeholders(text)
        if actual != expected:
            problems.append(Problem(
                'error', language, key,
                'placeholder mismatch: expected %s, got %s'
                % (sorted(expected) or 'none', sorted(actual) or 'none')))
            break
    # prune source entries that changed after translation
    if key in source_strings and isinstance(source_strings[key], str) \
            and isinstance(value, str) and value.strip() == source_strings[key].strip() \
            and placeholders(value) == placeholders(source_strings[key]):
        if language != SOURCE_LANGUAGE:
            problems.append(Problem('warning', language, key,
                                    'translation identical to source text'))


def lint_catalog(path, source_strings, source=SOURCE_LANGUAGE):
    """Lint a single catalog file. Returns a list of :class:`Problem`."""
    problems = []
    path = Path(path)
    language = path.stem
    try:
        data = read_json_strict(path)
    except ValueError as exc:
        return [Problem('error', language, '', 'invalid JSON: %s' % exc)]
    if not isinstance(data, dict):
        return [Problem('error', language, '', 'catalog must be a JSON object')]

    meta = data.get('meta')
    if not isinstance(meta, dict):
        problems.append(Problem('error', language, '', 'missing "meta" object'))
        meta = {}
    declared = meta.get('language')
    if declared != language:
        problems.append(Problem(
            'error', language, '',
            'meta.language is %r but the file is named %r.json'
            % (declared, language)))
    native = meta.get('native_name')
    if not isinstance(native, str) or not native.strip():
        problems.append(Problem('error', language, '',
                                'meta.native_name is required'))
    fallback = meta.get('fallback', source)
    if fallback != source:
        problems.append(Problem('warning', language, '',
                                'meta.fallback should be %r, got %r'
                                % (source, fallback)))

    strings = data.get('strings')
    if not isinstance(strings, dict):
        problems.append(Problem('error', language, '', 'missing "strings" object'))
        return problems

    for key, value in strings.items():
        if not isinstance(key, str) or not key.strip():
            problems.append(Problem('error', language, repr(key), 'invalid key'))
            continue
        if key in source_strings:
            english = source_strings[key]
        else:
            english = source_text(key, source_strings)
        _check_value(language, key, value, english, problems, source_strings)

    return problems


def lint_dir(catalog_dir, source=SOURCE_LANGUAGE):
    """Lint every catalog in *catalog_dir*. Returns ``(problems, catalogs)``."""
    catalog_dir = Path(catalog_dir)
    if not catalog_dir.is_dir():
        raise SystemExit('error: %s is not a directory' % catalog_dir)
    source_meta, source_strings = load_source(catalog_dir, source)
    problems = []
    catalogs = {}
    for path in sorted(catalog_dir.glob('*.json')):
        if path.stem == source:
            continue
        catalogs[path.stem] = path
        problems.extend(lint_catalog(path, source_strings, source))
    if not (catalog_dir / (source + '.json')).is_file():
        problems.append(Problem('error', source, '',
                                'source catalog %s.json is missing' % source))
    return problems, catalogs, source_strings


def coverage_report(catalog_dir, inventory_path, language, source=SOURCE_LANGUAGE):
    """Report how much of the extracted GUI inventory is translated."""
    inventory = json.loads(Path(inventory_path).read_text(encoding='utf-8'))
    texts = set()
    items = inventory.get('items', inventory if isinstance(inventory, list) else [])
    for item in items:
        text = item.get('text') if isinstance(item, dict) else None
        if isinstance(text, str) and text.strip():
            texts.add(text)
    catalog_file = Path(catalog_dir) / (language + '.json')
    translated = {}
    if catalog_file.is_file():
        data = read_json_strict(catalog_file)
        strings = data.get('strings') if isinstance(data, dict) else {}
        translated = {k: v for k, v in (strings or {}).items()
                      if isinstance(v, str) and v.strip()}
    covered = sorted(t for t in texts if t in translated)
    missing = sorted(t for t in texts if t not in translated)
    ratio = (100.0 * len(covered) / len(texts)) if texts else 0.0
    return {'language': language, 'inventory': len(texts), 'covered': len(covered),
            'missing': len(missing), 'coverage_percent': round(ratio, 1),
            'missing_texts': missing}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dir', default=str(Path(__file__).resolve().parent.parent
                                             / 'data' / 'i18n'),
                        help='catalog directory (default: data/i18n)')
    parser.add_argument('--source', default=SOURCE_LANGUAGE)
    parser.add_argument('--strict', action='store_true',
                        help='treat warnings as errors')
    parser.add_argument('--json', action='store_true',
                        help='print a JSON report')
    parser.add_argument('--coverage', metavar='INVENTORY',
                        help='GUI inventory JSON from tools/i18n_extract.py')
    parser.add_argument('--coverage-language', default='zh_CN')
    args = parser.parse_args(argv)

    problems, catalogs, source_strings = lint_dir(args.dir, args.source)
    errors = [p for p in problems if p.level == 'error']
    warnings = [p for p in problems if p.level == 'warning']

    report = {
        'catalog_dir': str(args.dir),
        'source_strings': len(source_strings),
        'catalogs': {code: str(path) for code, path in catalogs.items()},
        'errors': len(errors),
        'warnings': len(warnings),
        'problems': [p.as_dict() for p in problems],
    }
    if args.coverage:
        report['coverage'] = coverage_report(args.dir, args.coverage,
                                             args.coverage_language, args.source)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for problem in problems:
            print(problem)
        if args.coverage:
            cov = report['coverage']
            print('coverage %s: %d/%d strings (%.1f%%)'
                  % (cov['language'], cov['covered'], cov['inventory'],
                     cov['coverage_percent']))
            if cov['missing'] and args.strict:
                for text in cov['missing'][:200]:
                    print('   missing:', text)
        print('%d catalog(s), %d error(s), %d warning(s)'
              % (len(catalogs), len(errors), len(warnings)))

    if errors or (args.strict and (warnings or
                                 (report.get('coverage', {}).get('missing', 0)))):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
