# 技能权威归属：谁负责哪一层（v9.7）

> 起因（2026-10-21 审计）：本机 425 个流程型技能，**实际只用了 33 个（≈7%）**；
> 而且执行层（检索/写作/评审/结果分析）我们**重复实现了一遍**，质量还不如既有技能。
> 复现：`.lab/workspace/skill_audit.py`；审计报告 `.dsh-research/SKILL-UTILIZATION.md`。

## 1. 分工原则：**门自建，活外包**

| 层 | 归属 | 判据 |
|---|---|---|
| **编排与门控** | **本预设** | 阶段推进、证据门、claims 重算、prereg 冻结、DRIVE/ACQUIT 区分——**既有技能没有这些可机检的门** |
| **领域执行** | **既有技能** | 检索/写作/统计/生信/化学等具体活，既有技能更专、我们不可能重写更好 |
| **模板与设计资产** | 本预设（ppt-studio / slide-design） | 中文科研场景与反 AI 感红线是我们独有的 |

## 2. 执行层权威表（**优先调用既有技能，不要自己现写**）

| 任务 | 用哪个技能 | 不要做什么 |
|---|---|---|
| 文献检索 / 全文 / DOI | `paper-lookup`（11 个 API，含 Unpaywall/PMC） | 不要另写检索脚本 |
| 领域地图 / 综述 | `deep-research`、`literature-search` | 不要手搓检索词轮次 |
| 论文写作 / 改稿 | `academic-paper`、`paper-spine`、`scientific-writing` | 不要从零写章节模板 |
| 结果统计与解读 | `results-analysis`、`data-analysis` | 不要自己发明检验 |
| 独立评审 | `academic-paper-reviewer`（5 评审人格）、`peer-review` | **不得自己给自己打分** |
| **改稿 / 导师批注 / 逐条回复** | **`paper-revision-playbook`**（7 步法 + 批注类型学 + 48 KB 原始批注）+ 本预设 `advisor_pattern_gate.py`（机检） | 不要把"删一句形容词"当成完成；先分清「他说的」与「他想要的」 |
| 出图 | `scientific-visualization`、`scipilot-figure-skill` | 不要手调 matplotlib 默认样式 |
| PPT | `ppt-studio`（本预设）+ `scientific-slides` | 不要无图满页 bullet |
| 引用核验 | `citation-verification`、`verify_citations.py` | 不要凭记忆写参考文献 |

## 3. 三条硬规则

1. **能委派就不现写**：上表里的任务，先加载对应技能；确实不合适才自建，并在交付里说明原因。
2. **交付要对账**：收尾跑 `python tools/skill_routing.py check <交付目录>`——
   报告"该用但没用"的技能清单；`--strict` 时缺一个即 exit 1。
3. **不许空转**：每个任务在 `.dsh-research/skill-usage.jsonl` 至少留 1 条记录
   （`check_delivery.py` 已设为硬门，缺则交付 FAIL）。

## 4. 为什么这条值得写进契约

2026-10-21 审计发现「每阶段必须追加 skill-usage.jsonl」这条规则写了几个月，
实际全库只有 **79 行**——**规则存在 ≠ 规则生效**。三项配套（契约 + 路由对账 + 交付硬门）
就是把这句话从口号变成可执行检查。
