# ARIS 借鉴记录（auto-research 参考文档）

> 自 `skills/auto-research/SKILL.md` 外移，2026-10-17。内容未改写，仅搬家。
> 回滚方式：从 `.backup/` 恢复 SKILL.md 即可。

# 14. ARIS 借鉴记录（v8.1）

本预设 v8.1 的跨模型评审、证据门、验收门、评审留痕、无人值守契约、工件契约、防过度防御机制，改编自上海交大 ARIS 项目
（github.com/wanshuiyin/Auto-claude-code-research-in-sleep，MIT License，15k★，两篇论文被 AI 顶会收录）：
reviewer-independence / acceptance-gate / evidence-precheck / review-tracing / external-cadence / assurance-contract /
output-manifest / output-versioning / output-composition / citation-discipline / fan-out-pattern / effort-contract /
watchdog.py / iteration_log.py / auto-review-loop（停止条件与 REVIEWER_BIAS_GUARD）/ research-refine / experiment-plan 等。
逆向工程笔记存于 `<工作区>/reference/aris-notes/`（01 评审循环 / 02 实验 / 03 选题元优化 / 04 契约模板 / 05 现状地图），
差距分析见 `<工作区>/notes/gap-analysis.md`。融合研究侧的对应升级见其 SKILL.md 与 `references/aris-integration.md`。
