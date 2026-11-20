#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evidence_check.py — 确定性证据预检（G11 证据门的机械部分）

移植自 ARIS (github.com/wanshuiyin/Auto-claude-code-research-in-sleep) tools/evidence_check.py (MIT)。
定位：在花任何评审/模型调用之前，用纯确定性逻辑捕获「幻觉证据」——
引用了一个不存在的文件（path_missing），或引用的数字/值不在该文件中（value_not_found）。

语义（对齐 ARIS evidence-precheck）：
- verified          证据存在（只代表"存在"，不代表"支持 claim"——支持与否归独立评审 Type-B）
- value_not_found   文件存在但找不到所引用的值（幻觉证据 → 确定性拒绝）
- path_missing      引用的文件不存在（幻觉证据 → 确定性拒绝）
- unparseable       无法解析（保守交给评审判断，绝不误报 verified）

设计原则：宁 false-negative 不 false-positive；纯数字按「数字 token 相等」匹配
（73.2 匹配 73.20，但 73 不匹配 73.5）；非数字按归一化子串匹配。

用法：
  python evidence_check.py <root> --value 73.2 --source results/eval.json   # exit 0 = verified
  python evidence_check.py <root> --batch claims.json                        # exit 1 若任一条幻觉
  claims.json = [{"id": "c1", "value": "73.2", "source": "results/eval.json"}, ...]
输出（--batch）：{"results":[{id,value,source,status,detail}], "summary":{status:n}}
纯标准库，无外部依赖。
"""

import argparse
import json
import os
import re
import sys

STATUS_VERIFIED = "verified"
STATUS_NOT_FOUND = "value_not_found"
STATUS_PATH_MISSING = "path_missing"
STATUS_UNPARSEABLE = "unparseable"


def _norm_text(s):
    """归一化文本用于子串匹配：去空白、去常见格式噪音、小写。"""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


def _is_numeric_token(s):
    """判断是否纯数字 token（含小数/科学计数/百分比/千分位）。"""
    s = str(s).strip().replace(",", "")
    if s.endswith("%"):
        s = s[:-1]
    return bool(re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", s))


def _numeric_equiv(a, b):
    """数字 token 相等：73.2 == 73.20 == 73.2%（数值上）；73 != 73.5。"""
    try:
        na = float(str(a).replace(",", "").rstrip("%"))
        nb = float(str(b).replace(",", "").rstrip("%"))
        return abs(na - nb) < 1e-9
    except (ValueError, TypeError):
        return False


def check_value_in_text(value, text):
    """在一个文件文本中查找 value。纯数字按 token 相等；否则归一化子串。"""
    value_s = str(value).strip()
    if not value_s:
        return STATUS_UNPARSEABLE
    if _is_numeric_token(value_s):
        # 数字：遍历文本中的数字 token 做数值相等
        tokens = re.findall(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?%?", text)
        for t in tokens:
            if _numeric_equiv(value_s, t):
                return STATUS_VERIFIED
        return STATUS_NOT_FOUND
    # 非数字：归一化子串
    if _norm_text(value_s) in _norm_text(text):
        return STATUS_VERIFIED
    return STATUS_NOT_FOUND


def check_claim(value, source, root="."):
    """
    检查一条 (value, source)。返回 {status, detail}。
    保守：源路径无法安全解析或读取失败 → unparseable（交给评审），绝不误报 verified。
    """
    if not source or not isinstance(source, str):
        return {"status": STATUS_UNPARSEABLE, "detail": "source 缺失"}
    if value is None or str(value).strip() == "":
        return {"status": STATUS_UNPARSEABLE, "detail": "value 缺失"}
    # 路径解析（防目录穿越：只允许在 root 内的相对路径）
    try:
        full = os.path.normpath(os.path.join(root, source))
        root_abs = os.path.normpath(os.path.abspath(root))
        full_abs = os.path.normpath(os.path.abspath(full))
        if not (full_abs == root_abs or full_abs.startswith(root_abs + os.sep)):
            return {"status": STATUS_UNPARSEABLE, "detail": "source 越界 root"}
    except Exception:
        return {"status": STATUS_UNPARSEABLE, "detail": "路径解析失败"}
    if not os.path.isfile(full_abs):
        return {"status": STATUS_PATH_MISSING, "detail": f"文件不存在: {source}"}
    try:
        with open(full_abs, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        return {"status": STATUS_UNPARSEABLE, "detail": f"读取失败: {e}"}
    status = check_value_in_text(value, text)
    detail = "值存在于文件中" if status == STATUS_VERIFIED else (
        "文件中未找到该值" if status == STATUS_NOT_FOUND else status)
    return {"status": status, "detail": detail}


def check_batch(claims, root="."):
    results = []
    for c in claims:
        cid = str(c.get("id", "")) if isinstance(c, dict) else ""
        value = c.get("value") if isinstance(c, dict) else None
        source = c.get("source") if isinstance(c, dict) else None
        r = check_claim(value, source, root)
        r["id"] = cid
        r["value"] = value
        r["source"] = source
        results.append(r)
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"results": results, "summary": summary}


def main():
    ap = argparse.ArgumentParser(description="确定性证据预检（G11）")
    ap.add_argument("root", nargs="?", default=".", help="证据根目录（默认当前目录）")
    ap.add_argument("--value", help="单条检查：要查找的值")
    ap.add_argument("--source", help="单条检查：源文件路径（相对 root）")
    ap.add_argument("--batch", help="批量检查：claims.json 路径")
    args = ap.parse_args()

    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                claims = json.load(f)
        except Exception as e:
            print(json.dumps({"error": f"claims 读取失败: {e}"}, ensure_ascii=False))
            return 2
        if not isinstance(claims, list):
            print(json.dumps({"error": "claims.json 必须是数组"}, ensure_ascii=False))
            return 2
        out = check_batch(claims, args.root)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        # 幻觉证据（value_not_found / path_missing）→ exit 1（有用信号，不是失败）
        bad = out["summary"].get(STATUS_NOT_FOUND, 0) + out["summary"].get(STATUS_PATH_MISSING, 0)
        return 1 if bad > 0 else 0
    elif args.value is not None and args.source is not None:
        r = check_claim(args.value, args.source, args.root)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["status"] == STATUS_VERIFIED else 1
    else:
        ap.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
