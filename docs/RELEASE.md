# Release Guide for a New Open-Source Project

This repository is the **Open-Source PyMOL** distribution. If you want to
publish it as a *new* open-source project (a fork with its own name and
governance), this document records the licensing decision, the required
cleanup, the versioning scheme and the release-verification checklist.

## 1. License decision: keep, do not relicense

**Verdict: retain the existing `LICENSE` verbatim; do not switch the whole
project to MIT / Apache-2.0 / BSD-3-Clause.**

Rationale:

* The current `LICENSE` ("Open-Source PyMOL Copyright Notice") is already a
  **permissive, BSD-like** license: use / copy / modify / distribute / modify
  and distribute for any purpose, without fee, with three conditions
  (keep the copyright notice; keep the license in documentation; do not use
  "Schrodinger, LLC" for endorsement) plus a disclaimer of warranties. It is
  open-source in substance and compatible with MIT/BSD/Apache components.
* The copyright in the vast majority of the code belongs to **Schrodinger,
  LLC** and **Warren L. DeLano** (and third parties in `contrib/`). You cannot
  unilaterally relicense code you do not own. The license itself requires that
  copyright and permission notices remain in all copies.
* Mixing a second, different license over the same tree is more confusing and
  more risky than it is worth. New files authored for this fork are therefore
  published under the **same** BSD-like terms.

What *is* required for a fork:

* Keep `LICENSE` unchanged.
* Add a `NOTICE` file (see [`NOTICE`](../NOTICE)) restating upstream
  authorship and the trademark status.
* Add [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) listing every
  bundled third-party component and its license.
* **Rebrand** — the PyMOL trademark is retained by Schrodinger; a derivative
  must be "plainly distinguished" from Schrodinger's PyMOL products. Allowed
  phrases include "Based on PyMOL(TM)." / "Contains PyMOL(TM) source code.",
  always with the footnote "PyMOL is a trademark of Schrodinger, LLC."

## 2. Required cleanup / rebrand checklist

| # | Item | Action |
| --- | --- | --- |
| 1 | Project name & package | rename `pyproject.toml` `[project].name` ("pymol" → new name), the `pymol` entry-point script, and any `setup.py`/`README` occurrences of the product name |
| 2 | Executable & env vars | `pymol` launcher, `PYMOL_PATH`, `PYMOL_DATA`, `PYMOL_SCRIPTS` are technical names; keep them but document the rebrand in `README` |
| 3 | `README.md` / `README` | update title, add "Based on PyMOL(TM)" + trademark footnote, update installation/contributing links |
| 4 | `AUTHORS` | preserve upstream authors; append the fork's contributors |
| 5 | `SECURITY.md` | replace `security+pymol@schrodinger.com` with the fork's contact; clarify upstream vs fork support |
| 6 | `.github/ISSUE_TEMPLATE/*` | update links to point to the fork's repository |
| 7 | `.github/workflows/build.yml` | the Windows/macOS jobs use the `schrodinger` conda channel; verify every package is also available on `conda-forge`, or document the requirement |
| 8 | `ChangeLog` | keep upstream history; add a fork changelog (`CHANGELOG.md`) from the fork point |
| 9 | `data/` third-party | `data/startup/apbs_gui/*.py` are BSD-2-Clause — list them in `THIRD-PARTY-NOTICES.md` |
| 10 | Scratch/build dirs | remove `.analysis/`, `build/`, `dist/`, `*.egg-info`, `__pycache__` before tagging |
| 11 | CI badges & URLs | update the badge/links in `README.md` from `schrodinger/pymol-open-source` to the fork |

## 3. Version management

* **Scheme**: Semantic Versioning (`MAJOR.MINOR.PATCH`) for the fork, e.g.
  `0.1.0` as the first fork release. Pre-releases use `0.1.0-rc1`.
* **Upstream base**: keep a machine-readable record of the exact upstream
  revision the fork is based on (e.g. `UPSTREAM_BASE` in `CHANGELOG.md` or a
  `REVISION` file) so security fixes can be re-based.
* **Version source**: the *runtime* version still comes from
  `layer0/Version.h` (`_PyMOL_VERSION`); the fork's *release* version is a
  packaging-level value (`pyproject.toml` / tag). Document this split so users
  can tell "which upstream" and "which fork".
* **Tags**: `v0.1.0`, `v0.1.0-rc1`; branches `main` for releases,
  `develop`/feature branches otherwise.
* **Changelog**: maintain `CHANGELOG.md` (Keep a Changelog format); every PR
  that changes user-visible behavior adds an entry.

## 4. Verification checklist before release

- [ ] `python -m unittest discover -s testing/tests/i18n -p 'test_*.py'` passes.
- [ ] `python tools/i18n_lint.py` reports `0 error(s)`.
- [ ] `python tools/i18n_lint.py --coverage <gui_strings.json>` coverage recorded.
- [ ] No C/C++/header file changed (SHA-256 snapshot check) — or, if one did,
      it is reviewed and CI rebuilds it on Linux/macOS/Windows.
- [ ] `python -m compileall` (or an equivalent syntax check) over
      `modules/ tools/ testing/` reports no new syntax errors.
- [ ] CI (`pip install -v --config-settings testing=True .[dev]` then
      `pymol -ckqy testing/testing.py --run all`) is green on all three OSes.
- [ ] Manual smoke test: launch Qt GUI, switch `Display → Language →
      简体中文`, confirm menus/toolbar/dialogs update and the choice survives
      a restart; `pymol --lang zh_CN` and `PYMOL_LANG=zh_CN` both work.
- [ ] `LICENSE`, `NOTICE`, `THIRD-PARTY-NOTICES.md` are present and current.
- [ ] No `.analysis/`, `build/`, `__pycache__`, `*.egg-info` in the archive.
- [ ] The repository name/URLs/badges/emails are rebranded (see §2).
- [ ] A signed release tag is pushed with a changelog entry.

## 5. Suggested publishing steps

1. Finish §2 cleanup and §4 verification.
2. Set the fork name + first version in `pyproject.toml` and `CHANGELOG.md`.
3. Tag `v0.1.0`; attach source and (CI-built) binary wheels.
4. Publish docs, stating clearly it is "Based on PyMOL(TM)".
