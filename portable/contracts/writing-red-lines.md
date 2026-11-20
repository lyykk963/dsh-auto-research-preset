# 写作红线契约（Writing Red Lines）— 让「审稿人点过的问题」不再重犯

> 版本：v1.1（公开版）
> 来源：把一篇真实论文的多轮导师/审稿意见沉淀成可执行规则的做法（原稿数据已脱敏移除）。
> 定位：本契约把「被导师/审稿人反复提出的问题」变成**可事先执行**的动作，而不是事后再改。
> 与 `acceptance-gate.md` 的关系：本契约提供**具体规则内容**；判 PASS/FAIL 的权限仍归 acceptance-gate
> （Type-A 走确定性脚本，Type-B 走 Tier≥T2 独立评审）。

---


## 0. 资产分层（先看这张表，别拿蒸馏版当全部）

| 层 | 在哪 | 内容 | 什么时候读 |
|---|---|---|---|
| **可执行门**（现役） | 本文件 §1–§4 + `tools/advisor_pattern_gate.py` + `gates/paper_redline_profile.template.json`（可选，论文专属规则）| 通用反模式 + 论文专属规则蒸馏成的**机检规则**（`--strict` 可断稿） | 每次送导师/投稿前 |
| **原始档案**（未接入） | `~/.agents/skills/paper-revision-playbook/references/` | `07-raw-r3-r7.md`(20.8 KB)、`08-raw-r8-r12.md`(27.7 KB) = **48 KB 逐轮原始批注** | 遇到"这条意见到底什么意思"时回查原话 |
| **方法论**（未接入） | 同上 `SKILL.md` + `02-annotation-taxonomy.md` + `03-revision-rules.md` | 批注类型学、7 步改稿流程、"他说的 vs 他想要的" | **任何改稿类任务开工前** |
| **回归清单** | 同上 `05-regression-checklist.md` | 改完防同类错误复发 | 交付前三件套之一 |

**硬规则**：改稿 / 逐条回复审稿意见类任务，**必须先加载 `paper-revision-playbook`**，
再用本契约的机检门跑一遍。蒸馏版查"有没有犯已知的错"，原始档案查"这条意见的真实意图"。
两者缺一，就会重演"只删一句话、下一轮再被说"的循环。

## 0. 一句话

**导师指出的每一条意见，要么变成一条能自动跑的检查，要么变成一条能勾选的人工检查——不允许只变成"下次注意"。**

---

## 1. 三层机制（缺一层就退化成口头承诺）

| 层 | 时机 | 手段 | 谁执行 |
|---|------|------|--------|
| **L1 生成时自检** | 起草每个 section 时 | 本契约 §3 的通用红线 + 本项目 profile 的禁用词/口径 | 写作者本人（AI 或人） |
| **L2 投稿前机检** | 送导师/投稿**之前** | `python tools/advisor_pattern_gate.py <稿...> --profile <本项目 profile>` | 脚本（确定性，Type-A） |
| **L3 独立评审** | 机检通过后 | Tier≥T2 冷读全文（`reviewer-independence.md`） | 独立评审代理 |

**铁律**：L2 通过 ≠ 可以投稿。L2 只判「是否触发已知反模式」（能 DRIVE）；
「论文够不够好」是 Type-B，必须走 L3（能 ACQUIT 的只有独立评审）。
**不得用自评分替代 L3**（见 `acceptance-gate.md` §6.5）。

---

## 2. 什么时候必须跑

| 触发点 | 动作 |
|--------|------|
| 任何一个 section 定稿 | L1 自检（§3 + profile） |
| 全稿首次合并完成 | **L2 全量机检**（正文 + 补充材料 + Highlights 一起跑） |
| 每次按意见修改后 | **L2 增量机检**（改动过的文件 + 被改口径的全部文件） |
| 送导师 / 投稿前 | L2 `--strict` + L3 独立评审，两者都留痕 |
| 导师提了新意见 | **维护规则**：新意见 → 新规则（§5），`source_round` 留档 |

---

## 3. 通用红线（任何论文都适用，已内置进脚本）

> 以下每条都是**跨论文通用的**，来自真实稿件多轮意见中「与领域无关」的那部分。

### 3.1 措辞与立场
1. **不得过度宣称**：`on par` / `significantly improves` / `state-of-the-art` / `first` / `novel` 等强断言，
   同段必须有对应证据（显著性检验或等价性检验）。**非显著 ≠ 等效**——要主张"相当/等效"必须做等价性检验。
2. **术语与方法必须匹配**：双侧 TOST 检验的是 **equivalence**，不是 non-inferiority；
   非劣效是**单侧**设计。二者不得混用（机检：`advisor_pattern_gate` T-TOST-NONINF-CONFLICT）。
3. **不得用「特征变好」证明「任务变好」**：特征级指标（CKA/相似度）与任务级指标（mAP）只能弱关联表述，
   不得写成方法优越性的证据。
