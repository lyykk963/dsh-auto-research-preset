---
name: auto-research
description: 自动化科研总章程。夜间发布科研任务 → 通宵全自动执行（任务解析/研究计划/文献调研/方法设计/执行分析/撰写交付）→ 早晨交付晨报；同时维护右下角科研进度面板。任何自动化科研任务的会话都必须先加载本 skill 并按其执行。
---

# 自动化科研方法论（Auto-Research）

本 skill 是本模式（`自动化科研` 预设）的**执行协议**：进度文件协议、时间纪律、质量关口、晨报格式、进度面板插件维护、故障恢复。
**方法论主体是用户自研的「融合研究」skill（v8 模式定义层）**：任务以命名模式为入口，按四轴+一出口坐标系执行。本 skill 与融合研究的分工：融合研究决定「怎么做研究」（深度/自主度/时间/光谱/产出），本 skill 决定「如何落盘、报进度、跨夜续跑、交付晨报」。

## 0. 核心概念

- 一个「科研任务」= 一次完整交付：从用户的任务描述到晨报（夜间全自动模式）或对应模式的交付物。
- 任务入口：**手动选择命名模式**（🌙夜间全自动 / ⚡快速查证 / 🔬专题半自主 / 📄发表冲刺 / 💡灵感风暴 / 🎤组会材料），档位定义与行为映射见融合研究真身 `%USERPROFILE%\.trae-cn\skills\融合研究\references\mode-definitions.md`。
- 所有状态与产物都**落盘在工作区**（`.dsh-research/` 与各阶段目录），跨轮次、跨重启可恢复 —— 这是通宵自动化与面板持久化的根基。
- 右下角面板 = 进度可视化；其数据源是 `<工作区>/.dsh-research/progress.json`，面板轮询读取。
- **跨模型评审与证据门（v8.1 新增，吸收 ARIS）**：质量/正确性验收不得由执行者自判——评审必须来自独立视角（Tier≥T2 冷读），且每阶段完成必须有**确定性证据**落盘（`acceptance-gate.md`：「能 DRIVE，不能 ACQUIT」）。细则见 §10–§12 与 `contracts/` 目录。
- **科研大脑（v8.2 新增）**：一条主循环 + 一份持久研究状态——`wake→plan→execute→verify→reflect→next`，以 `SKILLS_REGISTRY.md`（能力地图）做路由、`brain.json`（研究思考状态）做工作记忆。细则见 `references/research-brain.md` 与 `contracts/research-brain.md`。这是把 540+ 执行层 skills 真正"用起来"的编排中枢。

## 1. 阶段工作流（默认 6 阶段，可按任务增删）

| # | 阶段 | id | 说明 | 默认时间占比 |
|---|------|----|------|-------------|
| 1 | 任务解析 | intake | 澄清/记录假设、目标与验收标准、写 `task.json` | 5% |
| 2 | 研究计划 | plan | 拆解任务、排期、确定阶段与 skill 路由、写 `PLAN.md` | 10% |
| 3 | 文献调研 | litreview | 系统检索、阅读、整理证据库 `notes/litreview.md` | 25% |
| 4 | 方法设计 | method | 方法/实验/模型设计、可行性验证、写 `notes/method.md` | 15% |
| 5 | 执行与分析 | execute | 数据获取、预处理、建模/分析、可视化，产物进 `results/` | 30% |
| 6 | 撰写交付 | write | 撰写报告、自检、生成晨报 `MORNING_REPORT.md` | 15% |

规则：
- 湿实验、纯写作、纯综述类任务可增删阶段；**每次调整后立即更新进度文件**，让面板反映真实拆解。
- 每阶段开始时用 todo_write 登记子任务；完成后对照验收标准自检（见 §5）。

## 2. 进度文件协议（面板数据源）

路径：`<工作区>/.dsh-research/progress.json`
初始化：先执行 `New-Item -ItemType Directory -Force <工作区>/.dsh-research`（Windows）或 `mkdir -p`（macOS/Linux）。

更新方式（二选一，格式一致）：
1. 优先调用 **update_research_progress** 工具（进度面板插件注册；path 传绝对路径）。⚠️ **参数格式**：path/state 为**工具顶层属性**，直接传参，不要用 `{"arguments": {...}}` 包装；同一工具连续 2 次参数格式失败 → 立即切换方案 2（write 直写），不要重试第 3 次。
2. 插件不可用时直接用 **write** 工具写同一文件。

