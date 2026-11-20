#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_health.py — 技能层健康检查（v9.2）

定位：把「技能被静默丢弃」这类故障变成**可见**的。

背景（实测）：
  DSH 的技能名必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`
  （node_modules/@deepseek-ai/dsh-skill/lib/index.js:17）。
  不匹配者被 `dsh-skill-filesystem` 的 parseSkillFile **静默跳过**
  （lib/index.js:685-688 `return`，只留一条 logger.warn）。
  本机实测：14 个技能因此失效（13 个 trae-cn 侧中文 name + 1 个
  frontmatter 缺 name 的 `senior-computer-vision`），
  其中包含本预设方法论主体「融合研究」（frontmatter `name: 融合研究` 是中文）——
  预设 persona 却一直写着「加载 skill 融合研究」，于是每次会话都以"加载失败"
  开场，且**任何地方都不报错**。

处置现状（2026-10-17，v9.2）：
  真身 `name` **不能改**——Trae 的 `~/.trae-cn/skill-config.json` 以 `name`
  作 `managedSkills` 的键，改名会打断 Trae 侧注册。
  改用 **ASCII 指针技能**代偿（与预设里 fusion-research 同一模式）：
    · 12 个指针建在 `~/.agents/skills/<ascii-name>/SKILL.md`（正文写真身路径）；
    · `senior-computer-vision` 的假 junction（64 字节文本）重建为真 Junction；
    · 「融合研究」→ 预设内置 `fusion-research` 指针。
  批量工具：`<工作区>/tools/install_ascii_skill_pointers.py`（幂等）。

  ⇒ 因此本脚本 v9.2 起**动态识别指针代偿**：若某个 ASCII 技能的正文引用了
    待修真身的 SKILL.md 路径，则判定「已代偿」。这类条目**照常列出**（信息，
    用于审计），但**不计入"待修"、不致 exit 1**。否则真身永远中文、脚本永远
    报红，报警就废了。

本脚本让这类故障在下一次会话开头就能被看见。

另可校验 PPT 模板索引漂移（--ppt-index），因为模板以索引 + sha256 方式引用而非复制。

用法：
  python skill_health.py                                  # 默认扫描本机两个技能根
  python skill_health.py --json                            # 机器可读（含 shimmed_by 字段）
  python skill_health.py --ppt-index <index.json>          # 附带模板索引漂移检查
  python skill_health.py --roots <dir> [--roots <dir> ...]

exit 0 = 无**待修**问题（不合规项已全部由指针代偿）；
         1 = 仍存在未代偿的不合规技能 / 索引漂移 / 目录缺失。
纯标准库。
"""
import argparse
import hashlib
import json
import os
import re
import sys

# 与 @deepseek-ai/dsh-skill 的 SKILL_NAME 保持一字不差
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# 指针技能正文里的"真身绝对路径"（用于动态识别代偿，见 collect_shims）
SHIM_PATH_RE = re.compile(r"[A-Za-z]:\\[^`\"'|>\r\n]+?SKILL\.md", re.IGNORECASE)

DEFAULT_ROOTS = [
    os.path.expandvars(r"%USERPROFILE%\.trae-cn\skills"),
    os.path.expandvars(r"%USERPROFILE%\.agents\skills"),
]

# 代偿判定的兜底白名单：真身 `name`（不改，Trae 侧以它为键）。
# 主判定是**动态的**——见 find_shim()：任一 ASCII 技能正文引用了待修真身的
# SKILL.md 路径即视为已代偿。这里只兜住「指针不在被扫描根内」的情形
# （fusion-research 指针位于 preset 目录，不在上面两个根里）。
KNOWN_SHIMNED = {"融合研究"}


def root_label(root):
    """把技能根压成可读短标签，避免两个根都显示成 'skills'。"""
    low = root.replace("\\", "/").lower()
    if ".trae-cn" in low:
        return "trae-cn"
    if ".agents" in low:
        return "agents"
    if "agent-presets" in low or "auto-research" in low:
        return "preset"
    return os.path.basename(root.rstrip("\\/"))


def parse_name(skill_md):
    """从 SKILL.md 抽取 frontmatter 的 name。纯标准库，只处理 name 一行。

    注意：这是**近似**解析（不引 yaml）。对 name 字段已足够：
    支持 `name: x` / `name: "x"` / `name: 'x'`，并剥离两端引号。
    """
    try:
        with open(skill_md, encoding="utf-8-sig", errors="replace") as f:
            text = f.read(4096)
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    block = text[3:end] if end != -1 else text[3:]
    for line in block.splitlines():
        if line.startswith("name:"):
            v = line[5:].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            return v
    return None


