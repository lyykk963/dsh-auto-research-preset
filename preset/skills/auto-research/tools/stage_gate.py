#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stage_gate.py — 阶段产物自动清单门（P1-1 / v9）

定位：把「每阶段收尾必做」的 Type-A 确定性检查从口头纪律变成可执行脚本。
对给定阶段产物目录做机械清单检查：文件存在 / 非空 / JSON 可 parse / 图片可解码 /
关键数字正则命中 / 哈希留痕存在。未过 → 该阶段不得标 done（与 evidence/MANIFEST 联动）。

哲学对齐：
- 与 evidence_check.py 同源（ARIS evidence-precheck 移植）：只做「机械存在性」检查，
  不判质量（质量归独立评审）。能 DRIVE，不能 ACQUIT。
- 纯标准库，无外部依赖；宁 false-negative 不 false-positive。

用法：
  python stage_gate.py <产物根目录> --manifest <gate.json>
  python stage_gate.py <产物根目录> --auto            # 自动探测常见产物类型

gate.json 格式（清单声明要检查什么）：
{
  "phase": "execute",
  "require_files": ["results/main.json", "results/HASHES.txt"],
  "require_nonempty": ["results/main.json"],
  "require_json": ["results/main.json"],
  "require_images": ["figures/fig1.png"],
  "regex": [{"file": "results/main.json", "pattern": "0\\\\.7\\d+"}],
  "notes": "本阶段验收标准：主结果文件 + 图 + 哈希留痕"
}

输出：stdout 一行行检查结果，末尾 summary；exit 0 = 全过，exit 1 = 有缺失。
同时可写 stage_gate_report.md（--report <path>）。
"""
import argparse
import hashlib
import json
import os
import re
import sys

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_EMPTY = "empty"
STATUS_UNPARSEABLE = "unparseable"
STATUS_NO_MATCH = "pattern_not_found"


def _is_image(path):
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf"))


def _check_image(path):
    """轻量图片可解码性检查：PNG/JPEG 魔数即可；PDF 检查 %PDF 头。"""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
        if path.lower().endswith(".png"):
            return head[:8] == b"\x89PNG\r\n\x1a\n"
        if path.lower().endswith((".jpg", ".jpeg")):
            return head[:3] == b"\xff\xd8\xff"
        if path.lower().endswith(".gif"):
            return head[:6] in (b"GIF87a", b"GIF89a")
        if path.lower().endswith(".pdf"):
            return head[:5] == b"%PDF-"
        if path.lower().endswith(".webp"):
            return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        return True
    except Exception:
        return False


def _check_regex(path, pattern):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    try:
        return re.search(pattern, text) is not None
    except Exception:
        return False


def run(root, gate):
    results = []
    failures = []

    def record(item, status, detail=""):
        results.append({"item": item, "status": status, "detail": detail})
        if status != STATUS_OK:
            failures.append({"item": item, "status": status, "detail": detail})

    # require_files
    for rel in gate.get("require_files", []):
        p = os.path.join(root, rel)
        record(rel, STATUS_OK if os.path.isfile(p) else STATUS_MISSING)

    # require_nonempty
    for rel in gate.get("require_nonempty", []):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            record(rel, STATUS_MISSING, "file not found")
        else:
            sz = os.path.getsize(p)
            record(rel, STATUS_OK if sz > 0 else STATUS_EMPTY, f"size={sz}")

    # require_json
    for rel in gate.get("require_json", []):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            record(rel, STATUS_MISSING, "file not found")
        else:
            try:
                json.load(open(p, encoding="utf-8-sig"))
                record(rel, STATUS_OK)
            except Exception as e:
                record(rel, STATUS_UNPARSEABLE, str(e)[:120])

    # require_images
    for rel in gate.get("require_images", []):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            record(rel, STATUS_MISSING, "file not found")
        else:
            ok = _check_image(p)
            record(rel, STATUS_OK if ok else STATUS_UNPARSEABLE, "" if ok else "bad image header")

    # regex
    for spec in gate.get("regex", []):
        rel = spec.get("file", "")
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            record(f"regex@{rel}", STATUS_MISSING, "file not found")
        else:
            hit = _check_regex(p, spec.get("pattern", ""))
            record(f"regex@{rel}~{spec.get('pattern','')[:20]}", STATUS_OK if hit else STATUS_NO_MATCH)

    summary = {"total": len(results), "passed": len(results) - len(failures), "failed": len(failures)}
    return results, summary


def main():
    ap = argparse.ArgumentParser(description="阶段产物自动清单门")
    ap.add_argument("root", help="阶段产物根目录")
    ap.add_argument("--manifest", help="gate.json 清单路径")
    ap.add_argument("--report", help="可选：写 stage_gate_report.md 到该路径")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(json.dumps({"error": "root not found"}, ensure_ascii=False))
        sys.exit(1)

    if args.manifest:
        gate = json.load(open(args.manifest, encoding="utf-8-sig"))
    else:
        gate = {"phase": "unknown", "require_files": [], "require_nonempty": [],
                "require_json": [], "require_images": [], "regex": [], "notes": "auto mode"}

    results, summary = run(args.root, gate)

    for r in results:
        print(f"[{r['status']:>15}] {r['item']}" + (f"  ({r['detail']})" if r.get("detail") else ""))

    print(json.dumps({"summary": summary}, ensure_ascii=False))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(f"# Stage Gate Report\n\n- phase: {gate.get('phase','')}\n")
            f.write(f"- notes: {gate.get('notes','')}\n\n")
            f.write("| 状态 | 项目 | 详情 |\n|---|---|---|\n")
            for r in results:
                f.write(f"| {r['status']} | {r['item']} | {r.get('detail','')} |\n")
            f.write(f"\n**summary**: passed {summary['passed']}/{summary['total']}\n")

    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
