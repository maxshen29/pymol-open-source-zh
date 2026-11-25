# ---------------------------------------------------------------------
# Unit tests for pmg_qt.i18n_qt (the Qt widget localizer). The helper is
# duck typed, so we exercise it with lightweight fake widgets and no Qt
# installation.
# ---------------------------------------------------------------------
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _load(name, *parts):
    spec = importlib.util.spec_from_file_location(name, ROOT.joinpath(*parts))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


i18n = _load('_i18n_under_test', 'modules', 'pymol', 'i18n.py')

# i18n_qt does `from pymol import i18n`; provide a minimal fake package
_pymol = types.ModuleType('pymol')
_pymol.i18n = i18n
sys.modules.setdefault('pymol', _pymol)
i18n_qt = _load('_i18n_qt_under_test', 'modules', 'pmg_qt', 'i18n_qt.py')


class _Base:
    def __init__(self):
        self._props = {}
        self._children = []
        self._text = ''
        self._title = ''
        self._tooltip = ''
        self._status = ''
        self._placeholder = ''
        self._window = ''

    def setProperty(self, k, v):
        self._props[k] = v

    def property(self, k):
        return self._props.get(k)

    def children(self):
        return list(self._children)


class QAction(_Base):
    def text(self):
        return self._text

    def setText(self, v):
        self._text = v

    def toolTip(self):
        return self._tooltip

    def setToolTip(self, v):
        self._tooltip = v

    def statusTip(self):
        return self._status

    def setStatusTip(self, v):
        self._status = v


class QLabel(_Base):
    def text(self):
        return self._text

    def setText(self, v):
        self._text = v


class QPushButton(_Base):
    def text(self):
        return self._text

    def setText(self, v):
        self._text = v


class QLineEdit(_Base):
    def text(self):
        return self._text

    def setText(self, v):
        self._text = v

    def placeholderText(self):
        return self._placeholder

    def setPlaceholderText(self, v):
        self._placeholder = v


class QMenu(_Base):
    def title(self):
        return self._title

    def setTitle(self, v):
        self._title = v

    def windowTitle(self):
        return self._window

    def setWindowTitle(self, v):
        self._window = v


class QWidget(_Base):
    def windowTitle(self):
        return self._window

    def setWindowTitle(self, v):
        self._window = v


class QtLocalizerTestCase(unittest.TestCase):
    def setUp(self):
        i18n.reset_state()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        d = pathlib.Path(self._tmp.name)
        en = {'meta': {'language': 'en'}, 'strings': {}}
        zh = {'meta': {'language': 'zh_CN', 'native_name': '简体中文'},
              'strings': {'Hello': '你好', 'Type here': '在此输入',
                          'Close': '关闭', 'File': '文件', 'Language': '语言'}}
        (d / 'en.json').write_text(json.dumps(en, ensure_ascii=False), encoding='utf-8')
        (d / 'zh_CN.json').write_text(json.dumps(zh, ensure_ascii=False), encoding='utf-8')
        self.env_patch = mock.patch.dict(os.environ, {
            'PYMOL_I18N_DIR': str(d), 'PYMOL_LANG': '', 'PYMOL_DATA': '',
            'PYMOL_PATH': '', 'PYMOL_I18N_PREFERENCE': str(d / 'pref.json'),
            'LC_ALL': 'C', 'LANG': 'C'})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.locale_patch = mock.patch.object(i18n, 'system_language', return_value=None)
        self.locale_patch.start()
        self.addCleanup(self.locale_patch.stop)


class TestActionsAndWidgets(QtLocalizerTestCase):
    def test_action_translated(self):
        action = QAction()
        action.setText('Hello')
        self.assertTrue(i18n_qt.localize_action(action, 'Hello'))
        self.assertEqual(action.text(), 'Hello')  # current language is en
        i18n.set_language('zh_CN')
        i18n_qt.retranslate_tree(action)
        self.assertEqual(action.text(), '你好')

    def test_label_translated(self):
        label = QLabel()
        label.setText('Close')
        i18n.set_language('zh_CN')
        i18n_qt.localize_widget(label)
        self.assertEqual(label.text(), '关闭')

    def test_lineedit_text_is_not_translated(self):
        edit = QLineEdit()
        edit.setText('user typed data')
        i18n.set_language('zh_CN')
        i18n_qt.localize_widget(edit)
        self.assertEqual(edit.text(), 'user typed data')

    def test_lineedit_placeholder_is_translated(self):
        edit = QLineEdit()
        edit.setPlaceholderText('Type here')
        i18n.set_language('zh_CN')
        i18n_qt.localize_widget(edit)
        self.assertEqual(edit.placeholderText(), '在此输入')

    def test_mark_untranslated_skips(self):
        action = QAction()
        action.setText('English')  # language-native name must stay
        i18n_qt.mark_untranslated(action)
        i18n.set_language('zh_CN')
        i18n_qt.localize_widget(action)
        self.assertEqual(action.text(), 'English')

    def test_tree_recursion(self):
        root = QWidget()
        menu = QMenu()
        menu.setTitle('File')
        root._children.append(menu)
        action = QAction()
        action.setText('Close')
        menu._children.append(action)
        i18n.set_language('zh_CN')
        i18n_qt.localize_tree(root)
        self.assertEqual(menu.title(), '文件')
        self.assertEqual(action.text(), '关闭')

    def test_application_edited_text_is_preserved(self):
        label = QLabel()
        label.setText('Close')
        i18n.set_language('zh_CN')
        i18n_qt.localize_widget(label)
        label.setText('changed by app')
        i18n_qt.retranslate_tree(label)
        self.assertEqual(label.text(), 'changed by app')


if __name__ == '__main__':
    unittest.main()
