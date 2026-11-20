# 技能智能（auto-research 参考文档）

> 自 `skills/auto-research/SKILL.md` 外移，2026-10-17。内容未改写，仅搬家。
> 回滚方式：从 `.backup/` 恢复 SKILL.md 即可。

# 16. 技能智能（v8.3：G 图谱 · P 竞争带矩阵 · R 运行反馈）

> 让大脑"深入每个技能、知道各自优缺点"。设计详见 `.dsh-research/skill-intelligence-design.md`。

### 16.1 三个知识源

| 源 | 内容 | 位置 | 更新 |
|----|------|------|------|
| **G 技能图谱（自动）** | 每技能：擅长/不适用/绝不/转移建议("For X use Y")/依赖(key/GPU/MCP)/链(stage/emits/consumes) | 全局 `~/.agents/SKILL_GRAPH.json` + `.md`（工作区镜像 `.dsh-research/`） | 重扫脚本 `reference/gen-graph.js` |
| **P 竞争带矩阵（深读）** | 同意图候选对比：主攻/边界短板/依赖/质量档/何时用/何时换 | `reference/SKILL_PROFILES/<簇>.md` + `index.md` | 按簇子代理深读+复核 |
| **R 运行反馈（会学习）** | 每次用过的技能：效果(success/rework/abandoned/blocked)/坑/替代 | `<工作区>/.dsh-research/skill-usage.jsonl` | 主循环 reflect 步自动追加 |

### 16.2 路由决策（替代"盲扫注册表"）

plan 步遇到"同一意图多候选"时执行：
1. **G**：从图谱取候选的边界/依赖/转移建议，剔除明确不适用者；
2. **P**：查对应竞争带矩阵（`SKILL_PROFILES/<簇>.md`）读对比；
3. **R**：查 `skill-usage.jsonl` 该技能历史（连续 blocked/abandoned → 降权并换候选）；
4. 决策写入 `brain.json.decisions`（为什么选它/不选谁），供复盘。

### 16.3 反馈纪律（R 层）

- reflect 步每次用过技能追加一行 `skill-usage.jsonl`：
  `{"ts":ISO,"taskId":"…","skill":"…","phase":"…","outcome":"success|rework|abandoned|blocked","pitfall":"…","alternative":null}`
- 每 ~10 条或任务收尾，把新反馈并入对应 `SKILL_PROFILES` 的"体验"备注；与 meta-optimize（events.jsonl）共用日志纪律。
- 连续 2 次同技能 blocked/abandoned → 晨报「局限」提示并默认换路由。

### 16.4 维护

- 技能库变动后：重跑 `reference/gen-graph.js`（G 层自动刷新）+ 视需要补/更新受影响竞争带矩阵。
- 矩阵制作=子代理深读对应簇 SKILL.md 产出候选矩阵，本 agent 复核后并入 `SKILL_PROFILES/`。
