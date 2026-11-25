# Contributing

Thank you for your interest in contributing! Please see `DEVELOPERS` for the
upstream developer notice and `INSTALL` for build instructions.

## Quick start

```
# build with C++ unit tests (recommended for development)
pip install --verbose --no-build-isolation --config-settings testing=True .

# run the Python regression suite
pymol -ckqy testing/testing.py --run all

# run the internationalization tests (no build required)
python -m unittest discover -s testing/tests/i18n -p 'test_*.py'

# validate the translation catalogs
python tools/i18n_lint.py
```

## Style and process

* Open an issue before starting large changes.
* Python code targets the same Python versions as the CI matrix (3.9+).
* Keep C++ changes C++17-compatible and buildable on all three CI platforms.
* Add or update tests for behavior changes.
* **Translations**: edit `data/i18n/<code>.json` and run
  `python tools/i18n_lint.py`; keep `{placeholders}`, `%s`, and trailing `...`
  intact. New user-visible strings may be added to `data/i18n/en.json` with
  English text.

## License

Contributions are licensed under the same permissive BSD-like terms as the
project (`LICENSE`). By submitting a contribution you agree to this. See
`DEVELOPERS` and `NOTICE` for attribution and trademark requirements.

## Code of conduct

Be respectful and constructive. Report security issues privately (see
`SECURITY.md`); do not file them as public issues.
