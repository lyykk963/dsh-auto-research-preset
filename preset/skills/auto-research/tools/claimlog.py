#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claimlog.py — 分析脚本的"顺手记账"助手（P1：证据自动化）。

为什么存在（`.dsh-research/memory/capability-gaps.md` P1）：
  2026-10-17 的交付里，每个数字都是我人肉抄进 `claims.json` 的。
  抄漏了一条 `n==16` 的不变量，就让 R3-C1（模型比较用 17 点却说 16 个月）溜过了 11/11 的检查。
  **能自动产出的东西不该靠人记得。**

用法（在分析脚本里）：
    import sys; sys.path.insert(0, "<preset>/tools")
    from claimlog import ClaimLog
    log = ClaimLog("<交付目录>/claims.json", task_id="...")
    log.sample("C3", "固定集前段均值",                 # 声明一个"能从 primary 重算"的数
               source="evidence/monthly-series-fixed.json",
               expr="round(sum(r['count'] for r in data if r['month']<='2026-02')/9, 1)",
               value=pre_mean)
    log.pointer("C6", "台阶增量", source="evidence/trend-stats.json",
                pointer="model_comparison.models.趋势+台阶.coef.2", value=step)
    log.contains("C8", "报告写了 125 个唯一仓库", file="REPORT.md", needle="125 个唯一仓库")
    log.check()   # 写完立即用 check_claims 复验；不一致则抛异常，脚本不会"带病出图"

设计要点：
  · `sample()` 的 `expr` 必须只依赖 **primary 数据**（不是派生统计文件）——
    这是它比 `pointer()` 值钱的地方：派生文件可以由同一个 bug 生成，primary 不会。
  · 每条 claim 带 `origin: "script"`；重跑时**保留**人工添加的（origin != script）条目。
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_claims.py")


class ClaimLog:
    def __init__(self, path, task_id=None, preserve=True):
        self.path = path
        self.task_id = task_id
        self.claims = []
        self._keep = []
        if preserve and os.path.isfile(path):
            try:
                old = json.load(io.open(path, encoding="utf-8-sig"))
                self.task_id = self.task_id or old.get("taskId")
                self._keep = [c for c in old.get("claims", [])
                              if c.get("origin") != "script"]
            except Exception:
                self._keep = []
        self._n = 0

    # ---------- 三种声明 ----------
    def _add(self, cid, text, **kw):
        c = {"id": cid, "text": text, "origin": "script"}
        c.update({k: v for k, v in kw.items() if v is not None})
        self.claims.append(c)
        self._n += 1
        return c

    def sample(self, cid, text, source, expr, value, tolerance=0.0):
        """值 = 由 primary 数据重算（推荐：任何均值/计数/比值都用这个）。

        source 可为 str 或 [str,...]（多份 primary 时 data 是列表）。
        """
        kw = {"sources": source} if isinstance(source, (list, tuple)) else {"source": source}
        return self._add(cid, text, mode="compute", compute=expr,
                         expect=value, tolerance=tolerance, **kw)

    def pointer(self, cid, text, source, pointer, value, tolerance=0.0):
        """值 = 派生物里的字段（用于无法用简单表达式重算的量，如回归系数）。"""
        return self._add(cid, text, mode="pointer", source=source, pointer=pointer,
                         expect=value, tolerance=tolerance)

    def contains(self, cid, text, file, needle, expect=True):
        """断言某文件里确实出现（或不出现）某串——用于台账类"已改"。"""
        return self._add(cid, text, mode="contains", source=file, contains=needle, expect=expect)

    # ---------- 收尾 ----------
    def write(self):
        mine = {x["id"] for x in self.claims}
        claims = [c for c in self._keep if c.get("id") not in mine] + self.claims
        spec = {"taskId": self.task_id,
                "note": "本文件由分析脚本经 tools/claimlog.py 自动产出（origin=script），"
                        "重跑脚本会刷新；人工补充的条目（无 origin）会被保留。",
                "claims": claims}
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with io.open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        return len(claims)

    def check(self):
        """写完立刻用独立检查器复验——不一致就抛异常，禁止"带病出图"。"""
        n = self.write()
        rd = os.path.dirname(os.path.abspath(self.path))
        try:
            p = subprocess.run([sys.executable, CHECKER, rd],
                               capture_output=True, text=True, timeout=180)
        except Exception as e:
            raise RuntimeError(f"claimlog.check 无法调用检查器: {e}")
        tail = (p.stdout or "").strip().splitlines()
        last = tail[-1] if tail else ""
        if p.returncode != 0:
            raise RuntimeError("CLAIMLOG 自检失败（声明与证据不符，禁止继续）：\n"
                               + "\n".join(tail[-8:]))
        print(f"CLAIMLOG: 写入 {n} 条并自检通过（{last}）")
        return n
