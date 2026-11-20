<#
.SYNOPSIS
把科研自动化技能装到 Claude Code（用户级）。
.DESCRIPTION
复制本包到 ~/.claude/skills/sci-autoresearch/，并验证 SKILL.md 就位。
.PARAMETER DryRun
只打印将执行的动作，不落盘。
#>
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # 包根
$dest = Join-Path $env:USERPROFILE ".claude\skills\sci-autoresearch"

if (-not (Test-Path (Join-Path $pkg "SKILL.md"))) {
  throw "找不到 SKILL.md，请在本包的 adapters/claude-code/ 目录下运行"
}

Write-Host "源   : $pkg"
Write-Host "目标 : $dest"
if ($DryRun) { Write-Host "[DryRun] 不执行复制"; exit 0 }

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $pkg "*") -Destination $dest -Recurse -Force
Write-Host "已复制。验证："
Get-ChildItem $dest | Select-Object Name, Length | Format-Table -AutoSize

Write-Host ""
Write-Host "下一步："
Write-Host "  1) 新开 Claude Code 会话，说「用科研自动化模式做 X」"
Write-Host "  2) 自检：python `"$dest\tools\host_check.py`""
Write-Host "  3) 可选：把 adapters/claude-code/hooks-example.json 合进 .claude/settings.json"