Schema（v1）：

```json
{
  "version": 1,
  "taskId": "2025-06-15-phd-01",
  "title": "基于深度学习的蛋白质-配体结合亲和力预测",
  "mode": {
    "id": "night-auto",
    "name": "夜间全自动",
    "customized": false,
    "axes": { "L": "L2/L3", "A": "A4", "R": "Autopilot", "T": "T3", "M": "Balanced", "D": ["D2", "D3", "晨报"] }
  },
  "status": "running",
  "deadline": "2025-06-16T07:00:00",
  "publishedAt": "2025-06-15T23:05:00",
  "currentPhaseId": "litreview",
  "overallPercent": 35,
  "phases": [
    { "id": "intake",    "name": "任务解析",   "status": "done",    "percent": 100, "startedAt": "…", "finishedAt": "…", "note": "目标与验收标准已确认" },
    { "id": "plan",      "name": "研究计划",   "status": "done",    "percent": 100, "startedAt": "…", "finishedAt": "…", "note": "6 阶段，预算已排" },
    { "id": "litreview", "name": "文献调研",   "status": "running", "percent": 60,  "startedAt": "…", "note": "已检索 42 篇，精读 12 篇" },
    { "id": "method",    "name": "方法设计",   "status": "pending", "percent": 0,   "note": "" },
    { "id": "execute",   "name": "执行与分析", "status": "pending", "percent": 0,   "note": "" },
    { "id": "write",     "name": "撰写交付",   "status": "pending", "percent": 0,   "note": "" }
  ],
  "reportPath": null,
  "note": "正在精读 2023 年后的 SOTA 模型对比",
  "lastUpdatedAt": "2025-06-16T01:12:00"
}
```

字段规则：
- `mode`：模式快照（命名模式 + 轴档位），任务接收确认模式后写入；面板展示模式标签，悬停显示轴档位
- `status`（任务级）：`idle | queued | planning | running | blocked | done`
- 阶段 `status`：`pending | running | blocked | done`
- `percent`：0–100 整数
- `overallPercent`：优先自己算（各阶段按 effort 加权，默认等权平均）；不填则面板取等权平均
- `note`：当前正在做什么（面板直接展示，保持一句话）
- 每次更新都刷新 `lastUpdatedAt`；阶段开始/结束填 `startedAt` / `finishedAt`

**必须更新的时机**：
- 任务接收完（intake 完成）→ 列全 6 阶段、status=planning
- 每个阶段开始（status=running）、结束（status=done、percent=100）
- 阶段内实质进展（percent 每 +10% 或状态切换）
- blocked 时立刻更新（status=blocked + note 写明原因与恢复计划）
- 晨报写完 → status=done、overallPercent=100、reportPath 填晨报路径

## 3. skill 路由表（骨架：以本地已有科研 skills 为主体）

**原则：每个子任务先查表选最匹配的 skill，用 skill 工具加载后再干活；找不到专门 skill 时用 `deep-research` 或「检索 + 写作」兜底组合。**
执行层技能路由以融合研究 v8 为准（其 SKILL.md 第十部分路由表 + 资源索引），本表为 DSH 侧速查。

### 3.1 文献与检索
- `deep-research` — 六阶段系统文献综述（结构化笔记+论文库+综合报告）**【综述兜底】**
- `literature-review` / `literature-search` — 多库系统综述；Semantic Scholar/arXiv/OpenAlex 结构化 JSONL 检索
- `paper-lookup` — 10 个学术库：PubMed/PMC/bioRxiv/medRxiv/arXiv/OpenAlex/Crossref/S2/CORE/Unpaywall
- `research-lookup` / `exa-search` / `parallel-web` / `bgpt-paper-search` — 快速检索、深度检索、论文全文结构化提取
- `citation-management` — 引文校验与 BibTeX；`paperzilla` — 与论文库对话

### 3.2 假设、方法与批判性评估
- `scientific-brainstorming` / `idea-generation` / `idea-refine` / `hypothesis-generation` / `hypogenic` — 选题与假设
- `scientific-critical-thinking` / `peer-review` / `scholar-evaluation` — 证据等级、实验设计缺陷、方法评审

