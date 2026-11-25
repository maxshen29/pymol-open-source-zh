#!/usr/bin/env python
"""Extract user-visible strings from the PyMOL desktop front ends.

Produces a JSON inventory consumed by ``tools/i18n_lint.py --coverage`` and by
translators. The extractor is deliberately conservative: it only harvests
strings that a Python renderer actually displays.

Usage::

    python tools/i18n_extract.py --output gui_strings.json

Sources (defaults):

* ``modules/pymol/_gui.py``          shared menu-bar spec (Qt and Tk)
* ``modules/pmg_qt/**/*.py``         Qt widgets and dialogs
* ``modules/pmg_qt/forms/*.ui``      Qt Designer forms
* ``modules/pmg_tk/**/*.py``         Tk widgets

``modules/pymol/menu.py`` labels are excluded because they are painted by the
C++ internal GUI and cannot be translated from Python today.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# gettext-style ``('...', '...')`` pairs and Qt widget constructors
PAIRS = re.compile(r"\(\s*(?:'command'|'menu'|'check'|'radio')?\s*,\s*'([^']+)'\s*,|"
                   r"'([^']+)'\s*,\s*(?:cmd\.|lambda|WidgetMenu|self\.|'[a-z_]+')")
QT = re.compile(r"(?:QPushButton|QLabel|QAction|QCheckBox|QRadioButton|QGroupBox)"
                r"\(\s*(?:self\s*,\s*)?'([^']+)'|"
                r"setText\(\s*'([^']+)'|"
                r"setWindowTitle\(\s*'([^']+)'|"
                r"setToolTip\(\s*'([^']+)'")
UI_STRING = re.compile(r"<string>([^<]+)</string>")

CONTEXTS = {
    'modules/pymol/_gui.py': 'menu_label',
    'modules/pmg_tk/': 'label',
    'forms/': 'ui-string',
}


def _context(path):
    for prefix, ctx in CONTEXTS.items():
        if prefix in path:
            return ctx
    return 'widget'


def extract() -> dict:
    items = []
    counts = {}
    for py in sorted(ROOT.glob('modules/pmg_qt/**/*.py')) + \
            sorted(ROOT.glob('modules/pmg_tk/**/*.py')) + \
            [ROOT / 'modules' / 'pymol' / '_gui.py']:
        text = py.read_text(encoding='utf-8', errors='replace')
        rel = py.relative_to(ROOT).as_posix()
        n = 0
        for match in PAIRS.finditer(text):
            value = match.group(1) or match.group(2)
            if value and any(c.isalpha() for c in value):
                items.append({'file': rel, 'line': _line(text, match.start()),
                              'text': value, 'context': _context(rel)})
                n += 1
        for match in QT.finditer(text):
            value = next((g for g in match.groups() if g), None)
            if value and any(c.isalpha() for c in value):
                items.append({'file': rel, 'line': _line(text, match.start()),
                              'text': value, 'context': _context(rel)})
                n += 1
        counts[rel] = n

    for ui in sorted(ROOT.glob('modules/pmg_qt/forms/*.ui')):
        text = ui.read_text(encoding='utf-8', errors='replace')
        rel = ui.relative_to(ROOT).as_posix()
        n = 0
        for match in UI_STRING.finditer(text):
            value = match.group(1).strip()
            if value and any(c.isalpha() for c in value):
                items.append({'file': rel, 'line': _line(text, match.start()),
                              'text': value, 'context': 'ui-string'})
                n += 1
        counts[rel] = n

    return {'generated_by': 'tools/i18n_extract.py',
            'counts': counts,
            'items': items}


def _line(text, offset):
    return text.count('\n', 0, offset) + 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', '-o', help='write JSON to this file')
    args = parser.parse_args(argv)
    data = extract()
    payload = json.dumps(data, indent=1, ensure_ascii=False)
    if args.output:
        pathlib.Path(args.output).write_text(payload + '\n', encoding='utf-8')
    else:
        sys.stdout.write(payload)
    print('extracted %d items from %d sources'
          % (len(data['items']), len(data['counts'])), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
