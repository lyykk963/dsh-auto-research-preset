#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch.py — 统一取数层（P0）。

为什么存在（见 `.dsh-research/memory/capability-gaps.md`）：
  2026-10-17 一次调研里，取数环节造成 3/6 类摩擦：
    · GitHub Search 未认证 10 req/min → 5 次 403，靠手写 sleep 硬熬；
    · huggingface.co 主站超时（只能用镜像）、export.arxiv.org 持续 429；
    · 中文站 GB2312/GB18030 编码 → 抓下来全是乱码，返工一轮；
    · 每类源都重写一套一次性脚本（当天写了 4 套）。
  本工具把这些收敛成一条命令：**退避重试 + 限速 + 编码自适应 + 镜像回退 + 快照落盘**。

快照纪律：每次取数都落 (raw bytes, meta.json)——meta 记 URL/最终URL/时间/状态/
Content-Type/实际编码/sha256/截断长度。**没有快照 = 没有取过**（评审要能复核）。

用法：
  python fetch.py get <url> [--out DIR] [--text] [--max-chars N] [--json]
  python fetch.py probe [--json]        # 探测已知源的健康度（含镜像回退）
  python fetch.py --self-test           # 用真实失败源做回放（P0 验收）

退出码：0 成功；1 源不可用（已尽力重试）；2 参数错误。
纯标准库。
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from datetime import datetime
def _resolve_workspace(default):
    """工作区解析：SCI_WORKSPACE > 含 .dsh-research 的当前目录 > 内置默认值。"""
    env = os.environ.get("SCI_WORKSPACE")
    if env and os.path.isdir(env):
        return env
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".dsh-research")):
        return cwd
    return default



DEFAULT_OUT = os.path.join(os.path.expandvars(r"%USERPROFILE%\.."), "")
WS_OUT = os.path.join(_resolve_workspace(os.getcwd()), ".dsh-research", "fetch")

# 已知镜像回退：主站不可达时自动换（今天 HF 主站超时、镜像可用）
MIRRORS = {"huggingface.co": ["hf-mirror.com"]}

# 每域最小间隔（秒）——比"每个请求都 sleep 7"精确得多
MIN_INTERVAL = {"api.github.com": 6.5, "github.com": 1.0, "www.nature.com": 2.0,
                "huggingface.co": 1.0, "hf-mirror.com": 1.0}
DEFAULT_INTERVAL = 0.6

_LAST = {}
RETRY_ON = (403, 408, 425, 429, 500, 502, 503, 504)
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "latin-1")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def _throttle(host):
    gap = MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
    prev = _LAST.get(host)
    if prev is not None:
        wait = gap - (time.time() - prev)
        if wait > 0:
            time.sleep(wait)
    _LAST[host] = time.time()


def _decode(raw, charset=None):
    order = ([charset] if charset else []) + list(ENCODINGS)
    for enc in order:
        if not enc:
            continue
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1(replace)"