### 3.3 数据分析与建模
- `get-available-resources` — **任何重计算前先查**（CPU/GPU/内存/磁盘）
- `exploratory-data-analysis` — 200+ 格式数据初探（先摸清结构再分析）
- `statistical-analysis` / `statsmodels` / `pymc` / `scikit-learn` / `pymoo` / `shap` / `umap-learn` / `aeon` / `timesfm-forecasting` / `scikit-survival`
- `scientific-visualization` / `matplotlib` / `seaborn` / `scipilot-figure-skill` — 成图（发布级）
- 领域专用（按任务匹配，代表）：单细胞 `scanpy`、转录组 `pydeseq2`、化学 `rdkit`、材料 `pymatgen`、天文 `astropy`、地学 `geomaster`、神经 `neurokit2`、序列 `biopython`、量子 `qiskit`。**完整清单见 `~/.agents/SKILLS_REGISTRY.md`，用 `tools/skill_routing.py route` 自动选。**

### 3.4 计算与工程
- `dask` / `polars` / `vaex` / `zarr-python` / `optimize-for-gpu` / `pytorch-lightning` / `transformers`
- `nextflow` / `pacsomatic`（流水线）、`modal`（云端 GPU 按需）、`get-available-resources`（前置）

### 3.5 撰写与交付
- `scientific-writing` — IMRAD 论文写作（两阶段：要点+检索 → 成文）**【写作兜底】**
- `markdown-mermaid-writing` — 文档与图（默认文档规范）
- `scientific-slides` / `latex-posters` / `pptx` / `pptgen-drawio` / `venue-templates` — 汇报材料
- 临床/医学类：`clinical-reports` / `clinical-decision-support` / `treatment-plans` / `research-grants`

### 3.6 质量与验证
- `verification-before-completion` — 声称完成前必须验证（跑命令、查文件、对结论）
- `debugging-and-error-recovery` / `systematic-debugging` / `diagnosing-bugs` — 出错恢复
- `code-review-and-quality` / `code-reviewer` / `scientific-critical-thinking` — 代码与结论评审

### 3.7 科研基础设施
- `protocolsio-integration` / `benchling-integration` / `labarchive-integration` / `pyzotero` / `obsidian-vault` / `opentrons-integration` / `pylabrobot` / `adaptyv` / `ginkgo-cloud-lab` / `rowan` / `diffdock`
- ⚠️ 涉及真实下单/收费实验/对外提交：只产出方案与参数清单，**必须经用户明确确认后**才能调用执行类 API。

## 4. 时间纪律（按时间要求执行）

- **截止时间**：用户给定则用给定的；未给定时默认「次日早晨 07:00」（夜间任务），或用户入睡时刻 + 8 小时。
- **排期**：总预算 = 截止 − 当前时刻 − 30% 缓冲；按 §1 占比分配到各阶段；写入 `PLAN.md`。
- **时钟**：每阶段开始前确认当前时间（`pwsh Get-Date` / `bash date`），结束时核对是否超支。
- **超支处置**（按序）：压缩低优先级细节 → 用 subagent/workflow 并行拆分（文献、数据、写作分头推进）→ 缩减范围并在晨报「局限」中标注。
- **绝不空转**：一个子任务阻塞就换另一个推进；后台任务（background job / subagent）等待期间继续做别的。

## 5. 质量关口（每阶段收尾必做，6 条）

1. 产物存在且可打开（文件校验，不许口头声称）
2. 对照本阶段验收标准自检
3. 数据/结论可复现：记录版本、随机种子、命令、参数
4. 用 update_research_progress 更新进度（状态+百分比+note）
5. 不确定性明确标注（数据缺失、假设、置信度）
6. **运行反馈写盘（v9 硬规则，三件套缺一不得标 done）**：每阶段收尾必须向 `.dsh-research/` 追加：
   - `skill-usage.jsonl`（本阶段用过技能的反馈行，见 `references/skill-intelligence.md` §16.3）
   - `meta/events.jsonl`（本阶段关键事件 ≥1 行：skill_invoked / tool_failed / gate_triggered / phase_done）
   - `iteration-log.jsonl`（每目标轮结束 1 行，见 §12 与 `contracts/watchdog-contract.md` §3.1）
   三文件若该阶段无任何新行 → 该阶段**不得标 done**；"本阶段没调工具/没进展"不能成为跳过理由——无事发生也写一行 `no_new_findings`。

