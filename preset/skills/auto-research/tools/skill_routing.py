#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_routing.py — 技能路由与"该用未用"对账。

问题（2026-10-21 审计）：预设文档"点名"了 117 个技能，实际只调用过 33 个。
点名 ≠ 会用。本工具把"该用哪些"写成可执行判断，并**对账实际调用记录**。

用法：
  python skill_routing.py route "写一篇关于 X 的综述"      # 该加载哪些技能
  python skill_routing.py check <交付目录> [--strict]      # 该用但没用的是哪些
  python skill_routing.py check --task <taskId> --category sci_research
  python skill_routing.py list                             # 所有分类与推荐
  python skill_routing.py --self-test                      # 正负控制

数据源：$SCI_SKILL_NAV > ~/.agents/SKILL_NAV.json > 内置默认表（可移植）
退出码：0 正常 / 1 对账缺项（--strict）或数据缺失 / 2 参数错误
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 便携兜底表：没有 SKILL_NAV.json 的机器也能路由（覆盖最常见的四类）
DEFAULT_MAP = [
    {"id": "sci_research", "name": "科研 · 论文 · 学术",
     "triggers": ["paper", "academic", "manuscript", "review", "rebuttal", "citation",
                  "literature", "research", "thesis", "survey", "grant",
                  "科研", "论文", "综述", "审稿", "文献", "选题", "答辩"],
     "recommended": ["paper-lookup", "academic-paper", "results-analysis", "academic-paper-reviewer"]},
    {"id": "ppt", "name": "PPT · 演示 · 汇报",
     "triggers": ["ppt", "slide", "deck", "presentation", "幻灯", "汇报", "答辩"],
     "recommended": ["ppt-studio", "scientific-slides"]},
    {"id": "viz", "name": "图表 · 可视化",
     "triggers": ["chart", "plot", "figure", "visualization", "图表", "可视化", "画图"],
     "recommended": ["scientific-visualization", "matplotlib"]},
    {"id": "coding", "name": "编程 · 工程",
     "triggers": ["code", "bug", "refactor", "test", "代码", "报错", "重构"],
     "recommended": ["systematic-debugging", "test-driven-development"]},
]

FIELD_ALIASES = ("recommended", "recommend", "primary", "skills", "top", "main")


def nav_path():
    env = os.environ.get("SCI_SKILL_NAV")
    if env and os.path.isfile(env):
        return env
    p = os.path.join(os.path.expanduser("~"), ".agents", "SKILL_NAV.json")
    return p if os.path.isfile(p) else None


def load_categories():
    p = nav_path()
    if not p:
        return DEFAULT_MAP, "builtin"
    try:
        d = json.load(io.open(p, encoding="utf-8-sig"))
        cats = d.get("categories") or []
        out = []
        for c in cats:
            rec = None
            for k in FIELD_ALIASES:
                v = c.get(k)
                if isinstance(v, list) and v:
                    rec = [x if isinstance(x, str) else x.get("id") or x.get("name") for x in v]
                    break
            out.append({"id": c.get("id"), "name": c.get("name"),
                        "triggers": c.get("triggers") or [],
                        "recommended": rec or []})
        return (out or DEFAULT_MAP), p
    except Exception as e:
        print(f"[warn] SKILL_NAV 解析失败（{e}），退回内置表", file=sys.stderr)
        return DEFAULT_MAP, "builtin"


# 基础设施词停用表：它们描述工具链而非主题，且极易误伤
#   "ci" 会匹配进 science/decision/specific，"api"/"repo"/"git" 在技术报告里到处都是
STOP_TRIGGERS = {"ci", "api", "ide", "repo", "git", "cli", "sdk", "aws", "ui", "db"}


def _count_trigger(q, t):
    """ASCII 触发器用词边界匹配，中文用子串。

    实测教训：raw substring 会让 "ci" 命中 "science"、让 "api" 命中 "capital"，
    从而把一份科研报告判成编程类任务。
    """
    tl = str(t).lower()
    if not tl or tl in STOP_TRIGGERS:
        return 0
    if tl.isascii():
        # 只对 ASCII 做长度过滤：中文常用词大量是 2 字（综述/审稿/汇报/论文），
        # 套 len<3 会把它们全当噪声删掉 —— 这是上一版 self-test 变红的直接原因。
        if len(tl) < 3:
            return 0
        return len(re.findall(r"(?<![a-z0-9])" + re.escape(tl) + r"(?![a-z0-9])", q))
    return q.count(tl)



