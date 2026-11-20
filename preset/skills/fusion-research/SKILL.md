---
name: fusion-research
description: 融合研究方法论主体（模式定义层 / 质量门 G1–G11 / 创新三阶引擎 / L0–L4 工作流）的可加载入口。本技能只做「指针 + 索引 + 红线」，正文与 references 的真身位于 Trae 技能目录。当任务需要模式档位映射、质量门判据、创新发散引擎、写作/图表/PPT 规范时加载本技能。
---

# 融合研究（方法论主体 · 指针入口）

> **本文件不含方法论正文**，只是一个可加载的入口。DSH 的技能名必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`，
> 而真身 skill 的 `name: 融合研究` 是中文 → 会被 `dsh-skill-filesystem` 的 `parseSkillFile`
> 静默丢弃（`return`，仅留一条 logger.warn）。因此建立本指针，使启动协议第 1 步的
> 「加载 skill 融合研究」真正可执行。**不要删掉本文件去改 Trae 侧的 `name` 字段**（那是品牌标识，Trae 靠它调用）。

## 真身位置

> 根目录由 `TRAE_SKILLS_DIR` 决定；未设置时默认 `%USERPROFILE%\.trae-cn\skills`。
> 若该目录不存在（没装这套方法论），本指针仍可加载：按本预设 `skills\auto-research\` 的
> `SKILL.md` + `contracts/` 执行即可，只是少了外部方法论正文与中文科研 PPT 模板库。

| 内容 | 路径 |
|------|------|
| 主 SKILL.md（528 行：6 大原则 / 路由表 / 资源索引） | `%USERPROFILE%\.trae-cn\skills\融合研究\SKILL.md` |
| 全部 references（44 份方法论文件） | `%USERPROFILE%\.trae-cn\skills\融合研究\references\` |
| 中文科研 PPT 模板（15 个 .pptx，约 592 MB） | `%USERPROFILE%\.trae-cn\skills\融合研究\templates\` |

## 加载指引（按需读，不要全量读）

| 需要什么 | 读哪个文件 |
|----------|-----------|
| 模式档位 L/A/R/T/M/D 与世界模型、档位→行为映射、D 轴→质量门子集 | `references\mode-definitions.md` |
| 质量门 G1–G11 判据与阈值 | `references\quality-gates.md` |
| idea 发散：4 条突破路径 / 跨域结构映射 / 7 类反事实 / 多角色辩论 | `references\paradigm-breaker.md`、`cross-domain-fusion.md`、`counterfactual-engine.md`、`multi-agent-collider.md` |
| 可落地置信度评分卡（6 维 + 权重 + block/route_back） | `references\grounded-innovation-protocol.md` |
| 反常发现（阈值 + JSON schema + 自动路由） | `references\anomaly-hunter.md` |
| 可重复性协议（实验卡片 + R1–R4 分级） | `references\reproducibility-protocol.md` |
| 认知循环防护（五类检测阈值 + 最大步数表） | `references\cognitive-loop-protocol.md` |
| L0 / L1 / L2 流程 | `references\l0-workflow.md`、`l1-workflow.md`、`l2-workflow.md` |
| L4 发表级 8 个子工作流 A~H | `references\l4-workflows.md` |
| 领域画像骨架（航电 / 光电检测） | `references\avionics-persona.md`、`optoelectronics-detection-persona.md` |

## 红线（读真身之前先知道，避免照搬已作废或冲突的路径）

1. **自评不得作为质量验收依据。** 真身中 `self-scoring.md` 的 8 维自评、`quality-gates.md` G10 的五维自判、
   `grounded-innovation-protocol.md` 的 S(d) 自打分、`multi-agent-collider.md` 的"同批角色既生成又评审"，
   在本预设中**一律只能当生成时的自检提示**。验收走 `contracts/reviewer-independence.md` 的
   **Tier≥T2 独立评审**或确定性脚本（`tools\evidence_check.py` / `stage_gate.py` / `text_gates.py`）。
2. **`objective-evolution-protocol.md` 的「修改评分函数」默认禁用** —— 被评者不得改写判据。
   若要用目标进化，必须先落地「评分函数 hash 冻结 + primary objective 不可变 + 变更需独立批准」。
3. **`ppt-style-library.md` 的 §1 数量声明与 §7 路径表已失效**（论文答辩/人才申报实测为 **0 套**；
   `%USERPROFILE%\Desktop\templates_cache\` 不存在）。只用其场景表 / 字体总表 / 布局模式 / 默认推荐表，
   并配合本预设 `contracts\ppt-workflow.md` 使用。
4. **`supervisor-skills-handbook` 的 AI 禁令条款不适用于本预设**。其原文为「严禁使用大模型或 AI 生成内容」
   与「研究主导权不得交由 AI」。本预设的交付物本身就是 AI 产出，等价契约是：
   **AI 产出须过独立评审 + 证据门 + 人工确认；不可逆动作（是否投稿 / 下单 / 对外承诺）不得由 AI 独立决定。**
5. **已被本预设技能覆盖、不必再读**：`3.2/3.3/3.4` 写作模板（→ `tech-paper-template` /
   `benchmark-paper-template` / `intro-drafter`）、`4.1–4.3` 图表（→ `figure-designer`）、
   `1.1` 论文评价（→ `academic-paper-reviewer`）、`style-calibration`（→ `academic-paper`）。
6. **已知文件缺陷**：`references\figure-reference-library.md` 为 0 字节空文件；
   `supervisor-skills-handbook` 有 17 处 `assets/images/*.png` 死链；
   `find_papers.py` 在本预设副本中已修两处（见 §已迁入）。

## 已迁入本预设的部分（不必回 Trae 读）

| 资产 | 位置 |
|------|------|
| 多源文献检索（openalex/crossref/semanticscholar/arxiv/pubmed） | `tools\find_papers.py` |
| 引用核验（DOI/标题/年份/作者 + 批量 + BibTeX） | `tools\verify_citations.py` |
| 图表顾问（CSV 剖析→图型推荐→风格→QA） | `tools\generate_figure.py` |
| 发表级 matplotlib 样式 | `tools\styles\{nature,science,publication}.mplstyle` |
| PPT 场景→风格→字体→布局 四步流程 | `contracts\ppt-workflow.md` |
| D 轴产出出口→质量门子集映射 | `contracts\acceptance-gate.md` §6 |
| 实验卡片门 | `templates\experiment_card.template.json` + `gates\experiment_card.gate.json` |

详见本预设 `skills\auto-research\SKILL.md` §13。
