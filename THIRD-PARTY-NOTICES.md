# Third-Party Notices

This distribution bundles or builds against third-party code. Each component
is distributed under its own license, reproduced or referenced below. The
licenses below were detected from the source tree; **verify them against the
upstream repositories before distribution.**

## Bundled in this tree

| Component | Location | License | Copyright |
| --- | --- | --- | --- |
| Champ (cheminformatics core) | `contrib/champ/` | Open-Source PyMOL license (see `contrib/champ/LICENSE`) | Warren L. DeLano / Schrödinger, LLC |
| mmtf-c (MMTF parser) | `contrib/mmtf-c/` | Apache License 2.0 (header only) | RCSB, 2016 |
| pocketfft | `contrib/pocketfft/` | BSD-3-Clause (see `contrib/pocketfft/LICENSE.md`) | Max-Planck-Society; also Peter Bell, MIT/FFTW-derived (Matteo Frigo, MIT) |
| VMD molfile plugins | `contrib/uiuc/plugins/` | University of Illinois Open Source License (see `contrib/uiuc/plugins/LICENSE`); some plugins under NAMD, TkCon or other terms | Board of Trustees of the University of Illinois; D.E. Shaw Research; Georgia Institute of Technology; Regents of the University of California |
| OpenVR support | `contrib/vr/` | MIT (see `contrib/vr/LICENSE`) | EPAM Systems, Inc., 2018 |
| TNT (linear algebra) | `include/tnt/` | Public domain (NIST, 17 U.S.C. §105) | National Institute of Standards and Technology |
| GLUT bitmap fonts | `layer1/FontGLUT.h` | GLUT/freeglut terms | Mark J. Kilgard, 1994 |
| TTF font data | `layer1/FontTTF2.h` | SIL font terms (verify) | SIL International, 2003–2005 |
| Noto Sans SC (CJK subset) | `layer1/FontCJK.h` | SIL Open Font License 1.1 | Copyright 2014–2021 Adobe (http://www.adobe.com/), with Reserved Font Name "Source" |
| Marching cubes | `layer0/marching_cubes.cpp` | (verify upstream) | The ilastik development team, 2018 |
| cealign module | `layer0/ccealignmodule.cpp` | Open-Source PyMOL license | Jason Vertrees |
| Mersenne Twister RNG | `ov/src/OVRandom.cpp` | BSD-3-Clause | Makoto Matsumoto and Takuji Nishimura |
| jQuery (web example only) | `modules/web/examples/sample13/jquery.js` | MIT (and GPL, dual) | John Resig |
| APBS GUI scripts | `data/startup/apbs_gui/*.py` | BSD-2-Clause (header) | APBS contributors |

## Build-time dependencies (not bundled)

Retrieved by the build system or the package manager, each under its own
license: CMake, GLM, GLEW, freetype, libpng, libxml2, msgpack-c, mmtf-cpp,
nlohmann-json, netcdf, Catch2, OpenVR, Viskores, Qt/PySide6, Pmw, NumPy.

## Notes

* `contrib/mmtf-c/` has no standalone `LICENSE` file; its Apache-2.0 notice
  lives in the source headers. Adding a `contrib/mmtf-c/LICENSE` is
  recommended before distribution.
* `data/shaders/` and the sample structure files in `data/` carry no explicit
  per-file license header; they are part of the PyMOL distribution and fall
  under the root `LICENSE`.
* No GPL/AGPL/LGPL code was detected in the compiled application; the only
  "GPL" keyword hits are the dual-licensed jQuery example file under
  `modules/web/examples/`.
