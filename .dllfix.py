"""Copy the DLL dependency closure of PyMOL's extensions into their
package directories, so the portable bundle works on a machine without the
conda build environment.
"""
import pathlib
import shutil
import sys

import pefile

BUNDLE = pathlib.Path(r"C:\project\pymol-open-source\pymol安装包\python\Lib\site-packages")
CONDA_LIB = pathlib.Path(r"C:\Users\ssjl\mamba\envs\pymol-build\Library\bin")
CONDA_ROOT = pathlib.Path(r"C:\Users\ssjl\mamba\envs\pymol-build")

TARGETS = [
    BUNDLE / "pymol" / "_cmd.cp312-win_amd64.pyd",
    BUNDLE / "chempy" / "champ" / "_champ.cp312-win_amd64.pyd",
]
SEARCH = [CONDA_LIB, CONDA_ROOT / "DLLs", CONDA_ROOT / "Library" / "lib"]


def imports_of(path):
    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        return [e.dll.decode("ascii", "ignore")
                for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
    finally:
        pe.close()


def main():
    copied = {}
    for target in TARGETS:
        if not target.is_file():
            print("missing:", target)
            continue
        dest = target.parent
        queue = [target]
        seen = set()
        while queue:
            current = queue.pop()
            for dll in imports_of(current):
                if dll.lower() in seen:
                    continue
                seen.add(dll.lower())
                for directory in SEARCH:
                    candidate = directory / dll
                    if candidate.is_file():
                        out = dest / dll
                        if not out.is_file():
                            shutil.copy2(candidate, out)
                            copied[dll] = out
                        queue.append(out)
                        break
    for name in sorted(copied):
        print("copied", name, "%.2f MB" % (copied[name].stat().st_size / 1048576))
    print("total:", len(copied), "DLLs, %.1f MB"
          % (sum(p.stat().st_size for p in copied.values()) / 1048576))


if __name__ == "__main__":
    main()
