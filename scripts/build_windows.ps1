# ---------------------------------------------------------------------------
# Build PyMOL (with the Chinese internal GUI) on Windows.
#
# Requirements:
#   * Visual Studio 2019/2022 Build Tools with the C++ workload (MSVC).
#     Install (admin): https://visualstudio.microsoft.com/visual-cpp-build-tools/
#     Select "Desktop development with C++".
#   * Miniforge (installed automatically below if missing).
#
# Usage (PowerShell):
#   .\scripts\build_windows.ps1
#
# The resulting wheel is written to .\dist\ and can be installed into the
# portable bundle with:
#   python\python.exe -m pip install --force-reinstall dist\*.whl
# ---------------------------------------------------------------------------
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

function Fail($msg) { Write-Host "`n[ERROR] $msg`n" -ForegroundColor Red; exit 1 }

# --- 1. MSVC ---------------------------------------------------------------
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$hasMsvc = $false
if (Test-Path $vswhere) {
    $path = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($path) { $hasMsvc = $true }
}
if (-not $hasMsvc) {
    Fail @"
MSVC (Visual Studio C++ Build Tools) was not found.

Install it first (requires administrator rights), then re-run this script:
  https://visualstudio.microsoft.com/visual-cpp-build-tools/
Choose the "Desktop development with C++" workload.
"@
}
Write-Host "[ok] MSVC found" -ForegroundColor Green

# --- 2. Miniforge (provides the native deps) --------------------------------
$miniforge = "$env:USERPROFILE\miniforge3"
if (-not (Test-Path "$miniforge\Scripts\conda.exe")) {
    Write-Host "[..] Miniforge not found, installing to $miniforge"
    $installer = Join-Path $env:TEMP 'Miniforge3-Windows-x86_64.exe'
    Invoke-WebRequest -Uri 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe' -OutFile $installer
    Start-Process -FilePath $installer -ArgumentList "/S /D=$miniforge" -Wait
}
$conda = "$miniforge\Scripts\conda.exe"
if (-not (Test-Path $conda)) { Fail "Miniforge installation failed" }

# --- 3. Build environment ---------------------------------------------------
$envName = 'pymol-build'
Write-Host "[..] Creating conda env '$envName' (this may take several minutes)"
& $conda create -y -n $envName -c conda-forge --override-channels `
    python=3.12 pip setuptools cmake freetype glew glm libpng numpy
if ($LASTEXITCODE -ne 0) { Fail "conda create failed" }

$py = "$miniforge\envs\$envName\python.exe"
if (-not (Test-Path $py)) { Fail "conda env python not found" }

# setup.py finds the native deps through CONDA_PREFIX / PREFIX_PATH
$env:CONDA_PREFIX = "$miniforge\envs\$envName"
$env:PREFIX_PATH = "$env:CONDA_PREFIX\Library"

# --- 4. Build the wheel (minimal feature set: no glTF/msgpack/XML needed) ---
Push-Location $repo
try {
    Write-Host "[..] Building PyMOL wheel (compiles C++ with the embedded CJK font)"
    & $py -m pip install --no-input --upgrade setuptools cmake numpy
    & $py -m pip install --no-input --no-build-isolation `
        --config-settings testing=False `
        --config-settings json=False `
        --config-settings use-msgpackc=no `
        --config-settings libxml=no `
        -w dist .
    if ($LASTEXITCODE -ne 0) { Fail "wheel build failed" }
} finally {
    Pop-Location
}

$wheel = Get-ChildItem "$repo\dist\pymol_open_source-*.whl" | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $wheel) { Fail "no wheel produced" }

Write-Host "`n[ok] Built: $($wheel.FullName)" -ForegroundColor Green
Write-Host "`nInstall into the portable bundle:"
Write-Host "  `"$repo\pymol安装包\python\python.exe`" -m pip install --force-reinstall `"$($wheel.FullName)`""
