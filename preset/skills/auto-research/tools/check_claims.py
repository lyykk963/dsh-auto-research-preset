#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_claims.py — 交付物里的数字声明 vs 证据文件（M3：计数与台账失真）。

背景（失败模式台账 M3，见 `.dsh-research/memory/failure-modes.md`）：
  已发生的 CRITICAL 里，"正文数字与证据文件对不上"出现了 2 次，其中包括
  「正文写 136 条仓库记录，实际去重是 125 个仓库」这种一半对一半错的。
  这类错误**最便宜也最致命**：读者只要照着报告复算一次，整篇可信度就没了。

做法：交付目录放一份 `claims.json`，把"报告里出现的每个关键数字"声明成一条，
检查器**从证据文件重新算一遍**再比对。评审之前跑，把这类 CRITICAL 挡在门外。

claims.json 格式：
{
  "taskId": "2026-10-17-ai4science-2026",
  "claims": [
    { "id": "C1", "text": "去重后唯一仓库数", "mode": "compute",
      "source": "evidence/raw-20261017.json",
      "compute": "len(set(x['name'] for x in data))", "expect": 125, "tolerance": 0 },
    { "id": "C2", "text": "前段均值（固定集）", "mode": "pointer",
      "source": "evidence/trend-stats.json",
      "pointer": "fixed_set.pre_mean", "expect": 535.3, "tolerance": 0.05 },
    { "id": "C3", "text": "报告确实写了『不是 Clay 原题』", "mode": "contains",
      "source": "REPORT.md", "contains": "不是 Clay 原题", "expect": true }
  ]
}

三种 mode：
  · compute  —— 在受限环境里对已加载 JSON 求值（**只防手滑，不防恶意**：这是作者自己的文件）
  · pointer  —— 点进 JSON 取字段（最稳，优先用这个）
  · contains —— 断言某文件（通常 REPORT.md）确实包含/不包含某串（用于台账类"已改"）

用法：
  python check_claims.py <交付目录>            # 默认读 <dir>/claims.json
  python check_claims.py <dir> --json
exit 0 = 全部通过；1 = 有声明与证据不符（= 评审前必须修）。
纯标准库。
"""
import argparse
import io
import json
import os
import sys

SAFE_FUNCS = {
    "len": len, "sum": sum, "set": set, "round": round, "min": min, "max": max,
    "abs": abs, "sorted": sorted, "any": any, "all": all, "float": float,
    "int": int, "range": range, "list": list, "dict": dict, "str": str,
    "enumerate": enumerate, "zip": zip,
}
FORBIDDEN = ("__", "import", "open(", "eval(", "exec(", "os.", "sys.", "subprocess")


def load_source(path):
    with io.open(path, encoding="utf-8-sig") as f:
        if path.lower().endswith((".json",)):
            return json.load(f)
        return f.read()


def get_pointer(data, dotted):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def eval_compute(expr, data):
    for bad in FORBIDDEN:
        if bad in expr:
            raise ValueError(f"表达式含被禁片段 {bad!r}")
    # ⚠️ 必须把安全函数放进 **globals**：生成器/推导式内部看不到 eval 的 locals，
    #    否则 `sum(len(d) for d in data)` 会报 NameError: len is not defined。
    env = {"__builtins__": {}}
    env.update(SAFE_FUNCS)
    env["data"] = data
    return eval(expr, env)  # noqa: S307


def close(a, b, tol):
    try:
        return abs(float(a) - float(b)) <= float(tol)
    except Exception:
        return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--file", default="claims.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cpath = os.path.join(args.dir, args.file)
    if not os.path.isfile(cpath):
        print(f"CLAIMS: 无 {args.file}（{args.dir}）——交付前必须提供数字声明清单")
        return 1
    try:
        spec = json.load(io.open(cpath, encoding="utf-8-sig"))
    except Exception as e:
        print(f"CLAIMS: {args.file} 不可解析：{type(e).__name__}: {e}")
        return 1

    results = []
    for c in spec.get("claims", []):
        cid = c.get("id", "?")
        mode = c.get("mode", "pointer")
        rels = c.get("sources") or ([c["source"]] if c.get("source") else [])
        rec = {"id": cid, "text": c.get("text", ""), "mode": mode, "ok": False, "detail": ""}
        try:
            paths = [os.path.join(args.dir, r) for r in rels]
            missing = [r for r, p in zip(rels, paths) if not os.path.isfile(p)]
            if missing:
                rec["detail"] = f"证据文件不存在: {', '.join(missing)}"
            else:
                loaded = [load_source(p) for p in paths]
                data = loaded[0] if len(loaded) == 1 else loaded
                if mode == "contains":
                    want = bool(c.get("expect", True))
                    has = str(c.get("contains", "")) in str(data)
                    rec["ok"] = (has == want)
                    rec["detail"] = f"包含={has} 期望={want}"
                else:
                    got = (get_pointer(data, c["pointer"]) if mode == "pointer"
                           else eval_compute(c["compute"], data))
                    exp = c.get("expect")
                    rec["ok"] = close(got, exp, c.get("tolerance", 0))
                    rec["detail"] = f"证据算出 {got} vs 声明 {exp}（tol={c.get('tolerance', 0)}）"
        except Exception as e:
            rec["detail"] = f"{type(e).__name__}: {e}"
        results.append(rec)

    ok = sum(1 for r in results if r["ok"])
    if args.json:
        print(json.dumps({"taskId": spec.get("taskId"), "total": len(results),
                          "passed": ok, "failed": len(results) - ok, "claims": results},
                         ensure_ascii=False, indent=1))
        return 0 if ok == len(results) else 1

    print("=" * 78)
    print(f"数字声明核对（{spec.get('taskId', '?')}）")
    print("=" * 78)
    for r in results:
        print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['id']:<4} {r['text'][:34]:<34} {r['detail']}")
    print(f"\nCLAIMS: {ok}/{len(results)} 通过")
    if ok != len(results):
        print("  → 有声明与证据不符：**评审前**必须改正数字或证据，不许改声明去迁就。")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
