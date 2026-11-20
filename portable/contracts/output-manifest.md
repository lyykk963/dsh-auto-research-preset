# 产物清单与版本化（Output Manifest & Versioning）

> 来源：吸收 ARIS `shared-references/output-manifest.md` / `output-versioning.md` / `output-composition.md` 的约定，
> 与 DSH 工作区产物约定（README.md「工作区产物约定」）对接。

## 0. 为什么需要

跨轮次、跨重启、跨交付的科研任务，产物必须**可发现、可追溯、不互相覆盖**。
没有清单，晨报里的"产物索引"就不可信；没有版本化，重跑一轮就悄悄覆盖上一轮证据。

## 1. MANIFEST.md（产物总账）

位置：`<工作区>/.dsh-research/evidence/MANIFEST.md`（阶段证据）与 `<工作区>/MANIFEST.md`（交付物总账，可二选一或合并）。

**阈值规则（对齐 ARIS）**：**仅在产物数量超过 15 个工件时**维护 `MANIFEST.md`；少量产物不建清单（避免为记而记）。典型科研任务（含各阶段笔记/证据/评审/图表）通常超过阈值，建账收益大于成本。

格式（Markdown 表）：
```markdown
| 产物 | 说明 | 创建阶段 | 版本/时间戳 | 证据角色 |
|------|------|---------|------------|---------|
| PLAN.md | 计划与排期 | plan | 2026-08-25T20:35 | 计划证据 |
| notes/litreview.md | 文献笔记 | litreview | … | 调研证据 |
| results/exp1/metrics.json | 实验1指标 | execute | … | 数据证据 |
| .dsh-research/traces/task/round1/review.md | 评审留痕 | method | … | 质量证据 |
```

规则：
- 每次新增/替换主要产物时更新 MANIFEST（一行）。
- 覆盖旧版本前，旧文件保留副本或写版本后缀（见 §2）。
- 晨报「产物索引」直接引用 MANIFEST，不再口头罗列。

## 2. 版本化（防覆盖）

- 高价值中间产物（评审记录、实验结果、审计输出）写入时**先写时间戳文件名，再复制到固定名**：
  `results/exp1/metrics-20260825T2300.json` → 复制为 `results/exp1/metrics.json`（固定名供下游消费）。
- 轮次产物带轮次号：`notes/review-round2.md`、`evidence/execute/r2-manifest.json`。
- 被覆盖的固定名文件在 MANIFEST 中保留历史行（指向时间戳版本）。

## 3. 组合模式（Composed Output）

- 当某阶段产物是"编排器级"报告的一部分时（如 litreview 结论并入 method 设计、评审结论并入晨报）：
  在 MANIFEST 中记录"来源文件 → 并入目标"的关系，并保留来源文件的 trace 链接；
  不得只留合并结果而删除来源（来源是证据）。
- 中间产物只做**结构转换**（如 md → html）时，源文件仍是 canonical，转换产物标注"derived"。

## 4. 借鉴记录

改编自 ARIS（MIT）：`shared-references/output-manifest.md`（MANIFEST.md 记录每个输出）、
`output-versioning.md`（先时间戳后固定名）、`output-composition.md`（composed 模式：结论并入 canonical 报告并引用 trace）。
