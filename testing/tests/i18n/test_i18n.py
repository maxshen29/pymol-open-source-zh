# ---------------------------------------------------------------------
# Unit tests for pymol.i18n.  These run on a stock CPython without the
# PyMOL C extension: the module under test is loaded directly from the
# source tree (modules/pymol/i18n.py) via importlib.
# ---------------------------------------------------------------------
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
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
lint = _load('_i18n_lint_under_test', 'tools', 'i18n_lint.py')


def write_catalog(directory, code, strings=None, **meta):
    directory = pathlib.Path(directory)
    data = {'meta': {'language': code,
                     'native_name': meta.get('native_name', code),
                     'english_name': meta.get('english_name', code),
                     'source_language': 'en',
                     'fallback': 'en',
                     'version': '1.0'},
            'strings': dict(strings or {})}
    (directory / (code + '.json')).write_text(
        json.dumps(data, ensure_ascii=False), encoding='utf-8')


class I18nTestCase(unittest.TestCase):
    def setUp(self):
        i18n.reset_state()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.catalog_dir = pathlib.Path(self._tmp.name)
        write_catalog(self.catalog_dir, 'en')
        write_catalog(self.catalog_dir, 'zh_CN', {
            'File': '文件',
            'Hello {name}': '你好 {name}',
            'I have {n} atoms': '我有 {n} 个原子',
            'Close': '关闭',
        }, native_name='简体中文')
        write_catalog(self.catalog_dir, 'fr', {
            'File': 'Fichier',
            'Hello {name}': 'Bonjour {name}',
        }, native_name='Français')
        # isolate the environment from the host machine
        self.env_patch = mock.patch.dict(os.environ, {
            'PYMOL_I18N_DIR': str(self.catalog_dir),
            'PYMOL_LANG': '',
            'PYMOL_DATA': '',
            'PYMOL_PATH': '',
            'PYMOL_I18N_PREFERENCE': str(self.catalog_dir / 'pref.json'),
            'LC_ALL': 'C', 'LC_MESSAGES': 'C', 'LANG': 'C', 'LANGUAGE': 'C',
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        # make OS locale detection deterministic in every test
        self.locale_patch = mock.patch.object(i18n, 'system_language', return_value=None)
        self.locale_patch.start()
        self.addCleanup(self.locale_patch.stop)


class TestNormalize(I18nTestCase):
    def test_aliases(self):
        self.assertEqual(i18n.normalize_language('zh'), 'zh_CN')
        self.assertEqual(i18n.normalize_language('zh-cn'), 'zh_CN')
        self.assertEqual(i18n.normalize_language('zh_Hans'), 'zh_CN')
        self.assertEqual(i18n.normalize_language('en-US'), 'en')
        self.assertEqual(i18n.normalize_language('en_US'), 'en')
        self.assertEqual(i18n.normalize_language('zh_TW'), 'zh_TW')

    def test_encoding_suffix_stripped(self):
        self.assertEqual(i18n.normalize_language('zh_CN.UTF-8'), 'zh_CN')

    def test_garbage(self):
        self.assertIsNone(i18n.normalize_language(''))
        self.assertIsNone(i18n.normalize_language(None))
        self.assertEqual(i18n.normalize_language('Xx'), 'xx')


class TestCatalogLoading(I18nTestCase):
    def test_available_languages(self):
        codes = [e['code'] for e in i18n.available_languages()]
        self.assertIn('en', codes)
        self.assertIn('zh_CN', codes)
        self.assertIn('fr', codes)
        self.assertEqual(codes[0], 'en')

    def test_catalog_meta(self):
        meta = i18n.catalog_meta('zh_CN')
        self.assertEqual(meta['language'], 'zh_CN')
        self.assertEqual(meta['native_name'], '简体中文')

    def test_language_display_name(self):
        self.assertEqual(i18n.language_display_name('zh_CN'), '简体中文')


class TestTranslation(I18nTestCase):
    def test_identity_in_english(self):
        i18n.set_language('en')
        self.assertEqual(i18n.tr('File'), 'File')

    def test_translation(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('File'), '文件')

    def test_fallback_to_source_when_missing(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('Not Translated'), 'Not Translated')

    def test_fallback_to_english_catalog(self):
        # 'Close' only exists in zh_CN here; use fr which lacks it -> 'Close'
        i18n.set_language('fr')
        self.assertEqual(i18n.tr('Close'), 'Close')

    def test_non_string_passthrough(self):
        self.assertIsNone(i18n.tr(None))
        self.assertEqual(i18n.tr(''), '')
        self.assertEqual(i18n.tr(123), 123)

    def test_placeholder_interpolation(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('Hello {name}', name='小明'), '你好 小明')

    def test_missing_placeholder_is_preserved(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('Hello {name}'), '你好 {name}')

    def test_extra_values_are_ignored(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('File', bogus=1), '文件')

    def test_mnemonic_ampersand_lookup(self):
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('&File'), '文件')

    def test_plural_mapping(self):
        write_catalog(self.catalog_dir, 'zh_CN', {
            'File': '文件',
            'I have {n} atoms': {'one': '我有 {n} 个原子', 'other': '我有 {n} 个原子'},
        }, native_name='简体中文')
        i18n.reset_state()
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.trn('1 atom', 'I have {n} atoms', 1, n=1), '我有 1 个原子')
        self.assertEqual(i18n.trn('1 atom', 'I have {n} atoms', 5, n=5), '我有 5 个原子')

    def test_context(self):
        write_catalog(self.catalog_dir, 'zh_CN', {
            'File': '文件',
            'Close': '关闭',
            'menu\x04Close': '关闭菜单',
        }, native_name='简体中文')
        i18n.reset_state()
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.trc('menu', 'Close'), '关闭菜单')
        self.assertEqual(i18n.trc('other', 'Close'), '关闭')

    def test_has_translation(self):
        self.assertTrue(i18n.has_translation('File', 'en'))
        self.assertTrue(i18n.has_translation('File', 'zh_CN'))
        self.assertTrue(i18n.has_translation('File', 'fr'))
        self.assertFalse(i18n.has_translation('Close', 'fr'))

    def test_title_case_fallback(self):
        write_catalog(self.catalog_dir, 'zh_CN', {'Zoom': '缩放'},
                      native_name='简体中文')
        i18n.reset_state()
        i18n.set_language('zh_CN')
        self.assertEqual(i18n.tr('zoom'), '缩放')
        self.assertEqual(i18n.tr('Zoom'), '缩放')


