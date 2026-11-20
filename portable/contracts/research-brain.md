# 科研大脑（Research Brain）— 状态机 + 编排主循环

> 本契约是「自动化科研」模式的核心编排层：把方法论（融合研究）、执行协议（auto-research 六阶段）、
> 能力地图（SKILLS_REGISTRY）与海量执行层 skills 串成一条**自动主循环**。
> 定位：progress.json 记「进度」，brain.json 记「研究思考状态」——假设、claims、决策、开放问题、下一步。

## 0. 一句话

「科研大脑」= **一条主循环 + 一份持久研究状态**：
```
wake(恢复状态) → plan(查注册表定下一步) → execute(选技能执行) → verify(证据门+独立评审) → reflect(记状态) → next(继续/换向/交付)
```
每轮循环由大脑自动推进；质量验收仍受 acceptance-gate/reviewer-independence 约束（大脑能 DRIVE，不能 ACQUIT）。

## 1. 研究状态文件 brain.json

位置：`<工作区>/.dsh-research/brain.json`（跨会话持久；模板见 `templates/brain-state.json`）。

```json
{
  "taskId": "2026-09-04-xxx",
  "mode": { "id": "night-auto", "name": "夜间全自动", "axes": { "L":"L2/L3","A":"A4","R":"Autopilot","T":"T3","M":"Balanced","D":["D2","D3","晨报"] } },
  "goal": "一句话研究目标",
  "hypotheses": [ { "id": "H1", "text": "…", "status": "active | supported | refuted | stale", "evidence": ["路径"] } ],
  "assumptions": [ "…（歧义/未证实的前提，晨报列明）" ],
  "claims": [ { "text": "…", "evidence": ["文件路径"], "status": "unproven | verified | refuted" } ],
  "decisions": [ { "at": "ISO", "text": "…", "reason": "…" } ],
  "openQuestions": [ "…" ],
  "nextAction": "下一步具体动作（含目标 skill / 产出路径 / 验收）",
  "stalled": false,
  "lastUpdate": "ISO"
}
```

字段规则：
- `hypotheses` / `claims` 必须带证据路径（对齐 evidence-gate：口头声称 ≠ 证据）；状态沿 PROOF 轴。
- `decisions` 只记关键分叉（方向/方法/范围变化），append-only 语义。
- `nextAction` 是大脑的"工作指针"：每轮结束必更新；跨会话 wake 时据此恢复，绝不空转。
- `stalled` 由 watchdog/迭代日志判定写入（连续 2 轮无新发现 → true + 换向）。

## 2. 六步主循环

| 步 | 动作 | 产物/依据 |
|----|------|----------|
| **1. wake** | 读 `brain.json` + `progress.json` + goal 状态；还原模式快照与 nextAction；向用户/日志报告"上次断在哪、为什么、接下来做什么" | brain.json / progress.json / get_goal |
| **2. plan** | 查 `SKILLS_REGISTRY.md`（12 类意图→技能）选定本步技能与路由；写 nextAction 与阶段 todo | SKILLS_REGISTRY |
| **3. execute** | 用 skill 工具加载选定技能并按其执行；产物落盘；登记证据到 `evidence/MANIFEST.md` | 对应 skill + contracts/ |
| **4. verify** | 证据门（G11）：产物存在 + 证据齐全；质量门：D2+ 需 Tier≥T2 独立评审（reviewer-independence）；评审留痕 traces/ | acceptance-gate / review-tracing |
| **5. reflect** | 更新 brain.json：新假设/claims/决策/openQuestions；追加 iteration-log.jsonl（new_findings）；写 FINDINGS | brain.json / iteration-log |
| **6. next** | 决策：继续下一循环 / 换向（连续 2 轮无新发现）/ 交付（全部阶段 done + 晨报） | watchdog-contract / 验收清单 |

## 3. 与既有协议的关系（不重复、只补位）

- **progress.json** = 进度/面板（六阶段 status/percent）；**brain.json** = 研究思考状态（语义）。二者并存，wake 时同时读。
- **SKILLS_REGISTRY.md** = 能力地图（静态索引，随技能库变化重新生成）；brain 的 plan 步查它。
- **六阶段工作流**（intake/plan/litreview/method/execute/write）仍是交付骨架；大脑主循环是跨阶段的"神经"，每阶段内部多轮循环。
- **质量/独立评审/证据门/迭代日志** 全部保留，verify 与 reflect 步强制接线（见 §2）。
- **融合研究 v8** 提供模式/原则/质量门 G1-G11；大脑负责把它们在每一轮落实。

## 4. 能力注册表再生成

技能库变动后（如 `skills update` / 新装 Light-skills / K-Dense pull），重新扫描生成：
`<工作区>/.dsh-research/SKILLS_REGISTRY.md` 与全局 `~/.agents/SKILLS_REGISTRY.md`。
生成脚本约定：扫各技能根 SKILL.md 的 name+description，按 12 类关键词聚类（见注册表头注）。

## 5. 技能智能（G 图谱 · P 竞争带 · R 运行反馈）

plan 步从"查注册表选一个"升级为**路由决策**（详见 `skills/auto-research/references/skill-intelligence.md` 与
`.dsh-research/skill-intelligence-design.md`）：

| 源 | 内容 | 位置 |
|----|------|------|
| G 图谱（自动） | 每技能擅长/不适用/转移建议/依赖/链 | `~/.agents/SKILL_GRAPH.{json,md}`（生成：`reference/gen-graph.js`） |
| P 竞争带矩阵 | 同意图候选对比（写作/文献/图表/评审…） | `reference/SKILL_PROFILES/<簇>.md` |
| R 运行反馈 | 用过的技能效果/坑 | `<工作区>/.dsh-research/skill-usage.jsonl`（reflect 步追加） |

路由决策四步：G 剔不适用 → P 读对比 → R 查历史（连续 blocked 降权）→ 写 `brain.json.decisions` 理由。
新技能入库/技能库更新后：重跑 `gen-graph.js`；新增竞争带时补矩阵（子代理深读 + 复核）。