4. **复合差异不得归因到单一机制**：两个方法在整体行为上有差异，不等于其中某个子机制更优（混淆变量）。
5. **不得给基线贴道德化标签**（`fair` 之类）；基线若不是官方实现，必须写明是机制移植 / re-implementation。
6. **不得用「隐私友好」等不可证的市场化措辞**：改成「在隐私、存储或部署约束下更适用」。
7. **单次运行/单个 seed 不得作为结论**；每个结论都要说明 seed 数与统计口径。
8. **超范围限定词**：`gradient-free` / `teacher-free` / `zero-old-data` 这类卖点词，
   必须写清**限定在流程的哪一步**，不得泛指整个方法。

### 3.2 数字与口径守恒（最容易反复出问题的一类）
9. **同一个量只能有一个口径**：层数、通道数、seed 数、协议数、样本数——
   每个量在全文（正文+补充材料）必须唯一；出现 `21 of 33` 这种子集时必须**解释 33 是什么**。
10. **种数不得泛指**：不同方法用了不同 seed 数时，不得用 `five seeds` 泛指全部方法。
11. **表与图必须同源**：同一实验在表里和图里必须是同一批数字；不得出现同一指标在表与图中数值不一致这类冲突。
12. **不得留旧数值**：口径修正后，旧统计量（如修正前的 p 值）不得残留在任何位置。
13. **数字守恒**：正文删除的任何数值必须在补充材料里查得到；不得凭空新增数值。
14. **图与表不得重复**：主结果若已有表，不要再用图重复同一批数据。

### 3.3 叙事口径一致性
15. **核心结论句在 Abstract / Introduction 贡献 / Discussion / Conclusion 四处必须同一口径**。
    （常见教训：核心故事中途改判，Abstract/Intro/Discussion/Conclusion 四处要改多轮才一致。）
16. **禁用已被推翻的旧故事短语**：核心机制一旦改判，旧表述必须**全文清除**并进 profile 的
    `narrative.forbidden_phrases`，由脚本守门。
17. **共享类 ≠ 缺失类**：某类别在两个域的标签空间里都存在时，不得用它论证"缺类监督导致遗忘"
    （自相矛盾）。机检难以覆盖这类逻辑矛盾，属 **L3 人工/评审**项。
18. **结论三段式**：重述贡献 → 关键证据 → 带边界的意义；不得引入新的过度宣称。
19. **Results 只写"观察到什么"，Discussion 才写"怎么理解、何时不成立"**，不得混写。

### 3.4 结构与篇幅
20. **单节不得过长**；**caption/表注不得过长**（经验阈值：caption > 400 字符就该压缩）。
21. **句长 ≤ 30 词**；超过 20 词即检查是否含多个主命题，过载句必须拆。
22. **一段一个中心意思**；新意思另起段。
23. **不用句首填充语**（`Notably` / `Importantly` / `In other words` / `Overall` / `Additionally` …），
    句首不得连续同构。
24. **拼写统一**（美式或英式，全文一致）。
25. **不得残留占位符**：`TODO` / `TBD` / `待补` / `Author Name A` 之类在投稿版中必须为零。
26. **em dash 慎用/禁用**：若导师或期刊有要求，则全文（含补充材料）零 em dash，
    数字区间用 `--`。这是纯机械可检项。

### 3.5 图表自明性
27. **每个图表必须被正文引用**（不得有孤儿 label）；不得有未定义引用。
28. **图注要素齐全**：协议名、指标、seed 数/误差棒含义、panel 编号，读者不看正文也能读懂。

### 3.6 合规与伦理（投稿阶段）
29. **Highlights**：3–5 条，每条 ≤ 85 字符（按目标期刊官方要求），单独文件。
30. **摘要**：≤ 目标期刊上限（PR 实践 250 词），**0 引用**。
31. **CRediT**：真实姓名 + 角色与实际承担一致（不得第一作者独揽全部角色）；
    有资助则必须有 `Funding acquisition`。
32. **生成式 AI 使用声明**：按期刊政策单独声明；AI 不得列为作者。
33. **Data availability statement** 必须存在且与实际一致。
34. **摘要/正文中的 URL 与仓库承诺必须真实可达**（审稿人会点开）。
35. **中英双版本必须逐项同步**，且同步后要**逐条验证命中**（不是"我改了"就算）。
36. **页数/格式符合目标期刊区间**；补充材料独立上传、不计入正文页数。
37. **不要问审稿进度**（PR：投稿后 3 个月内不询问）。

---

## 4. 项目 profile（把"本项目特有"的部分外置）

通用红线内置在脚本里；**本项目特有**的禁用词、口径规范值、旧故事短语放在 profile JSON：

```
gates/paper_redline_profile.template.json   # 模板：复制成自己的 profile 后 --profile 传入
```

profile 结构：

