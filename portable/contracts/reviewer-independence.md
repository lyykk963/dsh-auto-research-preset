# 评审员独立协议（Reviewer Independence Protocol）

> 来源：吸收 ARIS（SJTU，Auto-Research-In-Sleep，MIT）`shared-references/reviewer-independence.md` 的跨模型评审纪律，
> 适配 DSH 单会话环境。本协议是 auto-research skill「跨模型评审」章节的细则。

## 0. 为什么需要它

融合研究 v8 的对抗评审（R1–R5 五角色）是**同一模型扮演多个角色**的自我博弈：
角色差异来自人设剧本，不是不同模型的真实认知差异 → 存在系统性盲区与自我一致偏误。
ARIS 的核心结论：**「执行者不得审判自己的诚实度」**。评审必须来自独立于执行者的视角，
否则分数膨胀（ARIS 实测：同一 reviewer 用 `codex-reply` 续 thread 时，分数从真实的 3/10 膨胀到 8/10）。

## 1. 评审独立性分级（Tier）

| Tier | 条件 | 标签 | 可当验收依据 |
|:--|:--|:--|:--|
| **T1 跨模型/跨实例** | 评审由**不同模型家族**（如 OpenAI/Anthropic/Google/DeepSeek 互异）或至少不同模型实例执行；在 DSH 中优先用 workflow 子代理的 `provider`/`model` 覆盖实现 | `cross-model` | ✅ 是 |
| **T2 冷读同模型** | 无跨模型能力时：同模型但**严格冷读**（只给工件路径，不给执行者转述/摘要/修复说明），角色剧本 + 全新上下文 | `cold-read`（provisional） | ⚠️ 仅作参考分，不单独定案 |
| **T3 非独立** | 同模型且带着执行者自述上下文评审（自审） | `same-family` | ❌ 禁止作为质量验收 |

- **同家族评审不是功能，是降级**。凡输出质量/正确性判定，必须至少 T2；能 T1 就用 T1。
- 判定分级必须**写入评审记录**（见 review-tracing.md），不许静默缺失。

## 2. 硬规则

1. **冷读**：给评审员的 prompt 只含工件路径（文件/目录/原始结果），**不得**包含执行者的结论、摘要、修复说明、叙事框架。需要解释时用「被审物清单 + 评审问题」格式，解释性内容一律指向文件本身。
2. **全新上下文**：每轮评审用**全新线程/全新子代理**，不得在上一轮评审上下文中续聊（防叙事积累抬高分数）；保留跨轮信息只能通过「工件变化」本身（diff/新文件）。
3. **家族判定**：能确认评审模型家族时才写 `different`；不能确认/同家族 → 按 T3 处理并 fail-closed（宁可 `REVIEW_UNAVAILABLE` 也不假装独立）。
4. **对抗立场**：评审 prompt 必须以「假定作品某处是坏的，找出它」为立场（"Assume the work is broken somewhere — your job is to find where"），要求验证而非礼貌打分；评分 + 判定 + 按严重度排序的弱点 + 每个弱点的**最小修复**。
5. **不传分数历史**：不得把上一轮评分塞给本轮评审（除非做趋势分析且明确标注）。
6. **评审员不得看到执行者内部复盘**（如 progress.json 的 note、执行日志的语气性描述）——只给工件。

## 3. 在 DSH 中的落地

- **T1 实现**：用 `workflow` 工具派发评审子代理，`agent(prompt, { provider: <异族provider>, model: <异族model> })`；若无多模型部署，工具会报错 → 捕获后降级 T2。
- **T2 实现**：用 `subagent`（全新子代理 = 全新上下文）执行评审任务；prompt 只含工件路径 + 评审契约（见下）。
- **R1–R5 五角色的再定位**：五角色保留为「评审内部的角色分工」（同一评审代理内依次扮演 R1..R5 或并行五个评审代理各扮一角），但**评审代理本身必须满足 Tier 1/2**；不再把「执行主模型自扮五角色」当作独立评审。
- **夜间全自动**：默认 T2 起步（subagent 冷读），workflow 多模型可用时自动升 T1；晨报「假设与局限」如实标注所用 Tier。

## 4. 评审 prompt 骨架（T2/T1 通用）

```
[评审轮次 N / 总轮次]
独立评审任务（Tier: {cross-model | cold-read}）。你是资深领域审稿人。
请直接阅读以下工件（路径），不要相信任何转述：
- 主张/草稿: <路径>
- 方法/代码: <路径>
- 原始结果: <路径>（逐字文件，不是摘要）
- 自上一轮的变化: <diff 或新文件路径>（读 diff，别读描述）

立场：假定作品某处是坏的，你的任务是找出它。不要礼貌打分。
输出：
1. 评分 1-10（面向目标场景）
2. 未解决的重大弱点（按严重度排序）
3. 每个弱点的最小修复（实验/分析/重述）
4. 判定: ready | almost | not ready

约束（防过度防御）：
- 只报告真实存在的问题；不要为不存在的风险制造机制。
- 检查范围限于被审工件的真实内容。
```

## 5. 验收与证据

- 评审判定（分数 + verdict）写入 `<工作区>/.dsh-research/traces/<taskId>/round<N>/review.md`（完整 prompt+response，见 review-tracing.md）。
- 质量门 G7/G9 只接受 Tier≥T2 的评审；T3 自审分数不得作为 G7 依据。
- 本轮若 `REVIEW_UNAVAILABLE`（无可用独立评审），质量门记 `blocked-evidence-missing`，晨报列明。

## 6. 借鉴记录

本协议改编自 ARIS（github.com/wanshuiyin/Auto-claude-code-research-in-sleep，MIT License）：
- reviewer-independence.md（执行者≠评审者、冷读、家族判定、REVIEW_UNAVAILABLE fail-closed）
- auto-review-loop 的 REVIEWER_BIAS_GUARD（全新 thread 防分数膨胀）
- research-review 的对抗立场与最小修复要求
