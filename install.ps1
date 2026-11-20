<#
.SYNOPSIS
  安装「自动化科研」DSH Agent 预设到 .agent-presets\auto-research。

.DESCRIPTION
  把仓库里的 preset\ 目录复制到 DSH 读取预设的位置，默认：
    %APPDATA%\dsh-desktop\harness\.agent-presets\auto-research
  目标已存在时先整目录备份为 auto-research.backup-<时间戳>，不覆盖式损坏。

.PARAMETER Target
  自定义安装目录（默认按上面的 %APPDATA% 路径推导）。

.PARAMETER NoBackup
  跳过备份（仅在你确认目标可以被覆盖时使用）。

.EXAMPLE
  pwsh -File install.ps1

.EXAMPLE
  pwsh -File install.ps1 -Target D:\tmp\agent-presets\auto-research
#>
[CmdletBinding()]
param(
    [string]$Target,
    [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here 'preset'

if (-not (Test-Path (Join-Path $src 'preset.yml'))) {
    throw "未找到预设源目录：$src（请在仓库根目录运行本脚本）"
}

if (-not $Target -or $Target.Trim() -eq '') {
    if (-not $env:APPDATA) { throw '未设置 %APPDATA%，请用 -Target 指定安装目录' }
    $Target = Join-Path $env:APPDATA 'dsh-desktop\harness\.agent-presets\auto-research'
}

if ((Test-Path $Target) -and -not $NoBackup) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $bak = "$Target.backup-$stamp"
    Copy-Item -Path $Target -Destination $bak -Recurse -Force
    Write-Host "已备份现有预设 -> $bak" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
$robocopyArgs = @($src, $Target, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/XF', '*.bak', '/XD', '__pycache__')
& robocopy @robocopyArgs | Out-Null
$code = $LASTEXITCODE
if ($code -ge 8) { throw "复制失败（robocopy exit $code）" }

$count = (Get-ChildItem $Target -Recurse -File).Count
Write-Host ""
Write-Host "安装完成：$Target" -ForegroundColor Green
Write-Host "  文件数：$count"
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1) 重启 DSH Desktop（或新建会话）"
Write-Host "  2) Agent 预设下拉里选择「自动化科研」"
Write-Host "  3) 首次会话按提示授权右下角进度面板插件"
Write-Host ""
Write-Host "自检：python `"$Target\skills\auto-research\tools\selfcheck.py`" -v" -ForegroundColor DarkGray