| 键 | 作用 |
|----|------|
| `banned_terms[]` | 禁用词/措辞红线；支持 `when_any` 条件触发（如"只在语料含 TOST 时才禁 non-inferior"） |
| `numeric_invariants[]` | 数值口径守恒：`forbidden_pattern` + `require_context` + `exempt_if` |
| `narrative.forbidden_phrases[]` | 被推翻的旧故事短语 |
| `narrative.canonical_claims[]` | 必须在语料中出现的统一口径 |
| `style` | 句长/caption/小节长度阈值、填充语表、拼写表 |
| `compliance` | Highlights 条数与字符数、摘要词数 |
| `residue.patterns[]` | 残留物正则 |
| `ignore_line_contains` | 免检行（防止把描述规则的文档本身扫出误报） |

**每新增一条导师意见：向其所属 profile 追加一条规则，并填 `source_round`**（可追溯到第几轮）。

---

## 5. 规则维护流程（每次导师提意见后必做）

1. 把该轮意见结构化（`rounds-<n>.jsonl`，字段见 §6），**逐字保留导师原文**；
2. 判断该条能否机检：
   - 能 → 转成 profile 规则或脚本规则，填 `machine_rule_hint`；
   - 不能 → 进 §3 的人工清单（并说明为什么不能机检）；
3. **跑一次回归**：新规则在「本轮修改前的那一版稿」上必须命中（证明规则确实对应这条意见），
   在「修改后的稿」上不得命中（证明修好了）——这就是本契约要求的 **正/负控制**；
4. 更新 `source_round` 与复发记录；
5. 若某条意见**跨 2 轮以上复发**，在报告中单列（说明规则没生效或生成流程有洞）。

---

## 6. 意见结构化数据格式（`rounds-<n>.jsonl`）

每行一个 JSON：

```json
{"round":"R3","source_file":"<导师意见原件绝对路径>","item_id":"R3-01a",
 "lang":"zh|en|zh-paraphrase","verbatim":"导师原话逐字（不得改写）",
 "advisor_ask":"一句话要求","category":"<12 类之一>","root_cause":"我方为何会被提",
 "applied_fix":"当时怎么改的（查不到写 null）","preemptable":true,
 "machine_checkable":true,"machine_rule_hint":"可机检规则或 null","note":"证据强度说明"}
```

12 类 category：`claim_overreach` `terminology_precision` `statistical_rigor`
`methodological_consistency` `number_consistency` `narrative_coherence`
`figure_table_quality` `writing_style` `structure_length` `compliance_format`
`ethics_authorship` `reproducibility`

**诚实性要求**：
- `verbatim` 必须是**程序化抽取**的原文（严禁手抄改写）；能写反编造校验就写（断言 verbatim 是源文件子串）。
- 只有我方转述、查不到导师原话的，必须用 `lang: "zh-paraphrase"` 并说明——**不得把转述伪装成原话**。
- 查不到的字段写 `null`，**不得填空**。

---

## 7. 与既有工具的分工（不要重复实现）

| 工具 | 管什么 |
|------|--------|
| `tools/advisor_pattern_gate.py` | **本契约**：导师点过的模式（措辞红线/口径守恒/叙事口径/图表结构/合规包装/残留物） |
| `tools/text_gates.py` | G1/G3 通用写作质量（AI 高频词、标点多样性、段落节奏、句长 CV、过度声明词、引用时效） |
| `tools/evidence_check.py` | G11 证据门（主张是否有落盘证据） |
| `tools/verify_citations.py` | 引用核验（DOI/标题/年份/作者） |
| `tools/stage_gate.py` | 阶段产物清单门 |
| `tools/find_papers.py` | 多源文献检索（防幻觉） |

---

## 8. 反模式（本契约自己不得犯的错）

1. **不要把通用规则写成项目规则**：领域词（如 `head-level forgetting`）进 profile，不进 §3。
2. **不要靠加规则来"看起来严格"**：每条规则必须有真实来源（`source_round`），否则是噪音。
3. **不要用规则数量代替效果**：衡量标准是「下一轮导师意见里，同类问题的条数是否下降」。
4. **不要为了通过而调阈值**：发现脚本在真实稿上误报，应当修**规则语义**（如上下文窗口、豁免条件），
   并在文件头记录「什么误报、为什么、怎么修」——本工具的 v1.0→v1.2 就是这么改的。
5. **不要让机检替代人判**：`narrative_coherence` 类的逻辑矛盾（共享类 vs 缺失类）
   脚本抓不到，必须留 L3 人工/评审项。

---

## 9. 溯源

- 规则内容来源：一次完整的改稿复盘（意见结构化数据 + 规律报告；原始稿件与个人批注不随包分发）
- 脚本：`tools/advisor_pattern_gate.py`（v1.4 公开版，含正/负控制自测 `--self-test`）
- profile：`gates/paper_redline_profile.template.json`（论文专属规则请自建 profile）
