# 引用纪律（Citation Discipline）

> 来源：吸收 ARIS `shared-references/citation-discipline.md`（含 Pre-Search Verification Protocol）与
> `tools/verify_papers.py` 的反幻觉思想，适配 DSH 的 paper-lookup / literature-search 等本地 skill。

## 0. 目标

杜绝幻觉引用与「真论文被引在不支持的语境」两类问题。声明必须可溯源，引用必须被核验。

## 1. 硬规则

1. **主张必带出处**：论文/综述/晨报中的每个实质声明（数字、结论、对比）必须有引用；无出处声明在交付前必须补上或降级为"个人判断/假设"并标注。
2. **搜索时核验，写作时引用**：检索阶段（SEARCH）收集候选文献后，先做**快速核验**（存在性），再进入写作（WRITE）引用。
3. **引用三轴核验**（投稿级/发表级 D5 时强制）：
   - 存在性：论文是否真实存在（arXiv ID / DOI / 会议记录）；
   - 元数据：作者/年份/会议/标题与权威源一致；
   - 语境恰当性：被引论文是否真的支持引用处的 claim（最有诊断价值的一轴）。
4. **网络瞬时失败不计入幻觉**：核验时网络 5xx/超时/429 → 标 `verify_pending`，保留 `[UNVERIFIED]` 标记让问题可见，不静默删除。
5. **LLM 生成 BibTeX 禁止**：能取真实 BibTeX（DBLP/CrossRef）就用真实的；无法核验的条目在交付物中打 `[UNVERIFIED]`。
6. **审计门**：D5（发表级）交付前执行引用审计（存在性+元数据+语境），输出 KEEP / FIX / REPLACE / REMOVE 判定；无法通过的条目不得进入最终交付。

## 2. 落地（DSH 工具映射）

| 环节 | 用哪个工具/skill |
|:--|:--|
| 检索 | paper-lookup / literature-search / deep-research（多库） |
| 存在性核验 | paper-lookup（PubMed/PMC/bioRxiv/medRxiv/arXiv/OpenAlex/Crossref/S2/CORE/Unpaywall） |
| BibTeX | citation-management（DBLP/CrossRef 优先） |
| 语境审计（D5） | citation-audit / paper-claim-audit（本地 skill 路由）或 T2+ 独立评审 |
| 记录 | 核验结果写入 notes/litreview.md + evidence 清单 |

## 3. 借鉴记录

改编自 ARIS（MIT）：`shared-references/citation-discipline.md`（Pre-Search Verification Protocol）、
`tools/verify_papers.py`（3 层 fallback 核验 + 4 态 + verify_pending 不计幻觉率）、`/citation-audit`（三轴审计 KEEP/FIX/REPLACE/REMOVE）。