class TestLanguageResolution(I18nTestCase):
    def test_default_is_english(self):
        self.assertEqual(i18n.get_language(), 'en')

    def test_env_variable_wins(self):
        with mock.patch.dict(os.environ, {'PYMOL_LANG': 'zh_CN'}):
            i18n.reset_state()
            self.assertEqual(i18n.get_language(), 'zh_CN')

    def test_unsupported_env_falls_back(self):
        with mock.patch.dict(os.environ, {'PYMOL_LANG': 'de'}):
            i18n.reset_state()
            self.assertEqual(i18n.get_language(), 'en')

    def test_init_from_argv(self):
        i18n.init(['--lang', 'zh_CN'])
        self.assertEqual(i18n.get_language(), 'zh_CN')

    def test_init_from_argv_equals(self):
        i18n.init(['--lang=fr'])
        self.assertEqual(i18n.get_language(), 'fr')

    def test_init_from_options(self):
        class Options:
            lang = 'zh_CN'
        i18n.init(options=Options())
        self.assertEqual(i18n.get_language(), 'zh_CN')

    def test_system_locale_used_when_supported(self):
        with mock.patch.object(i18n, 'system_language', return_value='zh_CN'):
            i18n.reset_state()
            self.assertEqual(i18n.get_language(), 'zh_CN')

    def test_system_locale_ignored_when_unsupported(self):
        with mock.patch.object(i18n, 'system_language', return_value='de_DE'):
            i18n.reset_state()
            self.assertEqual(i18n.get_language(), 'en')


class TestPreferences(I18nTestCase):
    def test_save_and_read(self):
        pref = self.catalog_dir / 'pref.json'
        with mock.patch.dict(os.environ, {'PYMOL_I18N_PREFERENCE': str(pref)}):
            self.assertTrue(i18n.save_preference('zh_CN'))
            self.assertEqual(i18n.read_preference(), 'zh_CN')

    def test_preference_used_as_default(self):
        pref = self.catalog_dir / 'pref.json'
        pref.write_text(json.dumps({'language': 'fr'}), encoding='utf-8')
        with mock.patch.dict(os.environ, {'PYMOL_I18N_PREFERENCE': str(pref)}):
            i18n.reset_state()
            self.assertEqual(i18n.get_language(), 'fr')

    def test_set_language_persist(self):
        pref = self.catalog_dir / 'pref.json'
        with mock.patch.dict(os.environ, {'PYMOL_I18N_PREFERENCE': str(pref)}):
            i18n.set_language('zh_CN', persist=True)
            self.assertEqual(i18n.read_preference(), 'zh_CN')


class TestListenerAndMissing(I18nTestCase):
    def test_listener_notified_once(self):
        seen = []
        i18n.add_listener(seen.append)
        i18n.set_language('zh_CN')
        self.assertEqual(seen, ['zh_CN'])
        i18n.set_language('zh_CN')  # no change -> no notification
        self.assertEqual(seen, ['zh_CN'])
        i18n.remove_listener(seen.append)

    def test_broken_listener_does_not_break(self):
        def boom(code):
            raise RuntimeError('nope')
        i18n.add_listener(boom)
        try:
            i18n.set_language('zh_CN')
        finally:
            i18n.remove_listener(boom)
        self.assertEqual(i18n.get_language(), 'zh_CN')

    def test_missing_report_collects_with_debug(self):
        with mock.patch.dict(os.environ, {'PYMOL_I18N_DEBUG': '1'}):
            i18n.reset_state()
            i18n.set_language('zh_CN')
            i18n.tr('Completely Unknown String')
            self.assertIn('Completely Unknown String', i18n.missing_report())


class TestShippedCatalogs(unittest.TestCase):
    def setUp(self):
        i18n.reset_state()
        self.catalog_dir = ROOT / 'data' / 'i18n'

    def test_catalogs_exist(self):
        self.assertTrue((self.catalog_dir / 'en.json').is_file())
        self.assertTrue((self.catalog_dir / 'zh_CN.json').is_file())

    def test_shipped_catalogs_lint_clean(self):
        problems, catalogs, source = lint.lint_dir(str(self.catalog_dir))
        errors = [p for p in problems if p.level == 'error']
        self.assertEqual(errors, [], 'catalog errors: %r' % errors)
        self.assertIn('zh_CN', catalogs)

    def test_source_keys_covered(self):
        problems, catalogs, source = lint.lint_dir(str(self.catalog_dir))
        self.assertEqual([p for p in problems if p.level == 'error'], [])
        zh = json.loads((self.catalog_dir / 'zh_CN.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(zh['strings']), 100)


if __name__ == '__main__':
    unittest.main()
