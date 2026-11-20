# 元优化与被动使用日志（Meta-Optimize）

> 来源：吸收 ARIS `meta-optimize`（hooks 被动日志 → 分析 → 改进建议 → 评审 → 批准）与 `meta-apply`
> （producer 只读提建议 / applier 有权限落地，落地时自己重跑评审）的机制，轻量适配 DSH 预设。

## 0. 目标

让预设能**基于真实使用数据优化自己**：记录每次任务的执行事件，周期性分析，提出对 skill/契约/流程的改进建议，
经独立评审与用户批准后落地。闭环：「能推进，不能自封」——改进建议的产生与落地权限分离。

## 1. 被动日志（events.jsonl）

位置：`<工作区>/.dsh-research/meta/events.jsonl`（追加式 JSONL，每事件一行）

```json
{"ts": "2026-08-26T02:30:00", "taskId": "aris-02", "phase": "execute",
 "event": "skill_invoked", "skill": "auto-research", "ok": true, "detail": "…"}
{"ts": "…", "taskId": "…", "phase": "litreview", "event": "tool_failed",
 "tool": "paper-lookup", "ok": false, "detail": "timeout"}
{"ts": "…", "taskId": "…", "phase": "method", "event": "gate_triggered",
 "gate": "G11", "detail": "evidence missing: execute"}
{"ts": "…", "taskId": "…", "phase": "execute", "event": "round_no_progress",
 "round": 3, "detail": "iteration-log stale≥2"}
```

事件类型（最小集）：`skill_invoked` / `tool_failed` / `gate_triggered` / `round_no_progress` / `direction_change` / `assumption_recorded` / `phase_done`。
规则：每轮/每阶段结束时顺手追加（追加成本 < 1 行）；不阻塞主线。

## 2. 周期自审（meta 复盘）

- **触发**：每完成一个任务（或累计 ≥5 次事件）后，花 ≤15 分钟做一次 meta 复盘：
  1. 读 events.jsonl，统计：哪些 skill/工具失败最多、哪些门常被触发、哪些阶段空转。
  2. 提出 ≤3 条改进建议（对 SKILL.md / contracts / 流程），每条附数据依据。
  3. **建议必须经独立评审（Tier≥T2）** 后，才允许修改 skill/契约本体（对齐 ARIS：a loop can DRIVE; only the cross-model jury can ACQUIT）。
  4. 用户批准后落地，写 improvement-plan 增量；不批准则记录待办。
- **权限分离**：本 agent 是 producer（只读分析、提建议）+ 在批准后作为 applier（落地）；落地时按 acceptance-gate 引用评审记录。
- **不覆盖既有实践**：融合研究 skill 已有 improvement-plan/quality-report 惯例——本日志为其提供数据输入，不替代。

## 3. 阈值与防自我吹捧

- **防自封**：改进建议的「有效」判定（是否值得落地）由独立评审给，不由提建议者自判。
- **防漂移**：改动预设本体前先确认与 v8.1 契约一致（不得破坏 acceptance-gate/reviewer-independence 等既有强制规则）。
- **记录**：每次落地写 `improvement-plan` 增量条目 + 更新质量报告；events.jsonl 永不截断（超过 5000 行时归档到 `events-<date>.jsonl`）。

## 4. 借鉴记录

改编自 ARIS（MIT）：`meta-optimize`（hooks 日志→建议→reviewer→批准）、`meta-apply`（producer/applier 权限分离 + 落地重跑评审）、`templates/claude-hooks/meta_logging.json`（被动日志事件）。
