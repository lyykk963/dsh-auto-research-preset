#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cost_metrics.py — 单位交付成本（**代理指标**）。

诚实前提：真实 token 消耗不在本地落盘，拿不到。所以本脚本只算三个**可复算**的代理量：
  1) 墙钟（分钟）= 该任务全部 phase 的最早 startedAt → 最晚 finishedAt/lastUpdatedAt
  2) 返工轮数 = 该任务的评审记录条数（见 reviews/*.json）
  3) 成本代理 = 墙钟 × 返工轮数（"几个机时换一次过审"）

三者都只是代理：墙钟含等待与人工停顿，轮数不代表返工严重程度。
**不得**把本脚本的输出当作 token 成本的替代品写进对外材料；它只用于**纵向自比较**（自己比自己）。

数据源：`<工作区>/.dsh-research/progress*.json` 与 `.dsh-research/reviews/*.json`

用法：
  python cost_metrics.py                # 表格
  python cost_metrics.py --json
exit 0 恒为 0（度量，不是门）。
"""
import argparse
import glob
import json
import os
from datetime import datetime

WS = os.environ.get("SCI_WORKSPACE") or os.getcwd()
DOT = os.path.join(WS, ".dsh-research")


def parse_dt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            continue
    return None


def collect_tasks():
    tasks = {}
    for p in glob.glob(os.path.join(DOT, "progress*.json")):
        try:
            with open(p, encoding="utf-8-sig") as f:
                d = json.load(f)
        except Exception:
            continue
        tid = d.get("taskId")
        if not tid:
            continue
        stamps = []
        for ph in d.get("phases", []) or []:
            for k in ("startedAt", "finishedAt"):
                t = parse_dt(ph.get(k))
                if t:
                    stamps.append(t)
        t = parse_dt(d.get("lastUpdatedAt")) or parse_dt(d.get("publishedAt"))
        if t:
            stamps.append(t)
        if len(stamps) < 2:
            continue
        phases = d.get("phases", []) or []
        done = sum(1 for x in phases if x.get("status") == "done")
        rec = tasks.get(tid)
        cand = {
            "taskId": tid,
            "start": min(stamps),
            "end": max(stamps),
            "phases_done": done,
            "phases_total": len(phases),
            "status": d.get("status"),
            "src": os.path.basename(p),
        }
        # 同一 task 多份快照 → 取覆盖期最长的那份
        if not rec or (cand["end"] - cand["start"]) > (rec["end"] - rec["start"]):
            tasks[tid] = cand
    return tasks


def collect_rounds():
    n = {}
    for p in glob.glob(os.path.join(DOT, "reviews", "*.json")):
        try:
            with open(p, encoding="utf-8-sig") as f:
                r = json.load(f)
        except Exception:
            continue
        n[r.get("taskId", "?")] = n.get(r.get("taskId", "?"), 0) + 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tasks = collect_tasks()
    rounds = collect_rounds()
    rows = []
    for tid, t in tasks.items():
        mins = round((t["end"] - t["start"]).total_seconds() / 60, 1)
        r = rounds.get(tid, 0)
        rows.append({
            "taskId": tid, "minutes": mins, "rounds": r,
            "phases": f"{t['phases_done']}/{t['phases_total']}",
            "status": t["status"],
            "cost_proxy": round(mins * r / 60, 2) if r else None,  # 机时×轮
            "src": t["src"],
        })
    rows.sort(key=lambda x: x["taskId"])

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    print("=" * 84)
    print("单位交付成本（代理指标：墙钟 / 返工轮数 / 机时×轮）")
    print("=" * 84)
    print("⚠️ 真实 token 不可得；本表只用于**自己比自己**，不得对外当成本引用。\n")
    print(f"  {'任务':<38} {'墙钟(min)':>9} {'轮':>3} {'阶段':>6} {'状态':>8} {'机时×轮':>8}")
    print(f"  {'-'*38} {'-'*9} {'-'*3} {'-'*6} {'-'*8} {'-'*8}")
    for r in rows:
        print(f"  {r['taskId'][:38]:<38} {r['minutes']:>9.1f} {r['rounds']:>3} "
              f"{r['phases']:>6} {str(r['status']):>8} {str(r['cost_proxy']):>8}")
    if rows:
        ms = sorted(r["minutes"] for r in rows)
        med = ms[len(ms)//2]
        print(f"\n  任务数 {len(rows)}｜墙钟中位数 {med:.0f} min｜最长 {ms[-1]:.0f} min")
        cov = sum(1 for r in rows if r["rounds"]) / len(rows)
        print(f"  有评审记录的任务占比 {cov:.0%}（其余任务的质量数据缺失——这本身是待办）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
