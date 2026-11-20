#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""host_check.py — 报告：当前宿主是谁、四层能力各剩多少、哪些降级了。

用法：python tools/host_check.py [--json]
exit 0 = 核心可用；1 = 核心缺失（缺 SKILL.md 或缺工具）
"""
import argparse
import glob
import io
import json
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

HOSTS = [
    ("DSH", os.path.join(os.environ.get("APPDATA", ""), "dsh-desktop")),
    ("Claude Code", os.path.join(os.path.expanduser("~"), ".claude")),
    ("Codex CLI", os.path.join(os.path.expanduser("~"), ".codex")),
    ("Trae", os.path.join(os.path.expanduser("~"), ".trae-cn")),
    ("Cursor", os.path.join(os.path.expanduser("~"), ".cursor")),
    ("Gemini CLI", os.path.join(os.path.expanduser("~"), ".gemini")),
]

CORE_TOOLS = ["check_claims.py", "prereg.py", "check_delivery.py",
              "fetch.py", "claimlog.py", "check_deck.py", "stage_gate.py", "selfcheck.py"]


def has_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    detected = [n for n, p in HOSTS if os.path.isdir(p)]
    py_ok = sys.version_info >= (3, 8)
    l1 = os.path.isfile(os.path.join(PKG, "SKILL.md"))
    l2 = os.path.isdir(os.path.join(PKG, "contracts")) and os.path.isdir(os.path.join(PKG, "references"))
    tools = [t for t in CORE_TOOLS if os.path.isfile(os.path.join(HERE, t))]
    missing = [t for t in CORE_TOOLS if t not in tools]

    ws = os.environ.get("SCI_WORKSPACE") or os.getcwd()
    ws_ready = os.path.isdir(os.path.join(ws, ".dsh-research"))

    opt = {
        "matplotlib（出图）": has_module("matplotlib"),
        "python-pptx（读 pptx）": has_module("pptx"),
        "pywin32（导出 PPT 预览，仅 Windows）": has_module("win32com"),
        "pandoc（转 docx/LaTeX）": bool(shutil.which("pandoc")),
    }

    info = {
        "hosts_detected": detected,
        "python": platform.python_version(),
        "python_ok": py_ok,
        "platform": platform.system(),
        "package": PKG,
        "L1_skill_md": l1,
        "L2_contracts": l2,
        "L3_tools": tools,
        "L3_missing": missing,
        "workspace": ws,
        "workspace_ready": ws_ready,
        "optional": opt,
    }

    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return 0 if (l1 and not missing and py_ok) else 1

    print("=" * 66)
    print("科研自动化 · 宿主能力自检")
    print("=" * 66)
    print(f"  宿主（本机识别到）：{', '.join(detected) if detected else '未识别（不影响 L1–L3）'}")
    print(f"  Python {platform.python_version()}（{'OK' if py_ok else '需要 3.8+'}） · {platform.system()}")
    print()
    print(f"  L1 方法论 SKILL.md        {'OK' if l1 else '缺失'}")
    print(f"  L2 契约与参考             {'OK' if l2 else '缺失'}")
    print(f"  L3 机检工具               {len(tools)}/{len(CORE_TOOLS)} 可用"
          + (f"（缺：{', '.join(missing)}）" if missing else ""))
    print(f"  进度工作区 .dsh-research   {'就绪' if ws_ready else '未建立 → ' + ws}")
    print()
    print("  可选能力：")
    for k, v in opt.items():
        print(f"    {'OK  ' if v else '缺  '} {k}")
    print()
    print("  降级提示：")
    if not any(h in detected for h in ("DSH", "Claude Code", "Codex CLI")):
        print("    · 未检测到支持独立子代理的宿主 → 质量门只能 DRIVE，不能 ACQUIT")
        print("      交付里请写：质量门：DRIVE only（宿主无独立评审能力）")
    if not ws_ready:
        print("    · 先建工作区：mkdir <工作区>/.dsh-research（或设 SCI_WORKSPACE）")
    if not opt["matplotlib（出图）"]:
        print("    · 无 matplotlib → 图相关步骤跳过；check_deck 仍然可用")
    print()
    print("HOST_CHECK:", "OK" if (l1 and not missing and py_ok) else "FAIL")
    return 0 if (l1 and not missing and py_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
