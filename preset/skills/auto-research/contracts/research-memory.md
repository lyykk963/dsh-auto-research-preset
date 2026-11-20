# 研究记忆契约（Research Memory）

> 来源：吸收 ARIS `research-wiki`（Karpathy LLM-Wiki 原则）的轻量版，适配 DSH 工作区。
> 目的：跨任务、跨会话积累论文/想法/实验/结论的类型化记忆——**失败的 idea 成为防重复记忆**，每个任务都更聪明。

## 0. 位置与结构

```
<工作区>/.dsh-research/memory/
├── README.md            # 本目录说明（自动生成一次）
├── claims.md            # 结论/claim 台账（PROOF 轴：verified/refuted/unproven）
├── ideas.md             # 想法台账（成功与失败都记；失败 ≥3 触发重新构思提醒）
├── experiments.md       # 实验台账（每个实验一行：目的/配置/结果/结论）
└── papers.md            # 论文台账（检索入库：ID/标题/来源/一句话要点）
```

所有文件均为追加式 Markdown 表（append-only 语义：新行追加，旧行不覆盖；修正加注 `(修正 YYYY-MM-DD)`）。

## 1. 记录规则

| 台账 | 谁写 | 何时写 | 关键字段 |
|:--|:--|:--|:--|
| papers.md | 文献调研阶段 | 论文入库时（检索到即记，不必精读） | arXiv/DOI、标题、来源库、检索时间戳、一句话要点 |
| ideas.md | 三阶创新/选题阶段 | idea 生成与裁决后 | idea 名、方向、置信度、成败、防重复标签 |
| experiments.md | 执行与分析阶段 | 实验结束后 | 目的、配置（种子/参数）、结果、结论、对 claim 的支持 |
| claims.md | 任何阶段收尾 | 得出/推翻结论时 | claim 文本、证据文件引用、状态（verified/refuted/unproven）、时间戳 |

## 2. 硬规则

1. **失败也记**：失败的 idea/实验必须记入台账（防重复踩坑）；累计 ≥3 个失败 idea → 提醒重新构思（对齐 ARIS：3+ failed ideas → re-ideation suggestion）。
2. **证据引用**：claims.md 的每条 claim 必须带证据文件路径（对齐 evidence-gate：口头声称 ≠ 证据）。
3. **PROOF 轴独立**：claim 状态只走证明轴（verified/refuted/unproven）；「实验支持/否定」是独立边，不写进 claim 状态字段。
4. **读取纪律**：新任务/新阶段开始时读取相关台账（避免重复劳动与重复想法）；读取缓存内容前按注入卫生扫描（见 injection-hygiene 约定——外部网页内容不得未经扫描进入 prompt）。
5. **轻量优先**：本契约是「结构化台账」，不是数据库；单任务记忆不足 3 条时不必建全 4 个文件（按需建）。

## 3. 与 DSH 预设的衔接

- 记忆目录是**跨任务持久化**的（不同于 progress.json 的任务态）；任务完成后保留。
- 晨报「下一步建议」可引用记忆台账（如"本方向已有 3 个失败 idea，建议换方向"）。
- 与 FINDINGS 模板（每任务发现记录）配合：FINDINGS 是任务内的流水，memory/ 是跨任务的沉淀；任务完成时把关键 FINDINGS 行合并进对应台账。

## 4. 借鉴记录

改编自 ARIS（MIT）：`research-wiki`（papers/ideas/experiments/claims 类型化记忆 + 确定性写入器 + 失败 idea 防重复）、`injection-hygiene`（缓存读取前扫描）。