def _strip_html(t):
    t = re.sub(r"(?s)<script.*?</script>", " ", t)
    t = re.sub(r"(?s)<style.*?</style>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'),
                 ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def snapshot(url, raw, meta, outdir):
    host = re.sub(r"[^A-Za-z0-9._-]", "_", urlparse(url).netloc or "local")
    os.makedirs(outdir, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    stem = hashlib.sha256(url.encode()).hexdigest()[:10]
    base = os.path.join(outdir, host, f"{stem}")
    os.makedirs(os.path.dirname(base), exist_ok=True)
    with open(base + ".bin", "wb") as f:
        f.write(raw)
    meta = dict(meta, url=url, sha256=digest, bytes=len(raw),
                saved_at=datetime.now().isoformat(timespec="seconds"),
                snapshot=os.path.relpath(base + ".bin", outdir))
    with open(base + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return base, meta


def get(url, outdir=WS_OUT, attempts=4, want_text=False, max_chars=0, quiet=False):
    """取一个 URL。返回 dict(status ok|blocked|not_found|error, meta...)。"""
    tried = []
    candidates = [url]
    host = urlparse(url).netloc
    for m in MIRRORS.get(host, []):
        candidates.append(url.replace(host, m, 1))

    for cand in candidates:
        chost = urlparse(cand).netloc
        for i in range(attempts):
            _throttle(chost)
            req = urllib.request.Request(cand, headers={
                "User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "identity",  # 避免 gzip 未解压
            })
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    final = r.geturl()
                    ctype = r.headers.get("Content-Type", "")
                    cs = None
                    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
                    if m:
                        cs = m.group(1)
                    text, enc = _decode(raw, cs)
                    meta = {"final_url": final, "status": r.status, "content_type": ctype,
                            "encoding_used": enc, "elapsed_s": round(time.time() - t0, 2),
                            "attempt": i + 1, "mirror_used": cand != url,
                            "tried": tried}
                    if want_text:
                        text = _strip_html(text)
                        if max_chars and len(text) > max_chars:
                            text = text[:max_chars]
                            meta["truncated_to"] = max_chars
                    base, meta = snapshot(cand, raw, meta, outdir)
                    meta.update({"ok": True, "outcome": "ok", "text": text if want_text else None})
                    if not quiet:
                        print(f"OK   {cand} → {r.status} {len(raw)}B enc={enc}"
                              + (" mirror" if cand != url else ""))
                    return meta
            except urllib.error.HTTPError as e:
                tried.append(f"{cand} #{i+1}: HTTP {e.code}")
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if e.code in RETRY_ON and i < attempts - 1:
                    wait = float(retry_after) if (retry_after or "").isdigit() else min(2 ** i + random.random(), 20)
                    if not quiet:
                        print(f"  retry {e.code} in {wait:.1f}s ({i+1}/{attempts}) {cand}")
                    time.sleep(wait)
                    continue
                last = {"ok": False, "outcome": "blocked" if e.code in (401, 403, 429) else "not_found",
                        "http": e.code, "url": cand, "tried": tried}
                break
            except Exception as e:  # 超时/连接失败/DNS
                tried.append(f"{cand} #{i+1}: {type(e).__name__}")
                if i < attempts - 1:
                    wait = min(2 ** i + random.random(), 15)
                    if not quiet:
                        print(f"  retry {type(e).__name__} in {wait:.1f}s ({i+1}/{attempts}) {cand}")
                    time.sleep(wait)
                    continue
                last = {"ok": False, "outcome": "error", "error": f"{type(e).__name__}: {e}",
                        "url": cand, "tried": tried}
                break
        else:
            last = {"ok": False, "outcome": "error", "url": cand, "tried": tried}
        if last.get("ok") is False and len(candidates) > 1 and last.get("outcome") != "not_found":
            if not quiet:
                print(f"  → 主站失败，试镜像：{candidates[candidates.index(cand)+1] if cand == url else '(无)'}")
    if not quiet:
        print(f"FAIL {url} → {last.get('outcome')} ({last.get('http') or last.get('error')})")
    last["tried"] = tried
    return last


PROBES = [
    ("GitHub Search API", "https://api.github.com/search/repositories?q=topic:ai4science&per_page=1"),
    ("HuggingFace 主站", "https://huggingface.co/api/models?limit=1"),
    ("HuggingFace 镜像", "https://hf-mirror.com/api/models?limit=1"),
    ("arXiv API", "http://export.arxiv.org/api/query?search_query=all:electron&max_results=1"),
    ("Nature 摘要页", "https://www.nature.com/articles/s41586-026-10652-y"),
    ("Claude 文档", "https://claude.com/docs/claude-science/overview"),
    ("央广网（GB18030）", "https://news.cnr.cn/native/gd/20261015/t20261015_527842524.shtml"),
    ("openai.com（已知 403）", "https://openai.com/index/navier-stokes-solution/"),
]


def cmd_get(a):
    r = get(a.url, outdir=a.out, want_text=a.text, max_chars=a.max_chars)
    if a.json:
        print(json.dumps({k: v for k, v in r.items() if k != "text"}, ensure_ascii=False, indent=1))
    if r.get("ok") and a.text and r.get("text"):
        print("\n" + r["text"])
    return 0 if r.get("ok") else 1


def cmd_probe(a):
    rows = []
    for name, url in PROBES:
        r = get(url, outdir=WS_OUT, attempts=2, quiet=True)
        rows.append({"source": name, "url": url, "outcome": r.get("outcome"),
                     "http": r.get("http"), "encoding": r.get("encoding_used"),
                     "mirror": r.get("mirror_used"), "err": r.get("error")})
        mark = "OK  " if r.get("ok") else ("BLOCK" if r.get("outcome") == "blocked" else "FAIL")
        extra = f" mirror={r.get('mirror_used')}" if r.get("mirror_used") else ""
        print(f"  [{mark}] {name:<22} {r.get('outcome'):<9} enc={r.get('encoding_used')}{extra}")
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    ok = sum(1 for x in rows if x["outcome"] == "ok")
    print(f"\nPROBE: {ok}/{len(rows)} 可用（不可用的会明确标 blocked / error，而不是静默返回空）")
    return 0


def cmd_selftest(a):
    """回放今天的 4 个真实摩擦点。"""
    print("=" * 70)
    print("fetch.py 自测：回放 2026-10-17 真实摩擦点")
    print("=" * 70)
    fails = 0

    print("\n[1] GB18030 页面必须解码正确（今天第一次抓是乱码）")
    r = get("https://news.cnr.cn/native/gd/20261015/t20261015_527842524.shtml",
            want_text=True, max_chars=4000, quiet=True)
    ok = r.get("ok") and "Ghys" in (r.get("text") or "")
    print(f"  {'PASS' if ok else 'FAIL'} encoding={r.get('encoding_used')} 含关键词={'Ghys' in (r.get('text') or '')}")
    fails += 0 if ok else 1

    print("\n[2] HF 主站不可达时应自动回退镜像")
    r = get("https://huggingface.co/api/models?limit=1", quiet=True)
    ok = r.get("ok") and r.get("mirror_used") is True
    print(f"  {'PASS' if ok else 'FAIL'} ok={r.get('ok')} mirror_used={r.get('mirror_used')} outcome={r.get('outcome')}")
    fails += 0 if ok else 1

    print("\n[3] 已知 403 的源必须明确报 blocked（不能假装成功）")
    r = get("https://openai.com/index/navier-stokes-solution/", attempts=2, quiet=True)
    ok = (not r.get("ok")) and r.get("outcome") in ("blocked", "error")
    print(f"  {'PASS' if ok else 'FAIL'} outcome={r.get('outcome')} http={r.get('http')}")
    fails += 0 if ok else 1

    print("\n[4] GitHub API 必须带限速（连续 2 次调用间隔 ≥6.5s）")
    t0 = time.time()
    r1 = get("https://api.github.com/repos/karpathy/autoresearch", quiet=True)
    r2 = get("https://api.github.com/repos/SakanaAI/AI-Scientist", quiet=True)
    gap = time.time() - t0
    ok = r1.get("ok") and r2.get("ok") and gap >= 6.4
    print(f"  {'PASS' if ok else 'FAIL'} ok={r1.get('ok')}/{r2.get('ok')} 两次间隔={gap:.1f}s")
    fails += 0 if ok else 1

    print(f"\nSELFTEST: {4 - fails}/4 通过")
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="统一取数层：退避重试 + 限速 + 编码自适应 + 镜像回退 + 快照")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("get")
    g.add_argument("url")
    g.add_argument("--out", default=WS_OUT)
    g.add_argument("--text", action="store_true")
    g.add_argument("--max-chars", type=int, default=0)
    g.add_argument("--json", action="store_true")
    g.set_defaults(fn=cmd_get)
    p = sub.add_parser("probe")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_probe)
    s = sub.add_parser("self-test")
    s.set_defaults(fn=cmd_selftest)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if getattr(a, "self_test", False):
        a.fn = cmd_selftest
        return cmd_selftest(a)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
