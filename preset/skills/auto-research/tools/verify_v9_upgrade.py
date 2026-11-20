#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v9 upgrade verification: deterministic check that all P0-P2 edits are real and consistent.
Runs locally; exits 1 if any check fails."""
import json, os, re, subprocess, sys

WS = os.environ.get("SCI_WORKSPACE") or os.getcwd()
SKILL = os.path.join(WS, "auto-research", "skills", "auto-research")
failures = []

def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        failures.append(name)

# --- P0-1: SKILL.md quality gate #6 ---
skill = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
check("P0-1 SKILL.md 质量关口标题含 6 条", "6 条" in skill)
check("P0-1 SKILL.md 含三件套硬规则", all(x in skill for x in ["skill-usage.jsonl", "meta/events.jsonl", "iteration-log.jsonl", "no_new_findings"]))
check("P0-1 SKILL.md §12 含日志缺失告警", "日志缺失即告警" in skill)
wc = open(os.path.join(SKILL, "contracts", "watchdog-contract.md"), encoding="utf-8").read()
check("P0-1 watchdog-contract 含反馈日志不增长信号", "反馈日志不增长" in wc)

# --- P0-2: brain.json ---
brain = json.load(open(os.path.join(WS, ".dsh-research", "brain.json"), encoding="utf-8"))
check("P0-2 brain.json lastUpdate 为 2026-09-08", str(brain.get("lastUpdate", "")).startswith("2026-09-08"))
check("P0-2 brain.json 含工作区断层 openQuestion", any("工作区断层" in str(q) for q in brain.get("openQuestions", [])))
check("P0-2 brain.json H2 记录执行断层", any("执行闭环未落地" in str(h.get("text", "")) for h in brain.get("hypotheses", [])))

# --- P1-1: stage_gate.py exists & runs ---
sg = os.path.join(SKILL, "tools", "stage_gate.py")
check("P1-1 stage_gate.py 存在", os.path.isfile(sg))
if os.path.isfile(sg):
    r = subprocess.run([sys.executable, sg, "--help"], capture_output=True, text=True)
    check("P1-1 stage_gate.py 可运行(exit 0)", r.returncode == 0, r.stderr[:80])

# --- P1-2: CHECKPOINT.md ---
cp = os.path.join(SKILL, "templates", "CHECKPOINT.md")
check("P1-2 CHECKPOINT.md 存在", os.path.isfile(cp))
check("P1-2 SKILL.md 引用 CHECKPOINT", "CHECKPOINT.md" in skill)

# --- P1-3: EXPERIMENT_PLAN run contract ---
ep = os.path.join(SKILL, "templates", "EXPERIMENT_PLAN.md")
eptxt = open(ep, encoding="utf-8").read()
check("P1-3 EXPERIMENT_PLAN 含运行契约§9", "## 9. 运行契约" in eptxt)
check("P1-3 含 HASHES.txt 要求", "HASHES.txt" in eptxt)

# --- three feedback logs exist & have new rows ---
for f in ["iteration-log.jsonl", "meta/events.jsonl", "skill-usage.jsonl"]:
    p = os.path.join(WS, ".dsh-research", f)
    if os.path.isfile(p):
        n = sum(1 for _ in open(p, encoding="utf-8-sig", errors="replace"))
        check(f"三件套 {f} 存在且有 {n} 行", n >= 1, f"lines={n}")
    else:
        check(f"三件套 {f} 存在", False, "MISSING")

print()
if failures:
    print("RESULT: FAIL -", len(failures), "checks failed:", failures)
    sys.exit(1)
else:
    print("RESULT: ALL PASS")
    sys.exit(0)
