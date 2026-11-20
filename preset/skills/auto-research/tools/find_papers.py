#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# 迁入来源（provenance）— 本文件为冻结副本；上游演进不自动同步，同步需重跑核验
#   上游：D:\code\models\Tools\融合研究\融合研究-共享版\scripts\find_papers.py
#   上游 sha256（迁入时）：9f7c8bdd95e9fd46a4c03231febc9e67de1c012e6be641fecc329f76a32e78b2
#   迁入日期：2026-09-12 ｜ 迁入依据：融合研究-v8.1-可复用性评估.md（v9.1）
#   本副本改动：
#     1) 修复 arXiv 分支双重编码（quote() + urlencode() 叠加）——潜在缺陷，静态可证
#     2) 【主要】修复「静默失败」：原先 _http_get 失败返回 None → 各源 return [] →
#        「来源不可达」与「确实 0 条」不可区分且 exit 0。现改为抛 SourceUnreachable，
#        逐源记 source_status、打印显式告警，并以 exit 2 表示结果不完整。
#        对「防幻觉」工具而言，把"没能问出去"读成"没有相关工作"是最危险的失效模式。
# ---------------------------------------------------------------------------
"""多源文献检索工具 — 防幻觉核心。

从多个独立学术 API 并行检索论文，
输出交叉验证后的可信结果。

来源:
  - OpenAlex (多学科, 2.5亿+)
  - Crossref (DOI权威)
  - Semantic Scholar (引文影响)
  - arXiv (CS/物理/数学预印本)
  - PubMed/Europe PMC (生物医学)

用法:
  python find_papers.py --query "transformer vision" --sources openalex,crossref,arxiv --max-results 10
  python find_papers.py --query "CRISPR gene editing" --sources pubmed --max-results 20 --json
"""

import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Optional

# ── 配置 ──────────────────────────────────────────────────────────
USER_AGENT = "IntegratedResearch/1.0 (mailto:research@example.com)"
TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAY = [0.5, 1.0, 2.0]


class SourceUnreachable(Exception):
    """来源不可达（网络/超时/HTTP 错误）。

    与「检索成功但 0 条结果」严格区分：前者是"没能问出去"，后者是"问了，没有"。
    v9 修复：原实现把两者都折叠成 `[]`，导致对一个「防幻觉」工具而言最危险的失效模式——
    agent 会把"来源不可达"读成"不存在相关工作"。
    """


# ── 工具函数 ──────────────────────────────────────────────────────

def _http_get(url: str, headers: Optional[dict] = None) -> Optional[str]:
    """带指数退避的 HTTP GET。

    成功 → 返回响应体（可能为空串，交由调用方判断）；
    **失败 → 抛 SourceUnreachable**（不再静默返回 None）。
    """
    if headers is None:
        headers = {"User-Agent": USER_AGENT}
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY[attempt])
    raise SourceUnreachable(f"{type(last).__name__}: {last}")


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ── 各源检索函数 ──────────────────────────────────────────────────

def search_openalex(query: str, max_results: int = 10) -> list:
    """OpenAlex 检索（多学科，被引排序）。"""
    params = {
        "search": query,
        "per_page": min(max_results, 200),
        "sort": "relevance_score:desc",
        "mailto": "research@example.com",
    }
    url = f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}"
    data = _http_get(url)
    if not data:
        return []
    try:
        resp = json.loads(data)
    except json.JSONDecodeError:
        return []
    results = []
    for work in resp.get("results", [])[:max_results]:
        results.append({
            "title": work.get("title", ""),
            "doi": work.get("doi", ""),
            "year": work.get("publication_year"),
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in work.get("authorships", [])[:5]],
            "journal": (work.get("primary_location", {}) or {})
                       .get("source", {}).get("display_name", ""),
            "cited_by": work.get("cited_by_count", 0),
            "abstract": (work.get("abstract_inverted_index") and "可用" or ""),
            "source": "OpenAlex",
            "url": work.get("id", ""),
        })
    return results