**v8.1 增强（吸收 ARIS）**：
- **证据门（DRIVE）**：每阶段收尾除上述 5 条外，把本阶段的确定性证据文件登记到 `.dsh-research/evidence/MANIFEST.md`（模板 `templates/EVIDENCE_MANIFEST.md`）；证据缺失的阶段**不得标 done**（口头声称 ≠ 证据）。见 `contracts/acceptance-gate.md` §3。
- **质量验收（ACQUIT）**：D2 及以上交付物的质量门（融合研究 G7/G9 等）必须引用**独立评审（Tier≥T2）**或确定性校验输出；执行者自评不构成验收依据。见 `contracts/reviewer-independence.md`。
- **评审留痕**：每次独立评审的完整 prompt/response 落盘 `.dsh-research/traces/<taskId>/round<N>/`。见 `contracts/review-tracing.md`。

**v9.3 增强（把 CRITICAL 前置）**：`write` 收尾、送评审**之前**依次跑三道门（细则与反博弈条款见 `contracts/acceptance-gate.md` §3.0；台账 `.dsh-research/memory/failure-modes.md`）：
- `tools/check_claims.py <交付目录>` —— M3 数字声明（2/7 的 CRITICAL）：每个关键数字须在 `claims.json` 声明并由证据重算。**不许改 `expect` 迁就实测**。
- `tools/prereg.py verify <交付目录>` —— M1 口径预注册（3/7）：看数据后改口径会被**指名字段**；改动走 `amend -m "理由"`。
- `tools/check_delivery.py`（10 项，含**技能记录硬门**）+ `tools/skill_routing.py check`（**该用未用**对账，`--strict` 阻断；分工见 `contracts/skill-authority.md`）。
- **PPT 交付额外过** `tools/check_deck.py <deck.pptx>`（纯文字页占比 / 图形数 / 构图多样性）；设计与反 AI 感红线见 `contracts/slide-design.md`。

## 6. 晨报格式（交付物）

文件：`<工作区>/MORNING_REPORT.md`（同时归档一份到 `.dsh-research/reports/`）

```markdown
# 科研晨报 — {YYYY-MM-DD}
## 任务
（一句话 + 原始任务描述要点）
## 核心成果（3–5 条）
- ...
## 关键发现 / 数据结论
（含关键数字、图表索引、证据来源）
## 产物索引
| 文件 | 说明 |
|------|------|
## 假设清单与局限
- 假设：...；局限：...
## 下一步建议
- ...
```

完成流程：写晨报 → 更新进度 done/100% → complete goal → 最终消息汇报报告路径与要点（面板同步显示 100%）。

## 7. 进度面板插件维护

插件 = 会话级动态 Cordis 插件：
- **Host 半身**：读写 `progress.json`、注册 `update_research_progress` 工具、注册 `research-progress:get` / `research-progress:set` RPC
- **Client 半身**：右下角浮动面板（`shell.overlay`），每 4 秒轮询 `host.call('research-progress:get')`

**源码位置**：与本 SKILL.md 同目录（即本 skill 的 baseDir）：
- `plugin-host.js` → cordis_define 的 `code.host`
- `plugin-client.js` → cordis_define 的 `code.client`

**启动/恢复步骤**：
1. 检查：`cordis_inspect_self`（不带参数）列出插件。找到名字含 `research-progress` 的插件且 `activeRun` 正常 → 已运行，跳过。
2. 若定义存在但未运行 → `cordis_run { pluginId, packageId: currentPackageId, mode: "run" }`。
3. 若完全不存在（如进程重启后）→ 用 read 工具读取两个源码文件，然后：
   - `cordis_define { plugin: { kind: "new", idPrefix: "respr" }, name: "research-progress", purpose: "科研任务进度面板：右下角实时展示任务拆解与阶段进度", code: { host: <plugin-host.js 全文>, client: <plugin-client.js 全文> } }`
   - `cordis_run { pluginId, packageId, mode: "run" }`（首次运行）
4. 返回 `awaiting-approval`（Client 包需授权）→ 告诉用户点击授权即可，**继续推进其他工作**，不要等待；`starting` → 等待系统报告结果。
5. 面板数据流：本 agent 每次用 `update_research_progress` 写进度 → 面板自动轮询刷新。

**重启后**：动态插件随进程消失，但 `progress.json` 在磁盘上 → 按本 skill 启动协议重建插件即可，进度不丢。

## 8. 故障与恢复

