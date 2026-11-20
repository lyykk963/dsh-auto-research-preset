#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# 迁入来源（provenance）— 本文件为冻结副本；上游演进不自动同步，同步需重跑核验
#   上游：D:\code\models\Tools\融合研究\融合研究-共享版\scripts\verify_citations.py
#   上游 sha256（迁入时）：506a7eac11b760c8a6f6ba0430b6c8c890d91d6d6c5bdd5bfa0dc2f838b8cf99
#   迁入日期：2026-09-12 ｜ 迁入依据：融合研究-v8.1-可复用性评估.md（v9.1）
#   本副本改动：无（原样迁入）
# ---------------------------------------------------------------------------
"""引用核验工具 — 防幻觉第二道闸门。

拿待验引用（DOI + 声称的标题/作者/年）回 doi.org 取权威元数据比对，
输出 VERIFIED / METADATA_MISMATCH / DOI_NOT_FOUND 等判定。

用法:
  python verify_citations.py --refs refs.json
  python verify_citations.py --doi 10.1038/s41586-024-07155-5 --title "Attention is all you need"
  python verify_citations.py --bibtex refs.bib
"""

import json
import sys
import time
import urllib.request
import urllib.error
import difflib
from typing import Optional

USER_AGENT = "IntegratedResearch/1.0 (mailto:research@example.com)"
TIMEOUT = 15
MAX_RETRIES = 2


def resolve_doi(doi: str) -> Optional[dict]:
    """通过 doi.org content negotiation 获取 CSL-JSON 元数据。"""
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://dx.doi.org/", "").replace("doi:", "").strip()

    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/vnd.citationstyles.csl+json",
               "User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # DOI 不存在
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
            else:
                return None
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
            else:
                return None
    return None


def title_similarity(t1: str, t2: str) -> float:
    """计算标题相似度。"""
    return difflib.SequenceMatcher(None, t1.lower().strip(), t2.lower().strip()).ratio()


def verify_single_ref(doi: str, claimed_title: str = "",
                      claimed_year: Optional[int] = None,
                      claimed_first_author: str = "") -> dict:
    """核验单条引用。"""
    meta = resolve_doi(doi)
    if meta is None:
        return {
            "doi": doi,
            "status": "DOI_NOT_FOUND",
            "detail": "DOI 无法解析（疑似幻觉引用或 DOI 拼写错误）",
        }

    actual_title = meta.get("title", "")
    actual_year = None
    date_parts = (meta.get("issued") or {}).get("date-parts")
    if date_parts and date_parts[0]:
        actual_year = date_parts[0][0]
    actual_authors = [a.get("family", "") for a in meta.get("author", [])]

    issues = []
    status = "VERIFIED"

    if claimed_title:
        sim = title_similarity(claimed_title, actual_title)
        if sim < 0.7:
            issues.append(f"标题不匹配 (相似度 {sim:.2f}): 声称=\"{claimed_title[:60]}...\" 实际=\"{actual_title[:60]}...\"")
            status = "METADATA_MISMATCH"

    if claimed_year and actual_year and abs(claimed_year - actual_year) > 2:
        issues.append(f"年份不匹配: 声称={claimed_year} 实际={actual_year}")
        status = "METADATA_MISMATCH"

    if claimed_first_author and actual_authors:
        if claimed_first_author.lower() != actual_authors[0].lower():
            issues.append(f"第一作者不匹配: 声称={claimed_first_author} 实际={actual_authors[0]}")
            status = "METADATA_MISMATCH"

    result = {
        "doi": f"https://doi.org/{doi}",
        "status": status,
        "actual_title": actual_title,
        "actual_year": actual_year,
        "actual_first_author": actual_authors[0] if actual_authors else "",
        "issues": issues,
    }
    return result


def verify_bibtex(bibtex_path: str) -> list:
    """解析 BibTeX 文件并核验所有引用。"""
    results = []
    current_entry = {}
    with open(bibtex_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("@"):
                if current_entry.get("doi") or current_entry.get("title"):
                    results.append(verify_single_ref(
                        doi=current_entry.get("doi", ""),
                        claimed_title=current_entry.get("title", ""),
                    ))
                current_entry = {}
                continue
            for key in ["doi", "title", "year", "author"]:
                if line.lower().startswith(key + " ="):
                    val = line.split("=", 1)[1].strip().strip("{").strip("}").strip(",").strip('"')
                    current_entry[key] = val
        # 最后一条
        if current_entry.get("doi") or current_entry.get("title"):
            results.append(verify_single_ref(
                doi=current_entry.get("doi", ""),
                claimed_title=current_entry.get("title", ""),
            ))
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="引用核验 — 防幻觉")
    parser.add_argument("--doi", help="单个 DOI 核验")
    parser.add_argument("--title", help="声称的标题（配合 --doi）")
    parser.add_argument("--year", type=int, help="声称的年份（配合 --doi）")
    parser.add_argument("--author", help="声称的第一作者姓氏（配合 --doi）")
    parser.add_argument("--refs", help="引用列表 JSON 文件（[{doi, title?, year?, author?}]）")
    parser.add_argument("--bibtex", help="BibTeX 文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    all_results = []

    if args.doi:
        all_results.append(verify_single_ref(
            doi=args.doi,
            claimed_title=args.title or "",
            claimed_year=args.year,
            claimed_first_author=args.author or "",
        ))

    if args.refs:
        with open(args.refs, "r", encoding="utf-8") as f:
            refs = json.load(f)
        for ref in refs:
            all_results.append(verify_single_ref(
                doi=ref.get("doi", ""),
                claimed_title=ref.get("title", ""),
                claimed_year=ref.get("year"),
                claimed_first_author=ref.get("author", ""),
            ))

    if args.bibtex:
        all_results.extend(verify_bibtex(args.bibtex))

    if not all_results:
        print("请提供 --doi、--refs 或 --bibtex", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
    else:
        verified = sum(1 for r in all_results if r["status"] == "VERIFIED")
        mismatched = sum(1 for r in all_results if r["status"] == "METADATA_MISMATCH")
        not_found = sum(1 for r in all_results if r["status"] == "DOI_NOT_FOUND")
        total = len(all_results)

        print(f"\n{'='*60}")
        print(f"引用核验报告: {verified}/{total} 通过, {mismatched} 不匹配, {not_found} 未找到")
        print(f"{'='*60}\n")

        for r in all_results:
            icon = {"VERIFIED": "✓", "METADATA_MISMATCH": "✗", "DOI_NOT_FOUND": "?"}[r["status"]]
            print(f"{icon} [{r['status']}] {r.get('doi', 'N/A')}")
            if r["status"] == "VERIFIED":
                print(f"   → {r.get('actual_title', '')[:80]}")
            else:
                for issue in r.get("issues", []):
                    print(f"   → {issue}")
            print()


if __name__ == "__main__":
    main()
