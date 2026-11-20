#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_delivery.py — 交付完整性前置检查（M2：可复现性缺失）。

背景（失败模式台账 M2）：已发生的 CRITICAL 里，"读者拿着报告无法复算"出现 1 次
（8 个 total_count 零留痕、头条指标的查询式只出现在图注小字里）。
评审能抓到它，但代价是一整轮返工——所以把它做成交付前的机械检查。

检查项（对**交付目录**，不是预设）：
  1. 主文档存在（REPORT.md / MORNING_REPORT.md 二者其一）
  2. `evidence/` 存在且 ≥3 个文件（原始快照不能空口说有）
  3. `claims.json` 存在且 ≥3 条声明（≥2 条必须是 compute/pointer 型，纯 contains 不算）
  4. `analysis-plan.json` + `.prereg-lock.json` 存在（口径已冻结）
  5. 文档引用的本地图片都存在且**能解码**（PNG/JPEG/GIF/WebP 魔数）
  6. 文档引用的 `evidence/…`、`scripts/…`、`figures/…` 路径都存在
  7. 无未替换占位符（TODO / 待补 / XXX / <?> / 待填）

用法：
  python check_delivery.py <交付目录> [--json]
exit 0 = 通过；1 = 有缺口（= 评审前必须补）。
纯标准库。
"""
import argparse
import io
import json
import os
import re
import sys

MAIN_DOCS = ("REPORT.md", "MORNING_REPORT.md")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
PATH_RE = re.compile(r"`((?:evidence|scripts|figures|data)[\\/][^`\s]+)`")
PLACEHOLDER = re.compile(r"(TODO|待补|待填|XXX|\?\?\?|<待>|FIXME)")
MAGIC = {
    b"\x89PNG\r\n\x1a\n": "PNG", b"\xff\xd8\xff": "JPEG", b"GIF8": "GIF", b"RIFF": "WebP",
}


def is_image_ok(path):
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except Exception:
        return False, "不可读"
    for m, name in MAGIC.items():
        if head.startswith(m):
            if name == "WebP" and b"WEBP" not in head:
                continue
            return True, name
    return False, f"魔数不认（{head[:4]!r}）"


def _find_workspace(start):
    """从交付目录上溯找含 .dsh-research 的工作区。"""
    p = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(p, ".dsh-research")):
            return p
        np_ = os.path.dirname(p)
        if np_ == p:
            break
        p = np_
    return None


def _usage_count(ws, task_id):
    """读 skill-usage.jsonl 里本 taskId 的行数（编码容错）。返回 None = 文件不存在。"""
    p = os.path.join(ws, ".dsh-research", "skill-usage.jsonl")
    if not os.path.isfile(p):
        return None
    n = 0
    for raw in open(p, "rb").read().splitlines():
        if not raw.strip():
            continue
        o = None
        for enc in ("utf-8", "gb18030"):
            try:
                o = json.loads(raw.decode(enc))
                break
            except Exception:
                continue
        if isinstance(o, dict) and str(o.get("taskId")) == str(task_id):
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d = args.dir
    checks = []

    def add(ok, name, detail=""):
        checks.append({"ok": bool(ok), "name": name, "detail": detail})

    if not os.path.isdir(d):
        print(f"DELIVERY: 目录不存在 {d}")
        return 1

    # 1 主文档
    doc = next((os.path.join(d, x) for x in MAIN_DOCS if os.path.isfile(os.path.join(d, x))), None)
    add(bool(doc), "主文档存在", os.path.basename(doc) if doc else "缺 REPORT.md / MORNING_REPORT.md")

    # 2 evidence/
    ev = os.path.join(d, "evidence")
    n_ev = sum(len(fs) for _, _, fs in os.walk(ev)) if os.path.isdir(ev) else 0
    add(n_ev >= 3, "evidence/ 有原始快照", f"{n_ev} 个文件" if os.path.isdir(ev) else "缺 evidence/ 目录")

    # 3 claims.json
    cp = os.path.join(d, "claims.json")
    n_c = n_strong = 0
    if os.path.isfile(cp):
        try:
            spec = json.load(io.open(cp, encoding="utf-8-sig"))
            cl = spec.get("claims", [])
            n_c = len(cl)
            n_strong = sum(1 for c in cl if c.get("mode", "pointer") in ("compute", "pointer"))
        except Exception as e:
            add(False, "claims.json 可解析", f"{type(e).__name__}")
    add(n_c >= 3, "claims.json 声明数 ≥3", f"{n_c} 条（其中 compute/pointer {n_strong} 条）")
    add(n_strong >= 2, "claims 里至少有 2 条是重算型", f"{n_strong} 条（纯 contains 不足以证明数字）")

    # 4 预注册
    add(os.path.isfile(os.path.join(d, "analysis-plan.json")), "分析计划存在", "analysis-plan.json")
    add(os.path.isfile(os.path.join(d, ".prereg-lock.json")), "分析计划已冻结", ".prereg-lock.json")

    if doc:
        txt = io.open(doc, encoding="utf-8", errors="replace").read()
        # 5 图片
        bad = []
        for rel in IMG_RE.findall(txt):
            if rel.startswith(("http://", "https://")):
                continue
            p = os.path.join(d, rel.replace("/", os.sep))
            if not os.path.isfile(p):
                bad.append(f"{rel}（不存在）")
                continue
            ok, why = is_image_ok(p)
            if not ok:
                bad.append(f"{rel}（{why}）")
        add(not bad, "文档引用的图片都可解码", "; ".join(bad[:4]))

        # 6 路径引用
        missing = [r for r in set(PATH_RE.findall(txt))
                   if not os.path.exists(os.path.join(d, r.replace("/", os.sep)))]
        add(not missing, "文档引用的数据/脚本路径都存在", "; ".join(sorted(missing)[:5]))

        # 7 占位符
        hits = PLACEHOLDER.findall(txt)
        add(not hits, "无未替换占位符", f"{len(hits)} 处：{', '.join(sorted(set(hits))[:5])}")

    # 8 技能使用审计（v9.7）
    # 理由：2026-10-21 审计发现"每阶段必须追加 skill-usage.jsonl"这条规则全库只有 79 行
    #       —— 规则写死但没人核对，等于空转。这里把它变成交付门。
    try:
        _tid = os.path.basename(os.path.abspath(d))
        _cj = os.path.join(d, "claims.json")
        if os.path.isfile(_cj):
            _spec = json.load(io.open(_cj, encoding="utf-8-sig"))
            _tid = _spec.get("taskId") or _tid
        _ws = _find_workspace(d)
        if _ws is None:
            add(True, "技能使用记录（跳过）", "上溯未找到 .dsh-research")
        else:
            _n = _usage_count(_ws, _tid)
            if _n is None:
                add(True, "技能使用记录（跳过）", "无 skill-usage.jsonl")
            else:
                add(_n >= 1, "本任务留下了技能使用记录",
                    f"taskId={_tid} → {_n} 条（0 条 = 契约 §3 空转）")
    except Exception as _e:
        add(False, "本任务留下了技能使用记录", f"读取失败：{type(_e).__name__}")

    ok = sum(1 for c in checks if c["ok"])
    if args.json:
        print(json.dumps({"dir": d, "total": len(checks), "passed": ok,
                          "failed": len(checks) - ok, "checks": checks}, ensure_ascii=False, indent=1))
    else:
        print("=" * 78)
        print(f"交付完整性（{os.path.basename(os.path.abspath(d))}）")
        print("=" * 78)
        for c in checks:
            print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}" + (f" :: {c['detail']}" if c["detail"] else ""))
        print(f"\nDELIVERY: {ok}/{len(checks)} 通过")
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
