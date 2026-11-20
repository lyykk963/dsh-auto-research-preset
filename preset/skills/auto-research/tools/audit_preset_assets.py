#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预设资产回归测试 v0（read-only 诊断）。

动机：2026-10-17 发现 14 个技能被 DSH **静默丢弃**数月无人察觉，
且 tools/styles/nature.mplstyle 在 matplotlib 3.11 下解析失败（当时被绕过而非修复）。
这两件事同属一类缺陷：**预设携带的资产没有随环境漂移做回归**。

本脚本把"资产是否还能用"变成一条可复算的命令，输出 CHECKS: n pass / m fail。

用法：
  python audit_preset_assets.py                 # 全量
  python audit_preset_assets.py --json          # 机器可读
exit 0 = 全部通过；1 = 有失败项（= 该修了）。
纯标准库（matplotlib 检查为可选，缺失则跳过）。
"""
import argparse
import ast
import hashlib
import io
import json
import os
import re
import sys

PRESET = os.environ.get("AUTO_RESEARCH_PRESET_DIR") or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "dsh-desktop", "harness", ".agent-presets", "auto-research")
SUBDIRS = ["skills", "tools", "contracts", "templates", "gates", "assets", "reference"]
LINK_RE = re.compile(r"(?<![\\/A-Za-z0-9_.\-])(?:tools|templates|gates|contracts|assets|references|reference)[\\/][A-Za-z0-9_.\\/-]+"
                     r"\.(?:py|md|json|mplstyle)")


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "__pycache__", ".git")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=PRESET)
    args = ap.parse_args()
    root = args.root

    checks = []   # dict(ok, group, item, detail, warn_only)

    def add(ok, group, item, detail="", warn_only=False):
        checks.append({"ok": bool(ok), "group": group, "item": item,
                       "detail": detail, "warn_only": bool(warn_only)})

    if not os.path.isdir(root):
        print(f"[FATAL] 预设根不存在：{root}")
        return 2

    # A. 清单（按"包"归组：skills/<bundle> 单独一档，其余按顶层目录）
    inventory = {}
    for f in walk(root):
        rel = os.path.relpath(f, root).replace("\\", "/")
        parts = rel.split("/")
        key = f"skills/{parts[1]}" if parts[0] == "skills" and len(parts) >= 3 else parts[0]
        d = inventory.setdefault(key, {"files": 0, "bytes": 0})
        d["files"] += 1
        d["bytes"] += os.path.getsize(f)
    for d in inventory.values():
        d["kb"] = round(d["bytes"] / 1024, 1)

    # B. Python 语法（compile，不执行）
    py_files = [f for f in walk(root) if f.endswith(".py")]
    bad_py = []
    for f in py_files:
        try:
            compile(io.open(f, encoding="utf-8-sig").read(), f, "exec")
        except Exception as e:
            bad_py.append((f, f"{type(e).__name__}: {e}"))
    add(not bad_py, "python", f"{len(py_files)} 个 .py 可编译", "; ".join(f"{os.path.basename(a)}: {b}" for a, b in bad_py[:3]))

    # C. JSON 可解析
    js = [f for f in walk(root) if f.endswith(".json")]
    bad_json = []
    for f in js:
        try:
            json.load(io.open(f, encoding="utf-8-sig"))
        except Exception as e:
            bad_json.append((f, f"{type(e).__name__}"))
    add(not bad_json, "json", f"{len(js)} 个 .json 可解析", "; ".join(os.path.basename(a) for a, _ in bad_json[:5]))

    # D. Markdown 非空
    mds = [f for f in walk(root) if f.endswith(".md")]
    empty_md = [f for f in mds if os.path.getsize(f) < 16]
    add(not empty_md, "markdown", f"{len(mds)} 个 .md 非空",
        "空文件: " + "; ".join(os.path.relpath(f, root) for f in empty_md[:5]))

    # E. 交叉引用（SKILL.md 里提到的资产是否真在）
    skills = []
    sroot = os.path.join(root, "skills")
    bundle_roots = []
    if os.path.isdir(sroot):
        for e in sorted(os.listdir(sroot)):
            p = os.path.join(sroot, e, "SKILL.md")
            if os.path.isfile(p):
                skills.append(p)
            bundle_roots.append(os.path.join(sroot, e))
    missing_refs = []
    for sk in skills:
        try:
            txt = io.open(sk, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        # 排除指向工作区（<工作区>/tools/...）的引用——那不是预设资产
        txt = re.sub(r"<工作区>[^\s`|]*", "", txt)
        sdir = os.path.dirname(sk)
        cand_roots = [sdir, root] + bundle_roots
        # 正文里出现的绝对路径，其父目录也是合法解析基准（指针技能 → 真身 时用到）
        for ap in re.findall(r"[A-Za-z]:\\[^\s`*?\"'|<>]+", txt):
            d = os.path.dirname(ap.rstrip("\\/"))
            if d and os.path.isdir(d):
                cand_roots.append(d)
        for tok in set(LINK_RE.findall(txt)):
            t = tok.replace("/", os.sep)
            if any(os.path.exists(os.path.join(r, t)) for r in cand_roots):
                continue
            missing_refs.append((os.path.basename(sdir), tok))
    add(not missing_refs, "links", f"{len(skills)} 个 SKILL.md 的资产引用",
        "; ".join(f"{a}→{b}" for a, b in missing_refs[:6]))

    # F. matplotlib 样式能否 apply，且**声明的颜色数是否真的生效**
    # 两个坑（2026-10-17 实测）：① matplotlib ≥3.11 对非法 rc 值只打 warning、不抛异常；
    #   ② .mplstyle 读取时 _strip_comment() 把第一个 '#' 之后全当注释 → 十六进制色值被截断。
    # ⚡ 2026-10-18（实验 iter1）：import matplotlib ≈2 s，占 selfcheck 全量 ~60%。
    #    按样式文件内容 sha256 缓存结果；文件一变 key 就变，**覆盖率不降**。
    styles = [f for f in walk(root) if f.endswith(".mplstyle")]
    style_msg = "无 .mplstyle"
    style_ok = True
    if styles:
        import tempfile
        cache_path = os.path.join(tempfile.gettempdir(), "dsh-audit-mplstyle.json")
        h = hashlib.sha256()
        for s in sorted(styles):
            h.update(os.path.basename(s).encode())
            try:
                h.update(open(s, "rb").read())
            except Exception:
                h.update(b"?")
        key = h.hexdigest()
        cached = None
        try:
            c = json.load(io.open(cache_path, encoding="utf-8"))
            if c.get("key") == key:
                cached = (bool(c.get("ok")), c.get("msg", ""))
        except Exception:
            cached = None
        if cached is not None:
            style_ok, style_msg = cached
            style_msg += "（缓存命中）"
        else:
            try:
                import contextlib
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                def declared_cycle_len(path):
                    for line in io.open(path, encoding="utf-8", errors="replace"):
                        s = line.strip()
                        if s.startswith("#") or "axes.prop_cycle" not in s:
                            continue
                        val = s.split(":", 1)[1]
                        if "[" not in val or "]" not in val:
                            return None
                        body = val[val.index("[") + 1: val.rindex("]")]
                        depth = 0
                        n = 1
                        for ch in body:
                            if ch in "([":
                                depth += 1
                            elif ch in ")]":
                                depth -= 1
                            elif ch == "," and depth == 0:
                                n += 1
                        return n if body.strip() else 0
                    return None

                bad = []
                for s in styles:
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        try:
                            plt.style.use(s)
                        except Exception as e:
                            bad.append(f"{os.path.basename(s)}: {type(e).__name__}")
                            continue
                    w = err.getvalue().strip()
                    if w:
                        bad.append(f"{os.path.basename(s)}: {w.splitlines()[0][-100:]}")
                        continue
                    want = declared_cycle_len(s)
                    if want is not None:
                        got = len(plt.rcParams["axes.prop_cycle"])
                        if got != want:
                            bad.append(f"{os.path.basename(s)}: 声明 {want} 色，实际生效 {got} 色"
                                       "（疑 '#' 被当注释截断）")
                style_ok = not bad
                style_msg = f"{len(styles)} 个样式，失败 {len(bad)}" + (": " + "; ".join(bad) if bad else "")
                plt.rcdefaults()
            except ImportError:
                style_msg = "matplotlib 未安装，跳过"
            try:
                with io.open(cache_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps({"key": key, "ok": bool(style_ok), "msg": style_msg},
                                       ensure_ascii=False))
            except Exception:
                pass
    add(style_ok, "mplstyle", style_msg)

    # G. 主 SKILL.md 体积预算 —— 超支只算**警告**（不是资产坏了，是待重构）
    main_sk = os.path.join(sroot, "auto-research", "SKILL.md")
    if os.path.isfile(main_sk):
        size = os.path.getsize(main_sk)
        add(size <= 24 * 1024, "size", f"auto-research/SKILL.md {size/1024:.1f} KB（预算 24 KB）",
            "超支：应拆到 references/ 而非继续打补丁（列入改进待办，不阻断）"
            if size > 24 * 1024 else "", warn_only=True)

    # 输出
    if args.json:
        print(json.dumps({"root": root, "inventory": inventory, "checks": checks,
                          "summary": {"total": len(checks),
                                      "passed": sum(1 for c in checks if c["ok"]),
                                      "failed": sum(1 for c in checks if not c["ok"] and not c["warn_only"]),
                                      "warned": sum(1 for c in checks if not c["ok"] and c["warn_only"])}},
                         ensure_ascii=False, indent=1))
    else:
        print("=" * 72)
        print("预设资产回归测试 v0")
        print("=" * 72)
        print(f"根：{root}\n")
        print("清单：")
        for k, v in inventory.items():
            print(f"  {k:<26} {v['files']:>4} files  {v['kb']:>9.1f} KB")
        print("\n检查：")
        for c in checks:
            mark = "ok  " if c["ok"] else ("WARN" if c["warn_only"] else "FAIL")
            print(f"  [{mark}] {c['group']:<10} {c['item']}")
            if c["detail"]:
                print(f"         {c['detail']}")
        p = sum(1 for c in checks if c["ok"])
        f_ = sum(1 for c in checks if not c["ok"] and not c["warn_only"])
        w_ = sum(1 for c in checks if not c["ok"] and c["warn_only"])
        print(f"\nCHECKS: {p} pass / {f_} fail / {w_} warn")

    return 0 if all(c["ok"] or c["warn_only"] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