def collect_shims(roots):
    """收集所有**合规**技能的正文里引用到的真身路径，用于判定「是否已有 ASCII 指针代偿」。

    判据：某个 name 合法（ASCII kebab-case）的 SKILL.md，其正文里出现了
    待修技能真身 SKILL.md 的绝对路径（大小写与斜杠方向归一）。这对应预设里
    fusion-research / 各 ASCII 指针技能的做法：**改指针、不改真身**。

    性能：只抽一次路径集合（集合查表），不做 N×M 全文子串匹配
    （2026-10-17 实测：984 技能 × 13 待修 × 20 KB 全文匹配 = 3.8 s，改成集合后 ~0.4 s）。
    """
    shims = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            skill_md = os.path.join(root, entry, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            name = parse_name(skill_md)
            if not name or not SKILL_NAME.match(name):
                continue
            try:
                with open(skill_md, encoding="utf-8-sig", errors="replace") as f:
                    body = f.read(8192)
            except Exception:
                continue
            paths = {p.replace("/", "\\").lower() for p in SHIM_PATH_RE.findall(body)}
            if paths:
                shims.append((name, paths))
    return shims


def find_shim(real_path, shims):
    """返回代偿该真身的指针技能名（找不到则 None）。"""
    key = real_path.replace("/", "\\").lower()
    for name, paths in shims:
        if key in paths:
            return name
    return None


def scan_roots(roots):
    dropped, missing, total = [], [], 0
    shims = collect_shims(roots)
    for root in roots:
        if not os.path.isdir(root):
            missing.append(root)
            continue
        for entry in sorted(os.listdir(root)):
            d = os.path.join(root, entry)
            if not os.path.isdir(d):
                continue
            skill_md = os.path.join(d, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            total += 1
            name = parse_name(skill_md)
            # 指针代偿判定：① 若某 ASCII 技能的正文引用了本真身路径 → 自动认定；
            #                ② 否则若在 KNOWN_SHIMNED 白名单 → 认定为预设内置指针。
            shim = find_shim(skill_md, shims)
            if not shim and name in KNOWN_SHIMNED:
                shim = "fusion-research（预设内置）"
            if name is None:
                dropped.append({"root": root, "dir": entry, "name": None,
                                "shimmed_by": shim,
                                "reason": "frontmatter 缺 name（DSH 要求 name+description）"})
            elif not SKILL_NAME.match(name):
                dropped.append({"root": root, "dir": entry, "name": name,
                                "shimmed_by": shim,
                                "reason": f"name 不匹配 {SKILL_NAME.pattern}（非 ASCII kebab-case）"})
    return dropped, missing, total


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def check_ppt_index(index_path):
    """校验 PPT 模板索引：文件是否仍在、sha256 是否漂移。"""
    problems = []
    try:
        with open(index_path, encoding="utf-8-sig") as f:
            idx = json.load(f)
    except Exception as e:
        return [{"item": index_path, "reason": f"索引不可读：{type(e).__name__}: {e}"}]
    for item in idx.get("templates", []):
        p = item.get("path", "")
        want = item.get("sha256", "")
        if not os.path.isfile(p):
            problems.append({"item": p, "reason": "模板文件不存在（索引指向已失效路径）"})
            continue
        got = sha256(p)
        if want and got != want:
            problems.append({"item": p, "reason": f"sha256 漂移：索引 {want[:12]}… 实际 {got[:12]}…"})
    return problems


def main():
    ap = argparse.ArgumentParser(description="技能层健康检查（技能名合法性 / PPT 模板索引漂移）")
    ap.add_argument("--roots", action="append", default=None,
                    help="技能根目录，可多次传入；默认 ~/.trae-cn/skills 与 ~/.agents/skills")
    ap.add_argument("--ppt-index", default=None, help="PPT 模板索引 JSON 路径")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    roots = args.roots if args.roots else DEFAULT_ROOTS
    dropped, missing, total = scan_roots(roots)
    ppt_problems = check_ppt_index(args.ppt_index) if args.ppt_index else []

    if args.json:
        print(json.dumps({
            "roots": roots,
            "skills_scanned": total,
            "dropped_count": len(dropped),
            "dropped": dropped,
            "missing_roots": missing,
            "ppt_index_problems": ppt_problems,
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print("技能层健康检查（skill_health.py）")
        print("=" * 64)
        for r in roots:
            mark = "OK  " if r not in missing else "MISS"
            print(f"  [{mark}] {r}")
        print(f"\n扫描到 SKILL.md：{total} 个")
        unshimmed = [d for d in dropped if not d.get("shimmed_by")]
        shimmed = [d for d in dropped if d.get("shimmed_by")]
        print(f"名字不合规（DSH 会静默丢弃）：{len(dropped)} 个"
              f"（其中已用指针代偿 {len(shimmed)}，待修 {len(unshimmed)}）\n")
        if dropped:
            print(f"  {'根':<8} {'目录名':<26} {'name':<26} 状态")
            print(f"  {'-'*8} {'-'*26} {'-'*26} {'-'*24}")
            for d in sorted(dropped, key=lambda x: (not x.get("shimmed_by"), str(x["name"]))):
                tag = (f"← 指针 {d['shimmed_by']}" if d.get("shimmed_by")
                       else ("← 指定代偿" if d["name"] in KNOWN_SHIMNED else "**待修**"))
                print(f"  {root_label(d['root']):<8} {d['dir']:<26} {str(d['name']):<26} {tag}")
            if unshimmed:
                print("\n  含义：待修项**不会出现在技能目录里**，也无法被 skill 工具加载。")
                print("  处置：改 frontmatter 的 name 为 ASCII kebab-case，或新建 ASCII 指针技能")
                print("        （本机已有批量脚本：<工作区>/tools/install_ascii_skill_pointers.py）。")
            else:
                print("\n  含义：以上真身仍是中文 name（Trae 侧 registry 以 name 为键，不能改），")
                print("        但均已由 ASCII 指针技能代偿 → DSH 侧可正常发现与加载。")
        if missing:
            print(f"\n[WARN] 技能根不存在：{missing}")
        if ppt_problems:
            print(f"\nPPT 模板索引问题：{len(ppt_problems)} 项")
            for p in ppt_problems:
                print(f"  - {p['item']}\n      {p['reason']}")
        if not unshimmed and not ppt_problems and not missing:
            print("\n未发现**待修**问题（不合规项均已由指针代偿）。")

    unshimmed_final = [d for d in dropped if not d.get("shimmed_by")]
    bad = bool(unshimmed_final) or bool(ppt_problems) or bool(missing)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
