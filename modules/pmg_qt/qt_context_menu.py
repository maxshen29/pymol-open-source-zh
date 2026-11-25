# ---------------------------------------------------------------------
# Qt-native right-click (context) menu.
#
# This file is part of the Open-Source PyMOL distribution and is
# published under the same BSD-like terms as the rest of this project
# (see the LICENSE file). No warranty of any kind.
# ---------------------------------------------------------------------
"""Render PyMOL's right-click menu with Qt so it can show CJK text.

PyMOL's C++ internal GUI paints popup menus with an ASCII bitmap font
(``FontGLUT``), so a translated label renders as ``??????``.  Qt uses system
fonts with full Unicode coverage, so rendering the same menu data with a
``QMenu`` lets the right-click menu follow the selected language.

Scope
-----
The atom under the cursor lives in C++ (``I->LastPicked``) and is not exposed
to Python, so this module shows the *generic* "Main Pop-Up" — the menu PyMOL
itself shows when right-clicking empty space.  The context-sensitive
object/atom menus are not reproduced.

Safety
------
The menu is only used when the default 3-button mode is active
(``button_mode == 0``); custom mouse modes keep their native C++ behaviour.
It can be switched off at runtime::

    pymol.qt_context_menu 0        # back to the native PyMOL menu
    PYMOL_QT_CONTEXT_MENU=0 pymol  # environment default
"""

from __future__ import annotations

import os
import re

from pymol import i18n
from pymol.Qt import QtGui, QtWidgets

__all__ = [
    'build_menu',
    'can_show',
    'enabled',
    'install_command',
    'set_enabled',
    'show',
]

#: PyMOL color-code prefix (e.g. ``\933``) used for destructive menu items.
_COLOR_RE = re.compile(r'\\[0-9]{3}')
_RED_CODE = '\\933'
_ENV = 'PYMOL_QT_CONTEXT_MENU'
_RED = (200, 0, 0)

_enabled = None


def enabled():
    """Whether the Qt right-click menu is enabled (env default: yes)."""
    global _enabled
    if _enabled is None:
        value = os.environ.get(_ENV, '1').strip().lower()
        _enabled = value not in ('', '0', 'no', 'false', 'off')
    return _enabled


def set_enabled(on):
    """Enable/disable the Qt right-click menu; returns the new state."""
    global _enabled
    _enabled = bool(on)
    return _enabled


def _clean(text):
    """Strip PyMOL color codes from a menu label."""
    return _COLOR_RE.sub('', text)


def _callback(command, cmd):
    """Turn a PyMOL menu command (string or callable) into a Qt callback."""
    if isinstance(command, str):
        return lambda: cmd.do(command)
    if callable(command):
        return lambda: command()
    return None


def build_menu(cmd, data, parent=None):
    """Recursively build a ``QMenu`` from PyMOL menu data.

    ``data`` is a list of ``[code, label, command_or_submenu]`` items, where
    ``code`` is 0 (separator), 1 (item) or 2 (title/header).
    """
    menu = QtWidgets.QMenu(parent)
    for item in data:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        code = item[0]
        raw = item[1] if isinstance(item[1], str) else ''
        label = i18n.tr(_clean(raw).strip())
        command = item[2] if len(item) > 2 else None
        if code == 0:
            menu.addSeparator()
        elif code == 2:
            action = menu.addAction(label)
            action.setEnabled(False)
        elif isinstance(command, list):
            submenu = build_menu(cmd, command, menu)
            submenu.setTitle(label)
            menu.addMenu(submenu)
        elif command:
            action = menu.addAction(label, _callback(command, cmd))
            # Qt6 removed QAction.setForeground; the color code is stripped
            # above, so destructive items are shown with normal text.
        else:
            action = menu.addAction(label)
            action.setEnabled(False)
    return menu


def can_show(cmd):
    """Whether the Qt menu should replace the native right-click menu."""
    if not enabled():
        return False
    try:
        # only the default 3-button mode puts "menu" on the right button
        return int(cmd.get('button_mode')) == 0
    except Exception:
        return True


def show(gl_widget, screen_pos):
    """Show the Qt version of PyMOL's right-click menu. Returns True if shown."""
    import pymol.menu as menu_module

    cmd = gl_widget.pymol.cmd
    try:
        data = menu_module.main_menu(cmd, (0.0, 0.0, 0.0), (0, 0))
    except Exception:
        return False
    build_menu(cmd, data, gl_widget).exec(screen_pos)
    return True


def install_command(cmd):
    """Register the ``qt_context_menu`` PyMOL command (0/1 to toggle)."""

    def qt_context_menu(on=1, quiet=1):
        """Use the Qt-native right-click menu (0 = native PyMOL menu)"""
        state = set_enabled(int(on))
        if not quiet:
            print(' qt_context_menu: %s' % ('on' if state else 'off'))
        return state

    try:
        cmd.extend('qt_context_menu', qt_context_menu)
    except Exception:
        pass
    return qt_context_menu
