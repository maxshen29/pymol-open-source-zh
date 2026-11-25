# ---------------------------------------------------------------------------
# Publish this fork to your own GitHub repository.
#
#   .\scripts\publish.ps1
#
# When git asks for credentials, use:
#     Username: your GitHub user name
#     Password: a Personal Access Token (NOT your account password)
#
# Create a token (Fine-grained, repository access = only this repo,
# Permissions -> Contents: Read and write):
#     https://github.com/settings/tokens?type=beta
#
# The target repository already contains a GitHub "Initial commit" whose
# history is unrelated to the upstream PyMOL history, so the first push uses
# --force.  Later pushes don't need it.
# ---------------------------------------------------------------------------
param(
    [string]$RemoteUrl = 'https://github.com/maxshen29/pymol-open-source-zh.git',
    [string]$Branch = 'main',
    [string]$GitName = 'maxshen29',
    [string]$GitEmail = 'maxshen29@users.noreply.github.com'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host ''
    Write-Host 'git was not found. Install Git for Windows first:' -ForegroundColor Red
    Write-Host '  https://git-scm.com/download/win'
    Write-Host ''
    exit 1
}

Push-Location $repo
try {
    Write-Host "[..] committing in $repo"

    git config user.name  $GitName
    git config user.email $GitEmail

    # Keep the upstream remote, point "origin" at your own repository
    $remotes = @(git remote)
    if ($remotes -contains 'origin') {
        $url = git remote get-url origin
        if ($url -notmatch 'maxshen29') {
            if ($remotes -contains 'upstream') { git remote remove origin }
            else { git remote rename origin upstream }
        }
    }
    $remotes = @(git remote)
    if ($remotes -contains 'origin') {
        git remote set-url origin $RemoteUrl
    } else {
        git remote add origin $RemoteUrl
    }
    Write-Host "[ok] origin -> $RemoteUrl"

    git add -A
    Write-Host "[..] staged files (first 30):"
    git status --short | Select-Object -First 30

    git commit -m "PyMOL 中文版：完整中文界面（Qt + 内部 GUI + HUD）与 i18n 架构" `
        -m "Based on Open-Source PyMOL 3.2.0a. Adds a catalog-driven i18n layer
(en + zh_CN), language switching (GUI / --lang / PYMOL_LANG / lang command),
an embedded Noto Sans SC subset so the C++ internal GUI can render Chinese,
Chinese popup menus and HUD, and two fixes to the vector-font renderer."

    Write-Host ''
    Write-Host 'When git asks for credentials:' -ForegroundColor Yellow
    Write-Host '  Username : your GitHub user name'
    Write-Host '  Password : a Personal Access Token (NOT your account password)'
    Write-Host ''
    git push -u origin "HEAD:$Branch" --force

    Write-Host ''
    Write-Host "[ok] published: https://github.com/maxshen29/pymol-open-source-zh" -ForegroundColor Green
} finally {
    Pop-Location
}
