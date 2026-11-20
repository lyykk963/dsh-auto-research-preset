#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfcheck.py — 预设自检总入口（一条命令、一行输出、异常才展开）。

设计目标（2026-10-17 定）：
  预设曾经有两个「静默失效」瞒了几个月（13 个技能不可加载 / 3 个出版样式的色环被清空），
  共同点是**没有任何例行检查**。本入口把两类检查合成一条命令，并保证：
    · 正常时只输出一行，不占注意力；
    · 异常时展开到"哪一项、为什么"；
    · 有**真实故障**才 exit 1 —— 预算超支这类"待重构"只算 warn，避免永远报红
      （永远报红的报警等于没有报警，skill_health v9.2 已踩过这个坑）。

包含：
  1) 技能层：skill_health.py   —— name 不合规且无 ASCII 指针代偿的技能数
  2) 资产层：audit_preset_assets.py —— py/json/md/links/mplstyle/体积预算

用法：
  python selfcheck.py            # 一行汇总
  python selfcheck.py -v         # 展开到每项
exit 0 = 无真实故障（可有 warn）；1 = 有 fail。
纯标准库。
"""
import argparse
import glob
import json
import os
import subprocess
import sys
def _resolve_workspace(default):
    """工作区解析：SCI_WORKSPACE > 含 .dsh-research 的当前目录 > 内置默认值。"""
    env = os.environ.get("SCI_WORKSPACE")
    if env and os.path.isdir(env):
        return env
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".dsh-research")):
        return cwd
    return default



HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_HEALTH = os.path.join(HERE, "skill_health.py")
AUDIT = os.path.join(HERE, "audit_preset_assets.py")
DATA_DIR = os.path.join(_resolve_workspace(os.getcwd()), ".dsh-research")


def check_logs(data_dir):
    """工作区日志必须能被 UTF-8 解码且逐行是合法 JSON。

    背景（2026-10-17 实测）：同一个 .jsonl 里混了 UTF-8 与 GBK 两种编码
    （不同时期 Appends 的默认编码不同），UTF-8 读会乱码、GBK 读会失败。
    JSON 能"碰巧解析"不代表内容没坏 —— 只有逐行严格解码才能发现。
    """
    if not os.path.isdir(data_dir):
        return None, []
    bad = []
    files = glob.glob(os.path.join(data_dir, "**", "*.jsonl"), recursive=True)
    files += glob.glob(os.path.join(data_dir, "reviews", "*.json"))
    files += glob.glob(os.path.join(data_dir, "*.json"))
    files = [f for f in files if not f.endswith((".bak", ".gbk.bak", ".bak.mixed"))]
    for p in files:
        rel = os.path.relpath(p, data_dir)
        # 规则：.jsonl 必须严格 UTF-8 无 BOM（BOM 会破坏追加语义与逐行解析）；
        #       .json 容忍 UTF-8 BOM（Windows 上 PowerShell 写出的常态，且 json.loads 前可剥）。
        enc = "utf-8" if p.endswith(".jsonl") else "utf-8-sig"
        try:
            txt = open(p, "rb").read().decode(enc)
        except UnicodeDecodeError:
            bad.append(f"{rel}: 非 UTF-8")
            continue
        if p.endswith(".jsonl"):
            for i, line in enumerate(txt.splitlines(), 1):
                if line.strip():
                    try:
                        json.loads(line)
                    except Exception:
                        bad.append(f"{rel}: 第 {i} 行非 JSON")
                        break
        else:
            try:
                json.loads(txt)
            except Exception:
                bad.append(f"{rel}: 非 JSON")
    return len(files), bad


def run_json(script, extra=()):
    """跑子脚本 --json，返回 (dict|None, err)。"""
    if not os.path.isfile(script):
        return None, f"missing script: {os.path.basename(script)}"
    try:
        p = subprocess.run([sys.executable, script, "--json", *extra],
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    out = (p.stdout or "").strip()
    if not out:
        return None, (p.stderr or "").strip()[:200] or "empty stdout"
    try:
        return json.loads(out), None
    except Exception as e:
        return None, f"bad json ({e}); stderr={((p.stderr or '').strip()[:160])}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="只跑技能层（纯标准库，~0.3 s）；跳过资产层与日志层")
    ap.add_argument("--data-dir", default=DATA_DIR, help="工作区 .dsh-research 路径（日志检查用）")
    args = ap.parse_args()

    details, fails, warns = [], [], []

    # 1) 技能层
    d, err = run_json(SKILL_HEALTH)
    if err:
        fails.append(f"skills: {err}")
        sk_txt = "skills=ERR"
    else:
        un = sum(1 for x in d.get("dropped", []) if not x.get("shimmed_by"))
        tot = d.get("dropped_count", 0)
        sk_txt = f"skills={tot}不合规/待修{un}"
        if un:
            fails.append(f"skills: {un} 个技能仍不可加载且无指针代偿")
            for x in d.get("dropped", []):
                if not x.get("shimmed_by"):
                    details.append(f"   · {x.get('dir')} (name={x.get('name')})")

    # 2) 资产层（--fast 跳过）
    if args.fast:
        as_txt = "assets=skipped"
        a = None
        err = None
    else:
        a, err = run_json(AUDIT)
    if args.fast:
        pass
    elif err:
        fails.append(f"assets: {err}")
        as_txt = "assets=ERR"
    else:
        s = a.get("summary", {})
        as_txt = f"assets={s.get('passed')}pass/{s.get('failed')}fail/{s.get('warned')}warn"
        if s.get("failed"):
            fails.append(f"assets: {s['failed']} 项失败检查")
            for c in a.get("checks", []):
                if not c["ok"] and not c.get("warn_only"):
                    details.append(f"   · [{c['group']}] {c['item']} :: {c['detail'][:140]}")
        for c in a.get("checks", []):
            if not c["ok"] and c.get("warn_only"):
                warns.append(f"   · [{c['group']}] {c['item']}")

    # 3) 工作区日志：UTF-8 + 逐行合法 JSON
    nf, logbad = check_logs(args.data_dir)
    if nf is None:
        lg_txt = "logs=NA"
    else:
        lg_txt = f"logs={nf}files" + (f"/{len(logbad)}bad" if logbad else "")
        if logbad:
            fails.append(f"logs: {len(logbad)} 个日志文件异常（编码或 JSON）")
            for x in logbad[:6]:
                details.append(f"   · {x}")

    head = "SELFCHECK: " + ("OK" if not fails else "FAIL")
    print(f"{head} | {sk_txt} | {as_txt} | {lg_txt}")
    if fails:
        for f in fails:
            print(f"  ! {f}")
        for x in details:
            print(x)
    if warns and (args.verbose or fails):
        for w in warns:
            print(f"  ~ warn {w.lstrip(' ·')}")
    if args.verbose:
        print(f"  (scripts: {os.path.basename(SKILL_HEALTH)}, {os.path.basename(AUDIT)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