def search_crossref(query: str, max_results: int = 10) -> list:
    """Crossref 检索（DOI 权威来源）。"""
    params = {
        "query": query,
        "rows": min(max_results, 100),
        "sort": "relevance",
    }
    url = f"https://api.crossref.org/works?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}
    data = _http_get(url, headers)
    if not data:
        return []
    try:
        resp = json.loads(data)
    except json.JSONDecodeError:
        return []
    results = []
    for item in resp.get("message", {}).get("items", [])[:max_results]:
        results.append({
            "title": item.get("title", [""])[0] if item.get("title") else "",
            "doi": f"https://doi.org/{item.get('DOI', '')}",
            "year": (item.get("published-print") or item.get("published-online") or {})
                    .get("date-parts", [[None]])[0][0],
            "authors": [a.get("family", "") for a in item.get("author", [])[:5]],
            "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
            "cited_by": item.get("is-referenced-by-count", 0),
            "source": "Crossref",
            "url": f"https://doi.org/{item.get('DOI', '')}",
        })
    return results


def search_semantic_scholar(query: str, max_results: int = 10) -> list:
    """Semantic Scholar 检索（引文影响、TLDR）。"""
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "title,year,authors,journal,citationCount,externalIds,abstract,url",
    }
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{urllib.parse.urlencode(params)}"
    data = _http_get(url)
    if not data:
        return []
    try:
        resp = json.loads(data)
    except json.JSONDecodeError:
        return []
    results = []
    for paper in resp.get("data", [])[:max_results]:
        doi = paper.get("externalIds", {}).get("DOI", "")
        results.append({
            "title": paper.get("title", ""),
            "doi": f"https://doi.org/{doi}" if doi else "",
            "year": paper.get("year"),
            "authors": [a.get("name", "") for a in paper.get("authors", [])[:5]],
            "journal": (paper.get("journal") or {}).get("name", ""),
            "cited_by": paper.get("citationCount", 0),
            "abstract": paper.get("abstract", ""),
            "source": "SemanticScholar",
            "url": paper.get("url", ""),
        })
    return results


def search_arxiv(query: str, max_results: int = 10) -> list:
    """arXiv 检索（CS/物理/数学预印本）。"""
    params = {
        "search_query": f"all:{query}",  # FIX: 原为 quote(query)，与下方 urlencode() 双重编码（潜在缺陷，已修）
        "max_results": min(max_results, 100),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    data = _http_get(url)
    if not data:
        return []
    results = []
    try:
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        for entry in root.findall("atom:entry", ns)[:max_results]:
            title = entry.find("atom:title", ns)
            title = title.text.strip().replace("\n", " ") if title is not None else ""
            published = entry.find("atom:published", ns)
            year = published.text[:4] if published is not None else None
            authors = [a.find("atom:name", ns).text or ""
                       for a in entry.findall("atom:author", ns)[:5]]
            links = {l.get("title", ""): l.get("href", "")
                     for l in entry.findall("atom:link", ns)}
            doi_link = links.get("doi", "")
            results.append({
                "title": title,
                "doi": doi_link if doi_link.startswith("https://doi.org/") else "",
                "year": int(year) if year and year.isdigit() else None,
                "authors": authors,
                "journal": "arXiv",
                "cited_by": 0,
                "abstract": "",
                "source": "arXiv",
                "url": links.get("", ""),
            })
    except ET.ParseError:
        pass
    return results


def search_pubmed(query: str, max_results: int = 10) -> list:
    """PubMed 检索（生物医学）。"""
    # 1. ESearch — 获取 ID 列表
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, 100),
        "retmode": "json",
    }
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{urllib.parse.urlencode(search_params)}"
    data = _http_get(search_url)
    if not data:
        return []
    try:
        search_resp = json.loads(data)
    except json.JSONDecodeError:
        return []
    ids = search_resp.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # 2. ESummary — 取详细信息
    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids[:max_results]),
        "retmode": "json",
    }
    summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{urllib.parse.urlencode(summary_params)}"
    data = _http_get(summary_url)
    if not data:
        return []
    try:
        summary_resp = json.loads(data)
    except json.JSONDecodeError:
        return []
    results = []
    result_map = summary_resp.get("result", {})
    for uid in ids[:max_results]:
        info = result_map.get(uid, {})
        if not info:
            continue
        results.append({
            "title": info.get("title", ""),
            "doi": "",
            "year": info.get("pubdate", "")[:4] if info.get("pubdate") else None,
            "authors": [a.get("name", "") for a in info.get("authors", [])[:5]],
            "journal": info.get("source", ""),
            "cited_by": 0,
            "abstract": "",
            "source": "PubMed",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
        })
    return results


