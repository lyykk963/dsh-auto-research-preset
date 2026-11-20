# 评审留痕（Review Tracing）

> 来源：吸收 ARIS `shared-references/review-tracing.md` 与 `tools/save_trace.sh` 的机制，适配 DSH 工作区。

## 0. 为什么留痕

独立评审的**可审计性**依赖完整记录：没有 trace，就无法回答
「评审真的发生过吗？评审模型是什么？与执行者是否同家族？评审判定依据了什么？」。
ARIS 把 trace 当作评审独立性的唯一证据。本协议要求**每次评审调用必须留痕**（Policy C：forensic，绝不静默跳过）。

## 1. 位置与命名

- 根目录：`<工作区>/.dsh-research/traces/<taskId>/`
- 每轮子目录：`round<N>/`，内含：
  - `review-request.md` — 发给评审的完整 prompt（含工件路径清单、Tier 声明）
  - `review-response.md` — 评审的完整回复（评分、verdict、弱点、修复建议）
  - `review-meta.json` — 元数据（见下）
- 追加式汇总：`<工作区>/.dsh-research/traces/<taskId>/TRACE_LOG.jsonl`（每轮一行，永不覆写）

## 2. review-meta.json schema

```json
{
  "taskId": "…",
  "round": 1,
  "tier": "cold-read",
  "executor_model": "deepseek-v4-flash",
  "reviewer_model": "…（实际使用的模型；缺失/未知须如实写 null）",
  "family_relation": "different | same | unknown",
  "independence_verified": true | false | "unverified",
  "reviewed_artifacts": ["results/exp1/*.json", "notes/method.md"],
  "verdict": "ready | almost | not ready | REVIEW_UNAVAILABLE",
  "score": 7.5,
  "weaknesses": ["…", "…"],
  "timestamp": "ISO8601"
}
```

- `family_relation` 必须从模型字符串如实推导：含 gpt/o1/o3/o4 → openai；claude/sonnet/opus/haiku → anthropic；gemini → google；deepseek/kimi/qwen/glm → 各自家族；无法判定 → `unknown`。
- **缺失/未知/同家族身份不能定罪**：评审模型身份无法证明独立时，该轮评审按 `REVIEW_UNAVAILABLE` 处理（fail-closed），不得冒充独立评审。

## 3. 硬规则

1. **每次评审必留痕**：T1/T2 评审调用后立即写入（先用 write 写 review-request/response，再补 meta）；漏留痕的评审在验收时无效。
2. **Append-only**：TRACE_LOG.jsonl 只追加（`>>`），永不删除/覆写历史行。
3. **run_id 绑定**：每次任务/每轮循环有唯一 run_id（如 `run_20260825_a1b2c3d4`），trace 文件名与 meta 都携带它，防止旧轮记录污染新轮验收。
4. **验收引用 trace**：acceptance-gate 中 G7/G9 等门引用 `TRACE_LOG.jsonl` 与 round 目录；无法定位 trace 的评分视为不存在。
5. **失败也要留痕**：评审调用失败/超时/REVIEW_UNAVAILABLE 也要写一行（status: error），因为"无评审"本身是验收状态的一部分。

## 3.5 统计索引（v9.3，供交付质量度量）

上面第 1–4 行是**取证**用的完整 trace；另需一个**统计索引**，否则"这个月比上个月强了吗"永远答不了。

```
<工作区>/.dsh-research/reviews/<taskId>-r<N>.json
{ "taskId":"…", "round":1, "ts":"…", "reviewer_tier":"T2",
  "verdict":"almost", "score":6, "critical":3, "major":8, "minor":9,
  "backfilled":false, "source":"subagent cold-read", "notes":"一句话列出 CRITICAL" }
```

- 它**不是第二份完整记录**，只是从 trace 里摘出的最小统计字段；写完 trace 后立即摘，字段从 trace 抄。
- 「固定预算 + 单指标 + keep/discard」里的单指标就是它算出来的**首轮零 CRITICAL 率**（定义见 `tools/review_metrics.py`）。
- **硬规则**：① verdict/score 拿不到就填 `null` + `unknown` + `backfilled:true`，**不许事后编分数**；② `reviewer_tier:"T3"`（自审）不入通过率——自评不能当质量证据；③ 索引条数少于 trace 轮数时，视为「该轮未统计」，在晨报里标注，不得静默补齐。

## 4. 借鉴记录

改编自 ARIS（MIT）：`shared-references/review-tracing.md`（Policy C forensic，.aris/traces/<skill>/<date>_run<NN>/）、
`tools/save_trace.sh`（完整 prompt/response 对 + 元数据）。