# 覆盖规则：优先于关键词打分。
# 起因（2026-10-21 实测）：查询"导师给了 20 条批注要我改稿"被 SKILL_NAV 判成
# "沟通·协作·反馈"分类，推荐 difficult-workplace-conversations —— 把学术改稿当职场沟通。
OVERRIDES = [
    (r"导师|批注|改稿|修改意见|逐条回复|rebuttal|revision|revise|改稿子|防同类错误",
     ["paper-revision-playbook", "advisor_pattern_gate.py", "academic-paper-reviewer"]),
]

def route(query, cats):
    """按触发器**出现次数**加权打分（词边界匹配 + 停用表）。

    单个触发器封顶 5 次防垄断；同分按 SKILL_NAV 原始顺序。
    """
    q = (query or "").lower()
    for pat, skills in OVERRIDES:
        if re.search(pat, q):
            return [(999, {"id": "revision_override",
                           "name": "改稿 / 导师批注（覆盖规则）",
                           "triggers": [pat], "recommended": skills},
                     re.findall(pat, q))]
    scored = []
    for idx, c in enumerate(cats):
        freq, hits = 0, []
        for t in c["triggers"]:
            n = _count_trigger(q, t)
            if n:
                hits.append(t)
                freq += min(n, 5)
        if hits:
            scored.append((freq, -idx, c, hits))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [(s[0], s[2], s[3]) for s in scored]


def find_workspace(start):
    p = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(p, ".dsh-research")):
            return p
        np_ = os.path.dirname(p)
        if np_ == p:
            break
        p = np_
    return None


def usage_of(ws, task_id):
    p = os.path.join(ws, ".dsh-research", "skill-usage.jsonl")
    if not os.path.isfile(p):
        return None
    used = []
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
        if not isinstance(o, dict):
            continue
        if task_id and str(o.get("taskId")) != str(task_id):
            continue
        for k in ("skill", "skillId", "name"):
            if o.get(k):
                used.append(str(o[k]))
                break
    return used


def task_id_of(delivery):
    p = os.path.join(delivery, "claims.json")
    if os.path.isfile(p):
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
            if d.get("taskId"):
                return d["taskId"]
        except Exception:
            pass
    return os.path.basename(os.path.abspath(delivery))


def cmd_route(a, cats):
    scored = route(a.query, cats)
    if not scored:
        print("未匹配到分类；用 list 看全部")
        return 1
    n, c, hits = scored[0]
    print(f"任务：{a.query}")
    print(f"分类：{c['name']}（命中触发器 {len(hits)}：{', '.join(hits[:6])}）")
    print("应加载：")
    for s in c["recommended"]:
        print(f"  - {s}")
    if a.json:
        print(json.dumps({"category": c["id"], "recommended": c["recommended"]}, ensure_ascii=False))
    return 0


