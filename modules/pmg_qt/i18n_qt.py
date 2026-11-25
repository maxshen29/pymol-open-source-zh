# ---------------------------------------------------------------------
# Qt front end localization helpers (Qt independent by design).
#
# This file is part of the Open-Source PyMOL distribution and is
# published under the same BSD-like terms as the rest of this project
# (see the LICENSE file). No warranty of any kind.
# ---------------------------------------------------------------------
"""Localize Qt widgets, menus and actions.

The helpers only rely on the *duck typed* Qt API (``text()``/``setText()``
and friends) and never import PySide6/PyQt, which keeps them unit testable
on machines without a Qt installation and lets the same code serve any Qt
binding that PyMOL supports.

Every localized widget keeps its English source text in a dynamic property
(``_pymol_i18n_<property>``), which makes :func:`retranslate_tree` able to
switch languages live and makes repeated calls idempotent. Text that the
application changed after localization (file names in the title bar,
feedback output, ...) is deliberately left alone.
"""

from pymol import i18n

__all__ = [
    'language_choices',
    'localize_action',
    'localize_menu',
    'localize_tree',
    'localize_widget',
    'mark_untranslated',
    'retranslate_tree',
    'translate',
]

_PREFIX = '_pymol_i18n_'
_SKIP_PROP = _PREFIX + 'skip'

#: ``getter``/``setter`` pairs that may hold user visible text.
PROPERTIES = (
    ('windowTitle', 'setWindowTitle'),
    ('title', 'setTitle'),
    ('text', 'setText'),
    ('toolTip', 'setToolTip'),
    ('statusTip', 'setStatusTip'),
    ('placeholderText', 'setPlaceholderText'),
)

#: Object types for which the ``text`` property is a label (never user data).
_TEXT_LABELS = frozenset({
    'QAbstractButton', 'QAction', 'QCheckBox', 'QGroupBox', 'QLabel',
    'QMenu', 'QPushButton', 'QRadioButton', 'QToolButton', 'QWidgetAction',
})


def _mro_names(obj):
    return {klass.__name__ for klass in type(obj).__mro__}


def _store(obj, prop, value):
    """Remember the source text for *prop* on *obj*."""
    setter = getattr(obj, 'setProperty', None)
    key = _PREFIX + prop
    if setter is not None:
        try:
            setter(key, value)
            return
        except Exception:
            pass
    try:
        setattr(obj, key, value)
    except Exception:
        pass


def _stored(obj, prop):
    """Return the remembered source text for *prop*, or ``None``."""
    key = _PREFIX + prop
    getter = getattr(obj, 'property', None)
    if getter is not None:
        try:
            value = getter(key)
        except Exception:
            value = None
        if value:
            return value
    try:
        return getattr(obj, key, None)
    except Exception:
        return None


def translate(text):
    """Translate *text*, tolerating Qt mnemonic ampersands."""
    return i18n.tr(text)


def mark_untranslated(obj):
    """Exclude *obj* from localization.

    Used for widgets whose text must always stay in its native form (for
    example the entries of the language selector menu, which show each
    language in its own language regardless of the active UI language).
    """
    setter = getattr(obj, 'setProperty', None)
    if setter is not None:
        try:
            setter(_SKIP_PROP, True)
            return
        except Exception:
            pass
    try:
        setattr(obj, _SKIP_PROP, True)
    except Exception:
        pass


def _is_skipped(obj):
    getter = getattr(obj, 'property', None)
    if getter is not None:
        try:
            if getter(_SKIP_PROP):
                return True
        except Exception:
            pass
    try:
        return bool(getattr(obj, _SKIP_PROP, False))
    except Exception:
        return False


def _is_menu_action(obj):
    """Return ``True`` for a QAction that represents a submenu.

    ``QMenu.menuAction()`` is the same text as ``QMenu.title()`` and Qt keeps
    them in sync, so localizing both makes them fight (and breaks switching
    back to the source language). The menu itself is localized separately, so
    its action must be skipped.
    """
    if 'QAction' not in _mro_names(obj):
        return False
    getter = getattr(obj, 'menu', None)
    if getter is None:
        return False
    try:
        return getter() is not None
    except Exception:
        return False


def _apply(obj, prop):
    """Translate one property of *obj*. Returns ``True`` if it changed."""
    if _is_skipped(obj):
        return False
    if _is_menu_action(obj):
        return False
    getter = getattr(obj, prop, None)
    setter = getattr(obj, 'set' + prop[0].upper() + prop[1:], None)
    if getter is None or setter is None:
        return False
    if prop == 'text' and not (_TEXT_LABELS & _mro_names(obj)):
        return False
    try:
        current = getter()
    except Exception:
        return False
    if not isinstance(current, str) or not current.strip():
        return False
    source = _stored(obj, prop)
    if source is None:
        source = current
        _store(obj, prop, source)
    else:
        applied = _stored(obj, prop + '_applied')
        if applied is not None and current != applied:
            # the application replaced the text after we translated it
            return False
    new = i18n.tr(source)
    if new == current:
        return False
    try:
        setter(new)
    except Exception:
        return False
    _store(obj, prop + '_applied', new)
    return True


def localize_widget(widget):
    """Translate every text property of a single widget/action/menu."""
    changed = False
    for prop, _setter in PROPERTIES:
        if _apply(widget, prop):
            changed = True
    return changed


def localize_action(action, source=None):
    """Translate a QAction, optionally with an explicit English *source*."""
    if source and not _stored(action, 'text'):
        _store(action, 'text', source)
        try:
            action.setText(i18n.tr(source))
            _store(action, 'text_applied', i18n.tr(source))
            return True
        except Exception:
            return False
    return _apply(action, 'text')


def localize_menu(menu, source=None):
    """Translate a QMenu title, optionally with an explicit English *source*."""
    if source and not _stored(menu, 'title'):
        _store(menu, 'title', source)
        try:
            title = getattr(menu, 'title', None)
            current = title() if title is not None else ''
            new = i18n.tr(source)
            if current != new:
                menu.setTitle(new)
                _store(menu, 'title_applied', new)
            # keep the (Windows) window title in sync, as the Qt GUI does
            if hasattr(menu, 'setWindowTitle'):
                try:
                    menu.setWindowTitle(menu.title())
                except Exception:
                    pass
            return True
        except Exception:
            return False
    return _apply(menu, 'title')


def _descendants(root):
    """Yield every QObject below *root* (breadth first, cycle safe)."""
    seen = set()
    queue = list(root.children()) if hasattr(root, 'children') else []
    while queue:
        obj = queue.pop(0)
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        yield obj
        try:
            queue.extend(obj.children())
        except Exception:
            continue


def localize_tree(root):
    """Translate *root* and everything below it. Returns the change count."""
    count = 1 if localize_widget(root) else 0
    for obj in _descendants(root):
        if localize_widget(obj):
            count += 1
    return count


def retranslate_tree(root):
    """Re-apply the current language to a previously localized tree."""
    return localize_tree(root)


def language_choices():
    """Available languages as ``[(code, native_name), ...]``."""
    return [(entry['code'], entry['native_name'])
            for entry in i18n.available_languages()]