- **阶段失败**：加载 `debugging-and-error-recovery` 定位修复；修复无望 → 记录 blocked 原因、更新进度、切换到可推进部分，晨报中说明。
- **插件/工具异常**：直接用 write 工具维护 `progress.json`（格式见 §2）；面板下次轮询自动恢复。
- **通用重试上限（v8.1 meta 改进 A1b）**：同一工具以同一错误连续失败 ≥2-3 次 → **停止重试**，换路径/换工具（如 write 直写），并把失败记入 `.dsh-research/meta/events.jsonl`（event: tool_failed）；不得第 4 次重试同一格式（实测教训：同一格式错误曾连续 8 次）。
- **会话中断/重启**：恢复依据 = `.dsh-research/` + goal 状态（get_goal）；先恢复进度文件再继续执行。
- **用户白天介入**：正常对话响应；按用户意愿继续、暂停或调整任务（暂停时 update_goal pause，恢复时 resume）。
- **任务跨夜**：未完成时晨报先出「阶段进展」+ 次日计划；goal 保持 armed，次日夜间自动续跑。

## 9. 任务完成判定（验收清单）

- [ ] 全部阶段 done（且各阶段证据门文件齐全，见 §5 增强）
- [ ] 涉及质量验收的交付物有独立评审记录（Tier≥T2）或确定性校验输出（traces/ 可定位）
- [ ] MORNING_REPORT.md 已生成且通过 §5 自检
- [ ] progress.json：status=done、overallPercent=100
- [ ] goal complete
- [ ] 最终消息给出报告路径与核心要点

---

## 10. 跨模型评审与评审员独立（v8.1，吸收 ARIS）

> 细则：`contracts/reviewer-independence.md`。核心：**执行者不得审判自己的诚实度**。

- **评审独立性分级**：T1 跨模型/跨实例（workflow 子代理 provider/model 覆盖，异族模型）→ 可当验收依据；T2 冷读同模型（全新子代理，只给工件路径，不给转述）→ 参考分，provisional；T3 自审（同模型带自述上下文）→ 禁止作为质量验收。
- **硬规则**：冷读（只传文件路径）；全新线程/子代理每轮（REVIEWER_BIAS_GUARD，防分数膨胀——ARIS 实测续聊可把 3/10 膨胀到 8/10）；家族判定 fail-closed（无法证明独立 → REVIEW_UNAVAILABLE，不假装）；对抗立场（假定作品某处是坏的）。
- **T1 探测时机（v8.1 meta 改进 A2）**：跨模型可用性在**任务启动时**探测一次（workflow agent 带 provider/model 覆盖），结果（可用/不可用）写入 evidence；不可用则本轮全程按 T2 执行，**后续轮次不重复尝试**；phase_done 时重探一次（部署可能变化）。探测轻量非阻塞：失败只记录，不 fail-closed 停摆。
- **与融合研究 R1–R5 的关系**：五角色保留为评审内部角色分工，但评审代理本身必须 Tier≥T2；主模型自扮五角色不再视为独立评审。
- **停止条件（对齐 ARIS）**：独立评审给出 `score >= 6/10 且 verdict ∈ {ready, almost}`（AND）才可停止迭代；高分数 + not ready ≠ 停止；迭代上限按融合研究 G8（≤8 轮）或任务约定。

## 11. 证据门与验收门（v8.1，吸收 ARIS）

> 细则：`contracts/acceptance-gate.md`。核心：**能 DRIVE，不能 ACQUIT**。

- 执行者可以自判「执行完成度」（DRIVE：文件存在、命令跑完、产物齐全）；**不可以自判「质量/正确性/新颖性」**（ACQUIT 必须外部：独立评审或确定性验证）。
- 每阶段完成时逐条落盘证据到 `.dsh-research/evidence/<phaseId>/`，登记到 `MANIFEST.md`；缺证据 = 该阶段不得标 done。
- 融合研究 G1–G10 在 DSH 执行层接线：G7/G9 只认 Tier≥T2 评审分数；G5 走确定性检查；G6 由迭代日志提供数据；T3 自审分无效。

## 12. 无人值守与存活契约（v8.1，吸收 ARIS）

> 细则：`contracts/watchdog-contract.md`。