# ── 去重与合并 ──────────────────────────────────────────────────

def deduplicate(results: list) -> list:
    """按 DOI 去重，无 DOI 按标题相似度去重。"""
    seen_dois = set()
    seen_titles = set()
    unique = []
    for r in results:
        doi = (r.get("doi") or "").strip()
        title = (r.get("title") or "").strip().lower()
        if doi and doi in seen_dois:
            continue
        if not doi and title and title in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        if title:
            seen_titles.add(title)
        unique.append(r)
    return unique


# ── 主入口 ──────────────────────────────────────────────────────

SOURCE_MAP = {
    "openalex": search_openalex,
    "crossref": search_crossref,
    "semanticscholar": search_semantic_scholar,
    "arxiv": search_arxiv,
    "pubmed": search_pubmed,
}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="多源文献检索 — 防幻觉")
    parser.add_argument("--query", "-q", required=True, help="搜索关键词")
    parser.add_argument("--sources", default="openalex,crossref,arxiv",
                        help="来源，逗号分隔: openalex,crossref,semanticscholar,arxiv,pubmed")
    parser.add_argument("--max-results", type=int, default=10, help="每源最大结果数")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",")]
    all_results = []
    source_stats = {}
    source_status = {}
    failed = []

    for src in sources:
        func = SOURCE_MAP.get(src)
        if not func:
            print(f"[WARN] 未知来源: {src}", file=sys.stderr)
            source_status[src] = "unknown_source"
            failed.append(src)
            source_stats[src] = 0
            continue
        try:
            results = func(args.query, args.max_results)
            source_stats[src] = len(results)
            source_status[src] = "ok"
            all_results.extend(results)
        except SourceUnreachable as e:
            source_stats[src] = None
            source_status[src] = "unreachable"
            failed.append(src)
            print(f"[WARN] 来源 {src} 不可达：{e}", file=sys.stderr)
            print(f"[WARN]   → 结果不完整。不得据此断言「无相关工作」"
                  f"（这是「没能问出去」，不是「问了没有」）。", file=sys.stderr)
        except Exception as e:
            source_stats[src] = None
            source_status[src] = "error"
            failed.append(src)
            print(f"[WARN] 来源 {src} 检索失败：{type(e).__name__}: {e}", file=sys.stderr)

    # 去重
    unique_results = deduplicate(all_results)

    if failed:
        print(f"[WARN] {len(failed)}/{len(sources)} 个来源未成功：{', '.join(failed)}；"
              f"本次结果不可作为「该方向无相关工作」的证据。", file=sys.stderr)

    if args.json:
        output = {
            "query": args.query,
            "sources_used": sources,
            "source_stats": source_stats,
            "source_status": source_status,
            "failed_sources": failed,
            "complete": len(failed) == 0,
            "total_raw": len(all_results),
            "total_unique": len(unique_results),
            "results": unique_results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"检索: {args.query}")
        print(f"来源: {', '.join(sources)} | 原始 {len(all_results)} 条 → 去重 {len(unique_results)} 条")
        if failed:
            print(f"⚠️  未成功来源: {', '.join(failed)} —— 结果不完整，不可据此断言「无相关工作」")
        print(f"{'='*60}\n")
        for i, r in enumerate(unique_results, 1):
            print(f"[{i}] {r['title']}")
            if r.get("authors"):
                print(f"   作者: {', '.join(r['authors'][:3])}")
            print(f"   来源: {r['source']} | 年份: {r.get('year', 'N/A')} | 被引: {r.get('cited_by', 0)}")
            if r.get("doi"):
                print(f"   DOI: {r['doi']}")
            if r.get("journal"):
                print(f"   期刊: {r['journal']}")
            print()

    # 输出来源统计到 stderr
    print(f"\n[STATS] 来源统计: {json.dumps(source_stats, ensure_ascii=False)}", file=sys.stderr)
    print(f"[STATS] 来源状态: {json.dumps(source_status, ensure_ascii=False)}", file=sys.stderr)

    # exit 码约定（v9 修复）：
    #   0 = 全部来源成功（即使 0 条结果，那是"问了，没有"）
    #   2 = 有来源未成功（"没能问出去"，结果不完整）
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
