# Changelog

This changelog tracks changes made **on top of** the upstream Open-Source
PyMOL distribution (see `ChangeLog` for upstream history). Format follows
[Keep a Changelog](https://keepachangelog.com/); the project uses Semantic
Versioning.

## [Unreleased]

### Added

- Centralized internationalization (i18n) subsystem:
  - `modules/pymol/i18n.py` — pure-stdlib translator with English-source
    fallback, placeholder-safe formatting, plural and contextual lookups,
    language listeners, and language resolution
    (`set_language` → `--lang` → `PYMOL_LANG` → saved preference → OS locale
    → English).
  - `data/i18n/en.json` and `data/i18n/zh_CN.json` (Simplified Chinese,
    900+ UI strings for the shared menu bar, the Qt toolbar/docks/dialogs
    and their tooltips, and the right-click / context menus).
  - `modules/pmg_qt/i18n_qt.py` — Qt widget/menu localizer; `Display →
    Language` menu with live retranslation in the Qt GUI; dialogs are
    localized automatically on first show.
  - Tk menubar translation and a `Language` menu in `pmg_tk`.
  - **Internal GUI (C++/OpenGL) in Chinese**: `layer1/FontCJK.h` embeds a
    Noto Sans SC subset (7,265 chars, SIL OFL 1.1); `TextInit()` registers it
    as font 19 and `TextDrawStr`/`TextDrawStrAt` use it, so the object list and
    HUD render Chinese. `PopUp.cpp` now decodes UTF-8 per code point (2 cells
    for CJK), so the native popup menus work too.
  - `tools/gen_font_header.py` regenerates the embedded font asset;
    `scripts/build_windows.ps1` and `.github/workflows/build-wheel.yml` build a
    wheel with the CJK internal GUI.
  - **Internal GUI HUD in Chinese** (`鼠标模式`, `鼠标键`, `拾取`, `状态`, …):
    `tools/gen_hud_header.py` generates `layer1/HudTr.h` (UTF-8 escaped) from
    the catalog; `TextTr()` in `Text.cpp` looks a HUD string up using
    `$PYMOL_LANG`, which `pymol.i18n.set_language()` keeps in sync, so the HUD
    follows runtime language switches.
  - Mouse-mode names (`3-Button Viewing` → `三键视图`, …) are translated in
    `pymol/controlling.py`.

### Fixed

- `layer1/FontType.cpp`: the vector-font renderer dereferenced `RenderInfo`
  without a null check (`sampling = info->sampling`, `info->ortho`). The Ortho
  overlay path (`TextDrawStr` / `TextDrawStrAt`) passes `nullptr`, so using a
  TTF font there crashed with an access violation. Both sites are now
  null-safe, which is what allows vector (CJK) fonts in the internal GUI.
- `layer1/FontType.cpp`: vector-font text was always passed
  `isworldlabel = true`, which routed it to the 3D label CGO command even in
  the 2D Ortho overlay (blank popup menus). It is now derived from `rpos`, so
  overlay text uses the 2D texture quad like the bitmap fonts.
- `PopUp.cpp`: popup labels are now drawn per UTF-8 code point (2 cells wide
  for CJK) and the popup width is computed in character cells.
- `pymol/menu.py`: right-click menu labels are translated, including
  color-coded entries (e.g. `\933delete all` → `\933删除全部`).

### Known limitation

- The **context-sensitive** right-click menus (object/atom show/hide/color) are
  not reproduced: the picked atom lives in C++ and is not exposed to Python.
  The right-click "Main Pop-Up" is rendered as a native Qt menu (Chinese) via
  `modules/pmg_qt/qt_context_menu.py`; toggle with `qt_context_menu 0/1`.

### Fixed

- Switching back from a translated language to English no longer leaves
  menu titles stuck in the translated language (the menu's `menuAction()`
  was being localized twice and fighting the menu title).
  - `pymol --lang <code>` / `$PYMOL_LANG` support (`invocation.py`,
    `pymol/__init__.py`), and a `lang` PyMOL command.
- Tooling: `tools/i18n_lint.py` (catalog validation + coverage reporting).
- Tests: `testing/tests/i18n/` (runs without a PyMOL build).
- Docs: `docs/I18N.md`, `docs/PROJECT-ANALYSIS.md`, `docs/RELEASE.md`,
  `NOTICE`, `THIRD-PARTY-NOTICES.md`, `CONTRIBUTING.md`.

### Changed

- No C/C++ sources were modified; the above is pure Python + data + docs.

## [0.1.0] — fork baseline

- Upstream Open-Source PyMOL as published by Schrödinger, LLC (see
  `layer0/Version.h` for the exact `_PyMOL_VERSION` and `ChangeLog` for
  upstream history).
