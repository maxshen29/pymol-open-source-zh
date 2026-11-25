# Project Analysis: Open-Source PyMOL

> 对 `pymol-open-source` 工作区的结构化分析（结构、技术栈、核心功能、编译流程、依赖、授权）。
> 生成于 2026-11-25；统计口径为源码文件与逻辑行数（非空白/注释）。

## 1. 一句话定位

PyMOL 是「Python 增强的分子可视化程序」，擅长蛋白质、小分子、密度图、表面与轨迹的
3D 可视化，并包含分子编辑、光线追踪与动画制作。本仓库是 Schrodinger 维护的
**开源基础版（Open-Source PyMOL）**，商业版（Incentive PyMOL）在其上叠加维护与支持。

## 2. 规模与语言构成

| 目录 | 用途 | Python 文件/行 | C/C++ 源/行 | C/C++ 头/行 |
| --- | --- | ---: | ---: | ---: |
| `modules/` | Python 应用层（pymol、pymol2、pmg_qt、pmg_tk、chempy、web） | 192 / 87,645 | — | — |
| `layer0/` | C++ 核心（分子对象、渲染、选择） | — | 40 / 23,983 | 73 / 14,081 |
| `layer1/` | C++ 命令/API/内置 GUI | — | 50 / 78,066 | 51 / 265,671 |
| `layer2/` | C++ 场景/坐标/渲染管线 | — | 53 / 68,900 | 52 / 4,519 |
| `layer3/` | C++ 计算几何/依赖 | — | 16 / 39,696 | 18 / 2,474 |
| `layer4/` | C++ 扩展（cealign 等） | — | 3 / 7,886 | 3 / 93 |
| `layer5/` | C++ 模块（docking/动画） | — | 3 / 5,262 | 3 / 664 |
| `layerGraphics/` | 图形抽象层 | — | 1 / 325 | 6 / 423 |
| `layerCTest/` | Catch2 单测 | — | 24 / 2,708 | 2 / 100 |
| `ov/` | OpenVR/OpenGL 工具 | — | 8 / 2,881 | 13 / 813 |
| `include/` | 头文件（pymol 自有 + TNT 公共领域） | — | — | 36 / 11,426 |
| `contrib/` | 第三方贡献（champ、mmtf-c、pocketfft、uiuc、vr） | 8 / 2,406 | 88 / 55,850 | 52 / 18,761 |
| `data/` | 运行时数据（着色器、chempy、皮肤、启动脚本） | 13 / 3,217 | — | — |
| `testing/` + `test/` | 回归测试与夹具 | 174 / 16,275 | — | — |
| `examples/` | 示例脚本 | 47 / 3,642 | — | — |

总计约 **1,587 个文件 / 113 万行**，其中 C/C++ 头文件体量最大（layer1 头文件含大量内联/生成代码）。

## 3. 分层与绑定

`layer0`（分子/渲染核心）→ `layer1`（命令、选择、内部 GUI）→ `layer2/3`（场景/几何）
→ `layer4/5`（扩展）→ `layerGraphics`（图形抽象）。Python 侧 `modules/pymol` 通过
CPython 扩展 `_cmd`（另有 `_guessing`、`chempy.champ`、`pymol2` 等）暴露 C++ 能力，
入口在 `setup.py` 的 `CMakeExtension` 定义，由 `_custom_build/backend.py` 驱动
`cmake` 构建并链接 GL/GLEW/freetype/libpng 等。

## 4. 核心功能

- **可视化**：卡通/棒/球棍/表面/网格/点/线等多种表征，光线追踪（POV-Ray、内置 ray）、
  立体、着色器（`data/shaders`，44 个）。
- **分子编辑**：Builder、片段与残基拼接、突变、电荷/价态编辑（`pymol/editing.py`）。
- **分析与测量**：氢键、距离/角度、空腔、静电势（APBS）、密度图（isosurface/volume）。
- **动画与电影**：相机/状态/场景、轨迹（MMTF/NetCDF）、MPEG/PNG 序列导出。
- **文件格式**：PDB/CIF/MMTF/mol2 等导入，会话、glTF/GLB/STL/USD 等导出。
- **脚本与插件**：`pymol.cmd` 命令 API、`pymol2.PyMOL` 头less API、旧式插件系统。

## 5. 构建与测试流程

- 构建后端：`pip install .`（`pyproject.toml` → `_custom_build/backend.py` →
  `setup.py` → `cmake`）。版本号读取自 `layer0/Version.h` 的 `_PyMOL_VERSION`。
- 关键可选参数：`--config-settings testing=True`（编译 Catch2 单测）、
  `--config-settings json=True`（glTF/GLB）、`--use-msgpackc`、`--libxml`、
  `--glut`、`--openvr`、`--use-viskores`。
- CI（`.github/workflows/build.yml`）：Linux（apt 依赖）/ Windows（conda-forge +
  schrodinger channel）/ macOS（miniforge），Python 3.11–3.14 矩阵，构建后运行
  `pymol -ckqy testing/testing.py --run all`。
- 测试体系：`testing/testing.py`（回归，含 `testing/tests/**`）、`layerCTest`（Catch2）、
  `test/`（图形基线）。

## 6. 依赖关系

- **必须**：C++17、CMake ≥3.13、Python ≥3.9、numpy ≥2.0、OpenGL、GLEW、libpng、freetype。
- **可选**：GLUT（Tk/旧 GUI）、libxml2（COLLADA）、msgpack-c+mmtf-cpp（MMTF 快速读写）、
  glm、catch2、nlohmann-json（glTF）、netcdf、openvr、viskores。
- **内嵌第三方**：`contrib/champ`（PyMOL 许可）、`contrib/mmtf-c`（Apache-2.0）、
  `contrib/pocketfft`（BSD-3）、`contrib/uiuc`（UIUC 开源许可）、`contrib/vr`（MIT）、
  `include/tnt`（NIST 公共领域）。
- **GUI 运行时**：Qt 优先（PySide6/PyQt），Tk（Pmw）回退，另含 `modules/web` 早期 Web 前端。

## 7. 授权协议

根目录 `LICENSE` 为「Open-Source PyMOL」**BSD-like 宽松许可证**（允许使用/复制/修改/
再分发，仅要求保留版权与许可声明、不得以 Schrodinger 名义背书）＋**PyMOL 商标条款**
（衍生作品须与 Schrodinger 发行的 PyMOL 产品明确区分）。详见
[`docs/RELEASE.md`](RELEASE.md) 对「保留 vs 换证」的结论与发布清单。

## 8. 本机可编译性结论

当前机器 **无法编译 C++ 扩展**：无 MSVC/cl、无 CMake、无 conda、PATH 无 Python。
因此本次改造聚焦纯 Python 层（i18n），并承诺：
- 改动未触碰任何 C/C++/头文件（以 SHA-256 快照比对验证通过）；
- 所有 Python 通过语法编译检查；
- 新功能以不依赖 C 扩展的 `unittest` 覆盖，并可在 CI（Linux/macOS/Windows）上
  随上游 `pip install` 与 `pymol -ckqy testing/testing.py --run all` 一起验证。