- **AUTO_PROCEED**：夜间全自动默认自动继续，不在关卡停下来问人；歧义记为假设、晨报列明。
- **Watchdog（轮间自检）**：progress.json 新鲜度 >45 分钟、连续 2 轮无进展、超支、后台任务卡死 → 强制触发实质推进或显式告警（progress note 写 `⚠️ watchdog: <信号>`，晨报汇总）。只报告，不自动重启裁决性流程。
- **迭代日志**：每轮向 `.dsh-research/iteration-log.jsonl` 追加一行（new_findings/artifacts_changed/percent）；连续 2 轮无新发现 → 强制换方向；连续 4 轮 → 上报 blocked 候选 + 晨报标注。
- **日志缺失即告警（v9）**：Watchdog 自检把「skill-usage.jsonl / meta/events.jsonl / iteration-log.jsonl 三文件近一轮无新行」列为停滞信号（同 2.1 的"连续 2 轮无进展"）——文件不增长 = 预设未在执行闭环，直接告警，不等脑内判断。
- 与融合研究 G6（认知循环）共用数据：G6 阈值对照 iteration-log 判定。

## 13. 深度文档索引（原 §13–16 已外移，v9.3）

主文件只留**每轮必读**的协议；以下四份为按需加载的深度文档（同目录 `references/`）：

| 文档 | 内容 | 什么时候读 |
|------|------|-----------|
| `references/artifact-contracts.md` | 工件契约、引用纪律、模板清单、实验卡片门、v9.2/v9.3 新增（自检入口、审查记录、写作红线） | 要落盘产物 / 写契约 / 查模板时 |
| `references/aris-integration.md` | ARIS 借鉴记录（各条机制的来源与许可） | 想知道某条规则从哪来时 |
| `references/research-brain.md` | 科研大脑：`brain.json` 结构、六步主循环、硬规则、与 light-skills / K-Dense 的关系 | 做 wake / plan / reflect 需要细则时 |
| `references/skill-intelligence.md` | 技能智能：G 图谱 / P 竞争带 / R 运行反馈、路由决策、维护 | 选技能、维护技能库时 |

**三条不能丢的红线**（已随文档搬走，此处复述）：
1. **自评不得作为质量验收依据** —— 验收只走 Tier≥T2 独立评审或确定性脚本（`evidence_check.py` / `stage_gate.py` / `text_gates.py`）。
2. **被评者不得改写判据** —— `objective-evolution-protocol` 的「修改评分函数」默认禁用。
3. **方法论真身不可改名** —— 真身在 Trae 侧 `融合研究`，DSH 侧用 `fusion-research` 指针技能加载。

> 拆分依据（2026-10-17）：主文件当时 34.9 KB，触发 `tools/selfcheck.py` 的体积预算 warn（24 KB）。
> 外移**只搬家、不删改**；行级多重集守恒由拆分脚本自检。
---

## 17. 自我改进三件套（v9.3）

预设自己也要被度量。三个**只读**工具，用可复算的方式回答三个问题：

| 工具 | 回答的问题 | 频率 |
|------|-----------|------|
| `tools/selfcheck.py` | 技能能不能加载？资产还能用吗？日志编码/JSON 完好么？（三层） | 每次会话开场（已挂进启动协议） |
| `tools/review_metrics.py` | 交付质量在变好还是变差？（首轮通过率 / 首轮零 CRITICAL 率 / 返工轮数 / 每轮 CRITICAL） | 每次交付后 |
| `tools/cost_metrics.py` | 一次交付花多少机时？（代理：墙钟 × 轮数；**真实 token 不可得**，只许自己比自己） | 每周 |
| `tools/claimlog.py` | 数字由脚本**顺手记账**（不再人肉抄），且尽量从 **primary** 重算 | 写分析脚本时 |
| `tools/fetch.py` | 数据能不能稳定取到？（退避重试 / 每域限速 / 编码自适应 / 镜像回退 / **强制快照**） | 任何联网取数 |

**取数纪律**：所有 http 取数走 `fetch.py`——它落 (raw, meta.json) 快照并记 sha256/编码/耗时；**没有快照等于没取过**。失败要报 `blocked`/`error`，不许静默返回空。

**迭代纪律（固定预算 + 单指标 + keep/discard）**：一轮只动 **1 个资产** → `selfcheck` 全绿且独立评审无 CRITICAL → **keep**（记 CHANGELOG、版本 +1）；否则 **discard**（从 `.backup/` 回滚）。每轮往 `.dsh-research/meta/events.jsonl` 追加一行留痕。

**2026-10-17 基线（首批可复算数字）**：`SELFCHECK: OK | skills 待修 0 | assets 6/6 pass、0 warn | logs 27 files`；首轮通过率 **0%**、首轮零 CRITICAL 率 **0%**、平均返工 **1.5 轮**、每轮平均 **2.67 个 CRITICAL**；墙钟中位 **105 min**。