<#
.SYNOPSIS
把科研自动化接进 Codex CLI（通过项目级 AGENTS.md）。
.PARAMETER Project
项目根目录；会在其 AGENTS.md 追加一段（幂等：已有标记则跳过）。
.PARAMETER DryRun
#>
param(
  [string]$Project = (Get-Location).Path,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$snip = Join-Path $PSScriptRoot "AGENTS.md.snippet"
$target = Join-Path $Project "AGENTS.md"
$marker = "## 科研自动化（auto-research）"

if (-not (Test-Path $snip)) { throw "找不到 AGENTS.md.snippet" }
$block = Get-Content $snip -Raw -Encoding UTF8

if ((Test-Path $target) -and ((Get-Content $target -Raw -Encoding UTF8) -like "*$marker*")) {
  Write-Host "AGENTS.md 已包含该段，跳过（幂等）"
  exit 0
}

Write-Host "目标 : $target"
if ($DryRun) { Write-Host "[DryRun] 不写入"; exit 0 }

if (-not (Test-Path $target)) { New-Item -ItemType File -Path $target -Force | Out-Null }
Add-Content -Path $target -Value ("`r`n" + $block) -Encoding UTF8
Write-Host "已追加。技能目录（供 tools 路径引用）：$pkg"
Write-Host "提示：Codex 的独立评审可用 codex exec 起干净子进程复算。"
