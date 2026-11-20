#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_metrics.py — 交付质量度量（首轮通过率 / 返工轮数 / 每轮 CRITICAL 数）。

为什么需要：预设里有一堆**质量门**（G1–G11、Tier≥T2 独立评审、证据门），
但没有任何指标能回答「这个月科研自动化比上个月强了吗」。
本脚本把每轮独立评审的 verdict 变成可统计的一条记录，算出趋势。

数据：`<工作区>/.dsh-research/reviews/*.json`，一文件一轮，字段见 SCHEMA。
  由主 agent 在每次评审结束后写一条（不允许事后补写"记不清"的分数：
  verdict/score 拿不到就填 null 并置 backfilled=true）。

指标定义（口径写死，避免自欺）：
  · 首轮通过率 = 有 verdict 的任务里，round 1 的 verdict == "ready" 且 critical == 0 的比例
  · 首轮零 CRITICAL 率 = round 1 的 critical == 0 的比例（更宽）
  · 平均返工轮数 = 每个任务的记录条数均值
  · 每轮平均 CRITICAL = 全部记录的 critical 均值
  verdict=null/unknown 的记录只参与 issue 计数，不参与通过率。

用法：
  python review_metrics.py            # 汇总
  python review_metrics.py --json
exit 0 恒为 0（这是度量，不是门）。
"""
import argparse
import glob
import json
import os

REVIEWS = os.path.expandvars(r"%USERPROFILE%\..")  # 占位，真值由 --dir 或默认工作区给
DEFAULT_DIR = os.path.join(os.environ.get("SCI_WORKSPACE") or os.getcwd(),
                           ".dsh-research", "reviews")

SCHEMA = """
{
  "taskId": "2026-10-17-ai4science-2026",
  "round": 1,
  "ts": "2026-10-17T13:50:00",
  "reviewer_tier": "T2",            // T1 跨模型 / T2 冷读同模型 / T3 自审(无效)
  "model": null,                    // 可选
  "verdict": "almost",              // ready | almost | not-ready | unavailable | unknown
  "score": 6,                       // 0-10，拿不到填 null
  "critical": 3, "major": 8, "minor": 9,
  "backfilled": false,              // 事后补录必须置 true
  "source": "subagent cold-read",   // 证据出处
  "notes": "口径循环论证/检索不可复现/计数错误"
}
"""


def load(dirpath):
    recs = []
    for p in sorted(glob.glob(os.path.join(dirpath, "*.json"))):
        try:
            with open(p, encoding="utf-8-sig") as f:
                r = json.load(f)
            r["_file"] = os.path.basename(p)
            recs.append(r)
        except Exception as e:
            print(f"[warn] 跳过不可解析 {os.path.basename(p)}: {type(e).__name__}")
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--schema", action="store_true", help="打印记录格式")
    args = ap.parse_args()

    if args.schema:
        print(SCHEMA)
        return 0

    recs = load(args.dir)
    if not recs:
        print(f"REVIEWS: 0 条（目录 {args.dir}）——先按 --schema 写第一条")
        return 0

    tasks = {}
    for r in recs:
        tasks.setdefault(r.get("taskId", "?"), []).append(r)

    rows = []
    for tid, rs in tasks.items():
        rs.sort(key=lambda x: (x.get("round") or 0))
        first = rs[0]
        known = [x for x in rs if x.get("verdict") in ("ready", "almost", "not-ready")]
        has_verdict = first.get("verdict") in ("ready", "almost", "not-ready")
        passed = bool(has_verdict and first.get("verdict") == "ready" and (first.get("critical") or 0) == 0)
        rows.append({
            "taskId": tid,
            "rounds": len(rs),
            "first_verdict": first.get("verdict"),
            "first_score": first.get("score"),
            "first_critical": first.get("critical"),
            "passed": passed,
            "zero_crit": (first.get("critical") or 0) == 0 if has_verdict else None,
            "backfilled": any(x.get("backfilled") for x in rs),
        })

    known_rows = [r for r in rows if r["first_verdict"] in ("ready", "almost", "not-ready")]
    n_rev = len(recs)
    avg_crit = sum((r.get("critical") or 0) for r in recs) / n_rev
    avg_rounds = sum(r["rounds"] for r in rows) / len(rows)
    fp = (sum(1 for r in known_rows if r["passed"]) / len(known_rows)) if known_rows else None
    zc = (sum(1 for r in known_rows if r["zero_crit"]) / len(known_rows)) if known_rows else None

    if args.json:
        print(json.dumps({"tasks": rows, "records": n_rev,
                          "first_pass_rate": fp, "first_zero_critical_rate": zc,
                          "avg_rounds": round(avg_rounds, 2),
                          "avg_critical_per_round": round(avg_crit, 2)},
                         ensure_ascii=False, indent=1))
        return 0

    print("=" * 78)
    print("交付质量度量（review_metrics）")
    print("=" * 78)
    print(f"记录 {n_rev} 条 / 任务 {len(rows)} 个 / 数据目录 {args.dir}\n")
    print(f"  {'任务':<34} {'轮':>2} {'R1 verdict':<11} {'R1分':>4} {'R1C':>3} {'通过':>4}")
    print(f"  {'-'*34} {'-'*2} {'-'*11} {'-'*4} {'-'*3} {'-'*4}")
    for r in sorted(rows, key=lambda x: x["taskId"]):
        flag = "*" if r["backfilled"] else ""
        print(f"  {r['taskId'][:34]:<34} {r['rounds']:>2} {str(r['first_verdict']):<11} "
              f"{str(r['first_score']):>4} {str(r['first_critical']):>3} "
              f"{'YES' if r['passed'] else 'no':>4}{flag}")
    print("\n  指标（口径见 docstring）：")
    print(f"    首轮通过率          {('%.0f%%' % (fp*100)) if fp is not None else 'n/a'}  ({len(known_rows)} 个任务有 verdict)")
    print(f"    首轮零 CRITICAL 率  {('%.0f%%' % (zc*100)) if zc is not None else 'n/a'}")
    print(f"    平均返工轮数        {avg_rounds:.2f}")
    print(f"    每轮平均 CRITICAL   {avg_crit:.2f}")
    print("\n  * = 含事后补录记录（backfilled）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
