#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
text_gates.py — 文本类质量门（G1 写作质量 / G3 终检项），v9.2

来源：融合研究 references/quality-gates.md 的 G1 六维与 G3 三项，机械化为确定性检查。
定位：Type-A（机器可判）。**不判"写得好不好"**，只判"是否触发了已知的反模式阈值"。
      质量验收仍归 Tier≥T2 独立评审（见 contracts/reviewer-acceptance 系列契约）。

已裁决的阈值冲突（见 contracts/acceptance-gate.md §6.4）：
  G1 AI 高频词密度 —— 原文件总览表写「>=5 处/千词」、明细表写「<=3 处/千词」。
  **本工具采用 3 处/千词**（明细表是可执行细则）。

计口规则（中英混排）：
  计数单位 = 英文单词数 + CJK 汉字数（标点不计）。密度均按「每 1000 计数单位」。

用法：
  python text_gates.py <文件> [<文件>...]            # 检查
  python text_gates.py <文件> --json                 # 机器可读
  python text_gates.py <文件> --bib refs.bib         # 附加 G3 引用时效性检查
  python text_gates.py <文件> --strict               # Major 失败也 exit 1

exit 0 = 无 Critical 失败；1 = 有 Critical 失败（或 --strict 下有任意失败）。
纯标准库。
"""
import argparse
import json
import os
import re
import sys

# ── 词表（逐字取自 quality-gates.md G1/G3）────────────────────────────────

AI_HIGH_FREQ = [
    "leverage", "delve", "pivotal", "tapestry", "realm", "nuanced",
    "multifaceted", "groundbreaking", "revolutionize",
]
CONNECTIVES = ["however", "moreover", "furthermore", "therefore", "in addition"]
OVERCLAIM = [
    "state-of-the-art", "sota", "first", "novel", "unprecedented",
    "breakthrough", "paradigm shift",
    "首个", "首次", "最新", "最好", "突破性", "领先", "国际领先", "填补空白",
]
# 段首冗余模板（G1「开篇冗余」）
REDUNDANT_OPENINGS = [
    r"^recently[,，]?\s+",
    r"^in recent years[,，]?\s+",
    r"^with the rapid development of",
    r"^has attracted (much|increasing|growing) attention",
    r"^随着.{0,12}(的)?(快速)?发展",
    r"^近年来[,，]?",
]

# ── 阈值（逐字取自 quality-gates.md）──────────────────────────────────────

TH = {
    "ai_density_max": 3.0,        # 处/千词（已裁决，见文件头）
    "period_ratio_max": 0.60,     # 句号占比 <= 60%
    "para_len_ratio_max": 4.0,    # 最长段 <= 最短段 x 4
    "sentence_cv_min": 0.5,       # 句长变异系数 >= 0.5
    "connective_max": 4.0,        # 任意连接词 <= 4 次/千词
    "citation_recent3y_min": 0.20,  # G3 近 3 年引用占比 >= 20%
}

CJK = re.compile(r"[\u4e00-\u9fff]")
EN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
SENT_SPLIT = re.compile(r"[.!?。！？]+")


def units(text):
    """计数单位 = 英文单词 + CJK 汉字。"""
    return len(EN_WORD.findall(text)) + len(CJK.findall(text))


def density(count, total_units):
    if total_units <= 0:
        return 0.0
    return count * 1000.0 / total_units


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def sentences(text):
    out = []
    for seg in SENT_SPLIT.split(text):
        seg = seg.strip()
        if seg:
            out.append(seg)
    return out


def check_text(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        raw = f.read()
    # 去掉 LaTeX 命令与代码块，避免把 \cite 之类计入
    text = re.sub(r"```.*?```", " ", raw, flags=re.S)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    text = re.sub(r"%.*", " ", text)

    total = units(text)
    low = text.lower()
    results = []

    def add(gate, name, ok, detail, severity):
        results.append({"gate": gate, "check": name, "ok": bool(ok),
                        "severity": severity, "detail": detail})

    # ── G1 ──
    hits = {}
    for w in AI_HIGH_FREQ:
        n = len(re.findall(r"\b" + re.escape(w) + r"\w*", low))
        if n:
            hits[w] = n
    total_ai = sum(hits.values())
    d = density(total_ai, total)
    add("G1", "AI高频词密度", d <= TH["ai_density_max"],
        f"{d:.2f} 处/千词 (阈值<={TH['ai_density_max']}) 命中 {total_ai} 次 {hits or ''}",
        "Critical")

    sents = sentences(text)
    # 标点多样性：分母是**全部**标点（句号/逗号/分号/冒号/破折号），
    # 不是句末标点——否则英文散文恒为 ~100%，该门失去意义。
    n_period = len(re.findall(r"[.。]", text))
    n_other = len(re.findall(r"[,;:，；：、—–\-]", text))
    denom = n_period + n_other
    pr = (n_period / denom) if denom else 0.0
    add("G1", "标点多样性(句号占比)", pr <= TH["period_ratio_max"],
        f"{pr:.2%} (阈值<={TH['period_ratio_max']:.0%}) 句号 {n_period} / 其他标点 {n_other}", "Major")

    paras = paragraphs(text)
    if len(paras) >= 2:
        lens = [units(p) for p in paras]
        shortest = min(lens)
        longest = max(lens)
        ratio = (longest / shortest) if shortest > 0 else float("inf")
        add("G1", "段落节奏", ratio <= TH["para_len_ratio_max"],
            f"最长/最短 = {ratio:.2f} (阈值<={TH['para_len_ratio_max']}) 段数={len(paras)}", "Major")
    else:
        add("G1", "段落节奏", True, "段落数<2，跳过", "Major")

    if len(sents) >= 3:
        slens = [units(s) for s in sents]
        mean = sum(slens) / len(slens)
        var = sum((x - mean) ** 2 for x in slens) / len(slens)
        cv = (var ** 0.5 / mean) if mean else 0.0
        add("G1", "句长变异系数", cv >= TH["sentence_cv_min"],
            f"CV={cv:.2f} (阈值>={TH['sentence_cv_min']}) 句数={len(sents)}", "Major")
    else:
        add("G1", "句长变异系数", True, "句子数<3，跳过", "Major")

    ch = {}
    for c in CONNECTIVES:
        n = len(re.findall(r"\b" + re.escape(c) + r"\b", low))
        if n:
            ch[c] = n
    worst = max(ch.values()) if ch else 0
    worst_word = max(ch, key=ch.get) if ch else "-"
    dw = density(worst, total)
    add("G1", "连接词多样性", dw <= TH["connective_max"],
        f"最高 {worst_word}={worst} 次 ({dw:.2f}/千词, 阈值<={TH['connective_max']})", "Major")

    red = []
    for p in paras:
        for pat in REDUNDANT_OPENINGS:
            if re.search(pat, p.lower()):
                red.append(p[:40])
                break
    add("G1", "开篇冗余", not red, f"命中 {len(red)} 段 {red[:3] if red else ''}", "Minor")

    # ── G3 ──
    oc = {}
    for w in OVERCLAIM:
        n = len(re.findall(re.escape(w), low))
        if n:
            oc[w] = n
    add("G3", "过度声明词", not oc,
        f"命中 {sum(oc.values())} 次 {oc or ''}（每个声明须有充分证据支持）", "Major")

    return {"file": path, "units": total, "sentences": len(sents),
            "paragraphs": len(paras), "results": results}


def check_bib(bib_path, current_year):
    """G3 引用时效性：近 3 年引用占比 >= 20%。"""
    try:
        with open(bib_path, encoding="utf-8-sig", errors="replace") as f:
            bib = f.read()
    except Exception as e:
        return {"gate": "G3", "check": "引用时效性", "ok": False, "severity": "Major",
                "detail": f"bib 不可读：{e}"}
    years = [int(y) for y in re.findall(r"\byear\s*=\s*[{\"]?(\d{4})", bib, re.I)]
    if not years:
        return {"gate": "G3", "check": "引用时效性", "ok": False, "severity": "Major",
                "detail": "bib 中未解析到 year 字段，无法判定（不得当作通过）"}
    recent = sum(1 for y in years if y >= current_year - 2)
    ratio = recent / len(years)
    return {"gate": "G3", "check": "引用时效性", "ok": ratio >= TH["citation_recent3y_min"],
            "severity": "Major",
            "detail": f"近3年 {recent}/{len(years)} = {ratio:.1%} (阈值>={TH['citation_recent3y_min']:.0%})"}


def main():
    ap = argparse.ArgumentParser(description="文本类质量门（G1 写作质量 / G3 终检项）")
    ap.add_argument("files", nargs="+", help="待检查文本文件（.tex/.md/.txt 均可）")
    ap.add_argument("--bib", default=None, help="可选：BibTeX 文件，做 G3 引用时效性检查")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Major 失败也 exit 1")
    args = ap.parse_args()

    reports = []
    for p in args.files:
        if not os.path.isfile(p):
            print(f"[ERROR] 文件不存在：{p}", file=sys.stderr)
            sys.exit(1)
        reports.append(check_text(p))

    if args.bib:
        import datetime
        reports.append({"file": args.bib, "units": 0, "sentences": 0, "paragraphs": 0,
                        "results": [check_bib(args.bib, datetime.date.today().year)]})

    all_res = [r for rep in reports for r in rep["results"]]
    crit_fail = [r for r in all_res if not r["ok"] and r["severity"] == "Critical"]
    major_fail = [r for r in all_res if not r["ok"] and r["severity"] == "Major"]

    if args.json:
        print(json.dumps({
            "files": [r["file"] for r in reports],
            "reports": reports,
            "critical_failed": len(crit_fail),
            "major_failed": len(major_fail),
            "verdict": "fail" if crit_fail or (args.strict and major_fail) else "pass",
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 66)
        print("文本质量门 G1/G3（text_gates.py）")
        print("=" * 66)
        for rep in reports:
            print(f"\n▸ {rep['file']}   （计数单位 {rep['units']}｜句 {rep['sentences']}｜段 {rep['paragraphs']}）")
            for r in rep["results"]:
                tag = "PASS" if r["ok"] else ("FAIL" if r["severity"] == "Critical" else "WARN")
                print(f"  [{tag}] {r['gate']} {r['check']} — {r['detail']}")
        print(f"\nCritical 失败 {len(crit_fail)}｜Major 失败 {len(major_fail)}")
        if crit_fail:
            print("结论：**不得进入下一阶段**（Critical 门未过，见 quality-gates 执行规则 1）")
        elif major_fail:
            print("结论：可通过，但须在交付物「局限」中列明上述 Major 项")
        else:
            print("结论：通过")

    sys.exit(1 if (crit_fail or (args.strict and major_fail)) else 0)


if __name__ == "__main__":
    main()
