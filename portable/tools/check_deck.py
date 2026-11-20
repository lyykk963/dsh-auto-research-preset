#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_deck.py — 幻灯片体检（把"AI 感 / 单调 / 没图"变成可测的数）。

为什么需要：2026-10-18 用户反馈"PPT 太有 AI 感、单调、没图"。
但"AI 感"是主观词——不能靠感觉，否则改完还是靠感觉验收。
本工具把三个病症量化成 4 个指标，对 .pptx 直接体检（纯标准库，解 zip + XML）：

  · 纯文字页占比  —— 没有任何图片/表格/图表的页占比（"没图"的直接度量）
  · 平均每页字数  —— 文字过载（"满页 bullet"是 AI 感的主因）
  · 超载页数      —— 单页字数 > 阈值
  · 版式重复连击  —— 连续同 layout 的最长页数（"单调"的度量）

判据（阈值可按场景调；默认值来自对"设计好的模板"与"朴素生成"的对比观察）：
  FAIL  text_only_ratio > 0.50 或 全篇图形对象数 < ceil(页数/4)
  WARN  avg_chars > 260 或 max_same_layout_run > 4

用法：
  python check_deck.py <a.pptx> [--json] [--max-text-only 0.5] [--min-graphics-ratio 0.25]
  python check_deck.py <a.pptx> --quiet      # 只输出结论行（给流程调用）
exit 0 = 通过（可带 WARN）；1 = 命中 FAIL（= 这版 deck 不要交）。
"""
import argparse
import io
import json
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def slide_files(z):
    names = [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)]
    return sorted(names, key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))


def layout_of(z, slide_name):
    """用 rels 里的 slideLayout 作为"版式签名"（单调性度量）。"""
    base = os.path.basename(slide_name)
    rel = f"ppt/slides/_rels/{base}.rels"
    try:
        root = ET.fromstring(z.read(rel))
    except Exception:
        return "?"
    for rel_el in root:
        tgt = rel_el.get("Target", "")
        if "slideLayout" in tgt:
            return os.path.basename(tgt)
    return "?"


def analyze(path):
    with zipfile.ZipFile(path) as z:
        slides = slide_files(z)
        rows = []
        for name in slides:
            root = ET.fromstring(z.read(name))
            texts = [t.text or "" for t in root.iter(f"{{{NS['a']}}}t")]
            body = "".join(texts)
            chars = len(body.strip())
            pics = sum(1 for _ in root.iter(f"{{{NS['p']}}}pic"))
            tables = sum(1 for _ in root.iter(f"{{{NS['a']}}}tbl"))
            charts = 0
            for gd in root.iter(f"{{{NS['a']}}}graphicData"):
                if "chart" in (gd.get("uri") or ""):
                    charts += 1
            shapes = len(texts)
            rows.append({
                "slide": os.path.basename(name),
                "chars": chars,
                "pics": pics, "tables": tables, "charts": charts,
                "graphics": pics + tables + charts,
                "paras": shapes,
                "layout": layout_of(z, name),
                "text": body[:70],
            })
    return rows


def summarize(rows, max_text_only, min_graphics_ratio):
    n = len(rows)
    if n == 0:
        return {"slides": 0, "verdict": "FAIL", "reason": "没有幻灯片"}
    text_only = [r for r in rows if r["graphics"] == 0]
    graphics = sum(r["graphics"] for r in rows)
    avg_chars = sum(r["chars"] for r in rows) / n
    # "单调"的正确度量不是 layout 重复（设计好的模板本来就用一个 layout），
    # 而是**内容构图**的多样性：把每页归成一个构图签名，看用了多少种、最长连击多长。
    def sig(r):
        return (r["pics"] > 0, r["tables"] > 0, r["charts"] > 0, min(r["paras"] // 4, 6))
    sigs = [sig(r) for r in rows]
    variety = len(set(sigs)) / n
    max_run, run = 1, 1
    for i in range(1, n):
        if sigs[i] == sigs[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    need_graphics = math.ceil(n * min_graphics_ratio)
    fails, warns = [], []
    if len(text_only) / n > max_text_only:
        fails.append(f"纯文字页 {len(text_only)}/{n}（{len(text_only)/n:.0%}）> {max_text_only:.0%}")
    if graphics < need_graphics:
        fails.append(f"图形对象共 {graphics} 个 < 需 ≥{need_graphics}（页数/4）")
    if avg_chars > 260:
        warns.append(f"平均每页 {avg_chars:.0f} 字 > 260（满页文字是 AI 感主因）")
    if variety < 0.30:
        warns.append(f"构图多样性 {variety:.0%} < 30%（只用了 {len(set(sigs))} 种构图/共 {n} 页 → 单调）")
    if max_run > 4:
        warns.append(f"连续 {max_run} 页构图相同 > 4（单调）")
    return {
        "slides": n, "text_only": len(text_only),
        "text_only_ratio": round(len(text_only) / n, 3),
        "graphics_total": graphics, "graphics_needed": need_graphics,
        "avg_chars": round(avg_chars, 1),
        "max_same_layout_run": max_run,
        "composition_variety": round(variety, 3),
        "fails": fails, "warns": warns,
        "verdict": "FAIL" if fails else ("WARN" if warns else "PASS"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--max-text-only", type=float, default=0.50)
    ap.add_argument("--min-graphics-ratio", type=float, default=0.25)
    ap.add_argument("--show", type=int, default=8, help="明细显示前 N 页")
    a = ap.parse_args()
    if not os.path.isfile(a.pptx):
        print(f"DECK: 文件不存在 {a.pptx}")
        return 2
    rows = analyze(a.pptx)
    s = summarize(rows, a.max_text_only, a.min_graphics_ratio)

    if a.json:
        print(json.dumps({"file": a.pptx, "summary": s, "slides": rows}, ensure_ascii=False, indent=1))
        return 0 if s["verdict"] != "FAIL" else 1

    if not a.quiet:
        print("=" * 78)
        print(f"幻灯片体检：{os.path.basename(a.pptx)}")
        print("=" * 78)
        print(f"  {'页':<10} {'字数':>5} {'图':>3} {'表':>3} {'图表':>4} {'版式':<14} 前 44 字")
        for r in rows[: a.show]:
            print(f"  {r['slide'][:10]:<10} {r['chars']:>5} {r['pics']:>3} {r['tables']:>3} "
                  f"{r['charts']:>4} {r['layout'][:14]:<14} {r['text'][:44]}")
        if len(rows) > a.show:
            print(f"  … 其余 {len(rows)-a.show} 页略")
        print()
        print(f"  纯文字页 {s['text_only']}/{s['slides']}（{s['text_only_ratio']:.0%}，阈值 ≤{a.max_text_only:.0%}）")
        print(f"  图形对象 {s['graphics_total']} 个（需 ≥{s['graphics_needed']}）")
        print(f"  平均每页 {s['avg_chars']} 字  构图多样性 {s['composition_variety']:.0%}"
              f"  最长同构图连击 {s['max_same_layout_run']} 页")
    for f in s["fails"]:
        print(f"  [FAIL] {f}")
    for w in s["warns"]:
        print(f"  [WARN] {w}")
    print(f"DECK: {s['verdict']}  ({os.path.basename(a.pptx)})")
    return 0 if s["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