def cmd_check(a, cats):
    delivery = a.target
    ws = find_workspace(delivery) if delivery else (os.environ.get("SCI_WORKSPACE") or os.getcwd())
    if not ws:
        print(f"找不到工作区（{delivery} 上溯无 .dsh-research）；用 SCI_WORKSPACE 指定")
        return 1
    tid = a.task or (task_id_of(delivery) if delivery else None)
    used = usage_of(ws, tid)
    if used is None:
        print(f"缺少 {os.path.join(ws, '.dsh-research', 'skill-usage.jsonl')}：本任务没有任何技能使用记录")
        return 1
    if a.category:
        cats_sel = [c for c in cats if c["id"] == a.category or c["name"] == a.category]
    elif a.query:
        s = route(a.query, cats)
        cats_sel = [s[0][1]] if s else []
    else:
        # 从交付文档推断任务类型（不猜就把 15 类全并进来，等于没对账）
        probe = ""
        for f in ("REPORT.md", "MORNING_REPORT.md", "README.md"):
            fp = os.path.join(delivery or "", f)
            if os.path.isfile(fp):
                probe = io.open(fp, encoding="utf-8", errors="replace").read(3000)
                break
        s = route(probe, cats) if probe else []
        cats_sel = [s[0][1]] if s else []
        if cats_sel:
            print(f"（按交付内容推断任务类型：{cats_sel[0]['name']}）")
        else:
            print("未能从交付推断任务类型 → 只报使用量，不做缺少判定（可用 --category 指定）")
    required = []
    for c in cats_sel:
        required += c["recommended"]
    required = list(dict.fromkeys(required))
    miss = [s for s in required if s not in used] if required else []
    print(f"任务 {tid}：技能使用记录 {len(used)} 条，去重 {len(set(used))} 个")
    print(f"  实际用过：{', '.join(sorted(set(used))[:12])}")
    print(f"  应加载 {len(required)} 个，缺 {len(miss)} 个：{', '.join(miss) if miss else '（无）'}")
    if a.json:
        print(json.dumps({"taskId": tid, "used": sorted(set(used)), "required": required,
                          "missing": miss}, ensure_ascii=False))
    if miss and (a.strict or a.category):
        print("SKILL_ROUTING: FAIL（该用未用）")
        return 1
    print("SKILL_ROUTING: OK" + ("（有缺项，未开 --strict 不阻断）" if miss else ""))
    return 0


def cmd_list(a, cats):
    for c in cats:
        rec = ", ".join(c["recommended"][:6]) or "（无推荐）"
        print(f"{c['id']:<16} {c['name'][:22]:<24} → {rec}")
    return 0


def cmd_selftest():
    cats, src = load_categories()
    print(f"数据源: {src}")
    ok = 0
    total = 4
    # 正：科研类查询应命中 sci_research
    s = route("帮我做一篇综述，需要文献检索和审稿意见", cats)
    hit = bool(s) and s[0][1]["id"] in ("sci_research",)
    print(f"  [{'PASS' if hit else 'FAIL'}] 路由识别科研类 → {s[0][1]['id'] if s else '无'}")
    ok += hit
    # 正：PPT 查询
    s2 = route("做一个汇报 PPT，别太有 AI 感", cats)
    hit2 = bool(s2) and ("ppt" in str(s2[0][1]["id"]) or "PPT" in s2[0][1]["name"])
    print(f"  [{'PASS' if hit2 else 'FAIL'}] 路由识别 PPT 类 → {s2[0][1]['id'] if s2 else '无'}")
    ok += hit2
    # 负：无关查询不应强行推荐
    s3 = route("今天天气如何", cats)
    hit3 = not s3
    print(f"  [{'PASS' if hit3 else 'FAIL'}] 无关查询不硬凑分类")
    ok += hit3
    # 正：改稿类必须命中 paper-revision-playbook（覆盖规则）
    s4 = route("导师给了 20 条批注意见，要我改稿并逐条回复", cats)
    hit5 = bool(s4) and s4[0][1]["recommended"][0] == "paper-revision-playbook"
    print(f"  [{'PASS' if hit5 else 'FAIL'}] 改稿类命中 paper-revision-playbook → "
          f"{s4[0][1]['id'] if s4 else '无'}")
    ok += hit5
    total += 1
    # 正：对账能读出真实记录
    ws = os.environ.get("SCI_WORKSPACE") or os.getcwd()
    used = usage_of(ws, "2026-10-17-ai4science-2026")
    hit4 = bool(used)
    print(f"  [{'PASS' if hit4 else 'FAIL'}] 能读出真实使用记录（{len(used or [])} 条）")
    ok += hit4
    print(f"\nSELFTEST: {ok}/{total}")
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("route"); r.add_argument("query"); r.add_argument("--json", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("target", nargs="?", default=None)
    c.add_argument("--task", default=None)
    c.add_argument("--category", default=None)
    c.add_argument("--query", default=None)
    c.add_argument("--strict", action="store_true")
    c.add_argument("--json", action="store_true")
    ls = sub.add_parser("list")
    s = sub.add_parser("self-test")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    cats, _ = load_categories()
    if a.self_test or a.cmd == "self-test":
        return cmd_selftest()
    if a.cmd == "route":
        return cmd_route(a, cats)
    if a.cmd == "check":
        return cmd_check(a, cats)
    if a.cmd == "list":
        return cmd_list(a, cats)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
