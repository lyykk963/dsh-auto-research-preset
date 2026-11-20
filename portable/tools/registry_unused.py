#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
registry_unused.py — 技能注册表「盲区探测」（P2-6 / v9）

目的：注册表 12 类 + 未分类的 513 技能里，哪些 (a) 从未被使用、(b) 长期未分类、
(c) 已用却被放在"未分类"。让路由表不膨胀失真。

纯标准库。输出 JSON 到 stdout，可 --report 写 md。

用法：
  python registry_unused.py <SKILLS_REGISTRY.md> [--usage <skill-usage.jsonl>] [--report <out.md>]
"""
import argparse
import json
import os
import re

CAT_HEAD = re.compile(r"^##\s+.+?（\d+）\s*$")  # 分类标题行（含中文数字统计）
ITEM = re.compile(r"^- \*\*([^*]+)\*\*", re.M)  # - **skill**


def parse_registry(path):
    """返回 {分类名: [skills]}；分类名按顺序，'未分类' 单独标记。"""
    text = open(path, encoding="utf-8-sig").read()
    lines = text.split("\n")
    cats = []  # (name, is_uncategorized, [items])
    cur = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("## "):
            uncat = "未分类" in s
            name = re.sub(r"[（(]\d+[）)]\s*$", "", s[3:]).strip()
            cats.append({"name": name, "uncat": uncat, "items": []})
            cur = cats[-1]
            continue
        if cur is not None:
            m = ITEM.match(s)
            if m:
                cur["items"].append(m.group(1).strip())
    return cats


def main():
    ap = argparse.ArgumentParser(description="技能注册表盲区探测")
    ap.add_argument("registry")
    ap.add_argument("--usage", help="skill-usage.jsonl 路径（可选）")
    ap.add_argument("--report", help="输出 md 路径（可选）")
    args = ap.parse_args()

    cats = parse_registry(args.registry)
    total = sum(len(c["items"]) for c in cats)
    uncat_cats = [c for c in cats if c["uncat"]]
    cat_cats = [c for c in cats if not c["uncat"]]
    uncat_items = sorted({i for c in uncat_cats for i in c["items"]})
    cat_items = sorted({i for c in cat_cats for i in c["items"]})

    result = {
        "total_skills": total,
        "categorized": len(cat_items),
        "uncategorized": len(uncat_items),
        "uncategorized_list": uncat_items,
        "category_counts": {c["name"]: len(c["items"]) for c in cats},
    }

    # usage 交叉：已用技能是否落在未分类（提示应归类）
    if args.usage and os.path.isfile(args.usage):
        used = set()
        for ln in open(args.usage, encoding="utf-8-sig", errors="replace"):
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                used.add(json.loads(ln).get("skill", ""))
            except Exception:
                pass
        used.discard("")
        result["used_but_uncategorized"] = sorted(used & set(uncat_items))
        result["used_count"] = len(used)

    print(json.dumps(result, ensure_ascii=False, indent=1))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("# 技能注册表盲区探测\n\n")
            f.write(f"- total: {result['total_skills']} | categorized: {result['categorized']} | uncategorized: {result['uncategorized']}\n")
            f.write("- category counts: " + json.dumps(result["category_counts"], ensure_ascii=False) + "\n\n")
            if result["uncategorized_list"]:
                f.write("## 未分类技能（{}）\n\n{}\n".format(
                    len(result["uncategorized_list"]), ", ".join(result["uncategorized_list"])))
            if result.get("used_but_uncategorized"):
                f.write("\n## 已使用但仍在未分类（应归类）\n\n- " + "\n- ".join(result["used_but_uncategorized"]) + "\n")


if __name__ == "__main__":
    main()
