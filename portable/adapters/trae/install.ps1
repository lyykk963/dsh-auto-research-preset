<#
.SYNOPSIS
把科研自动化装到 Trae（ASCII 技能名，避开中文 name 的 key 依赖）。
.PARAMETER DryRun
#>
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dest = Join-Path $env:USERPROFILE ".trae-cn\skills\sci-autoresearch"

if (-not (Test-Path (Join-Path $pkg "SKILL.md"))) { throw "找不到 SKILL.md" }
Write-Host "源   : $pkg"
Write-Host "目标 : $dest"
if ($DryRun) { Write-Host "[DryRun] 不执行"; exit 0 }

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $pkg "*") -Destination $dest -Recurse -Force
Write-Host "已复制。注意：Trae 的 skill-config.json 里 managedSkills 以 name 为 key，"
Write-Host "本包 name=auto-research 是 ASCII，不会与中文技能冲突。"
Write-Host "自检：python `"$dest\tools\host_check.py`""
