#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prereg.py — 分析计划预注册：冻结 → 交付前比对（M1：度量口径缺陷）。

背景（失败模式台账 M1，见 `.dsh-research/memory/failure-modes.md`）：
  已发生的 CRITICAL 里，"口径在事后漂移"占 3/7，且最难事后发现：
    · 月度序列的关键词集里含断点之后才诞生的词 → "台阶"由构造产生；
    · 置换检验的切点由同一批数据选出 → 事后检验，p 已触底。
  这两件事的共同点是：**分析计划在看过数据之后被改了，而且没有留痕**。
  事后再查永远查不出来，唯一可靠的办法是**事前冻结、交付前比对**。

用法：
  python prereg.py freeze  <交付目录>          # 冻结 analysis-plan.json（写 .prereg-lock.json）
  python prereg.py verify  <交付目录>          # 比对当前计划与冻结时的计划
  python prereg.py amend   <交付目录> -m "理由" # 记录一次"为什么改"，然后重新冻结
  python prereg.py show    <交付目录>          # 打印计划与冻结状态

判定：verify 不一致 → exit 1（评审前必须解释清楚；不许悄悄改）。
  · 允许的"无关改动"：纯空白/换行差异（做归一化）与 `_note` 字段；
  · 其余任何改动都会被抓到。若确需修改，走 amend（会留一条不可删的修订记录）。

纯标准库。
"""
import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime

PLAN = "analysis-plan.json"
LOCK = ".prereg-lock.json"
AMEND = ".prereg-amendments.jsonl"


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with io.open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def digest(obj):
    """对"实质内容"做 sha256：剔除 _note，键排序，紧凑序列化。"""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return o
    payload = json.dumps(strip(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cmd_freeze(d, force=False):
    plan_path = os.path.join(d, PLAN)
    plan = load_json(plan_path)
    if plan is None:
        print(f"PREREG: 缺 {PLAN}（{d}）——分析开始前必须先写计划")
        return 1
    lock_path = os.path.join(d, LOCK)
    old = load_json(lock_path)
    new_hash = digest(plan)
    if old and old.get("sha256") != new_hash and not force:
        print("PREREG: 已存在冻结记录且计划已变——拒绝静默重冻结。")
        print(f"  冻结时 {old.get('sha256')[:12]}…  现在 {new_hash[:12]}…")
        print("  确属修改请用 `prereg.py amend -m \"理由\"`（会留痕）。")
        return 1
    if old and old.get("sha256") == new_hash and old.get("key_digests"):
        print(f"PREREG: 计划未变（{new_hash[:12]}…），冻结记录保持 {old.get('frozen_at')}")
        return 0
    # 同哈希但缺 key_digests（旧 schema）→ 允许原地升级，保持原冻结时间
    same = bool(old and old.get("sha256") == new_hash)
    frozen_at = (old or {}).get("frozen_at") if same else datetime.now().isoformat(timespec="seconds")
    lock = {"sha256": new_hash, "frozen_at": frozen_at,
            "plan": PLAN, "keys": sorted(plan.keys()),
            # 每个键单独存摘要 → verify 时能指名"哪条口径变了"，而不是笼统说"变了"
            "key_digests": {k: digest(v) for k, v in plan.items()}}
    with io.open(lock_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(lock, ensure_ascii=False, indent=1))
    print(f"PREREG: 冻结 {new_hash[:12]}… → {LOCK}" + ("（lock schema 升级）" if same else ""))
    return 0


def cmd_verify(d):
    plan = load_json(os.path.join(d, PLAN))
    lock = load_json(os.path.join(d, LOCK))
    if plan is None:
        print(f"PREREG: 缺 {PLAN}")
        return 1
    if not lock:
        print(f"PREREG: 缺 {LOCK}——计划从未冻结，无法证明口径未漂移")
        return 1
    cur = digest(plan)
    if cur == lock["sha256"]:
        n = 0
        p = os.path.join(d, AMEND)
        if os.path.isfile(p):
            n = sum(1 for l in io.open(p, encoding="utf-8") if l.strip())
        print(f"PREREG: OK 计划自 {lock['frozen_at']} 起未变（{cur[:12]}…，修订 {n} 次）")
        return 0
    print("PREREG: FAIL 计划与冻结时不一致 —— 口径可能已漂移")
    print(f"  冻结 {lock['sha256'][:12]}…  现在 {cur[:12]}…")
    prev = lock.get("key_digests") or {}
    now = {k: digest(v) for k, v in plan.items()}
    changed = [k for k in now if k in prev and prev[k] != now[k]]
    added = [k for k in now if k not in prev]
    removed = [k for k in prev if k not in now]
    if changed:
        print(f"  变了的字段（{len(changed)}）：")
        for k in changed:
            print(f"    · {k}")
    if added:
        print(f"  新增字段：{', '.join(added)}")
    if removed:
        print(f"  被删字段：{', '.join(removed)}")
    if not (changed or added or removed):
        print("  （只有 _note 之类被忽略的字段变化，或序列化差异）")
    print("  → 若确需修改，用 `prereg.py amend -m \"为什么改\"`；本检查正是为了抓『看数据后改口径』。")
    return 1


def cmd_amend(d, msg):
    if not msg:
        print("PREREG: amend 必须给 -m 理由")
        return 1
    plan = load_json(os.path.join(d, PLAN))
    if plan is None:
        print(f"PREREG: 缺 {PLAN}")
        return 1
    lock = load_json(os.path.join(d, LOCK))
    rec = {"ts": datetime.now().isoformat(timespec="seconds"),
           "from": (lock or {}).get("sha256"), "to": digest(plan), "reason": msg}
    with io.open(os.path.join(d, AMEND), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rc = cmd_freeze(d, force=True)
    if rc == 0:
        print(f"PREREG: 已记录修订并重冻结 —— {msg}")
    return rc


def cmd_show(d):
    plan = load_json(os.path.join(d, PLAN))
    lock = load_json(os.path.join(d, LOCK))
    print(f"计划: {PLAN} {'✔' if plan else '✘'}")
    if plan:
        for k, v in plan.items():
            if str(k).startswith("_"):
                continue
            s = json.dumps(v, ensure_ascii=False)
            print(f"  {k}: {s[:96]}{'…' if len(s) > 96 else ''}")
    print(f"冻结: {LOCK} " + (f"✔ {lock.get('frozen_at')} {lock.get('sha256')[:12]}…" if lock else "✘ 未冻结"))
    p = os.path.join(d, AMEND)
    if os.path.isfile(p):
        n = sum(1 for l in io.open(p, encoding="utf-8") if l.strip())
        print(f"修订记录: {AMEND} {n} 条")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("freeze", "verify", "show"):
        sp = sub.add_parser(name)
        sp.add_argument("dir")
        if name == "freeze":
            sp.add_argument("--force", action="store_true")
    sp = sub.add_parser("amend")
    sp.add_argument("dir")
    sp.add_argument("-m", "--message", required=True)
    args = ap.parse_args()
    if args.cmd == "freeze":
        return cmd_freeze(args.dir, args.force)
    if args.cmd == "verify":
        return cmd_verify(args.dir)
    if args.cmd == "amend":
        return cmd_amend(args.dir, args.message)
    return cmd_show(args.dir)


if __name__ == "__main__":
    sys.exit(main())
