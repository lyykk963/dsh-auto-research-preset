# 科研大脑（auto-research 参考文档）

> 自 `skills/auto-research/SKILL.md` 外移，2026-10-17。内容未改写，仅搬家。
> 回滚方式：从 `.backup/` 恢复 SKILL.md 即可。

# 15. 科研大脑（v8.2 编排中枢）

> 细则：`contracts/research-brain.md`。定位：把方法论（融合研究）、执行协议（本 skill 六阶段）、能力地图（SKILLS_REGISTRY）与 540+ 执行层 skills 串成自动主循环。

### 15.1 两个持久文件

| 文件 | 记什么 | 用途 |
|------|--------|------|
| `<工作区>/.dsh-research/progress.json` | 进度/阶段/百分比 | 面板、六阶段骨架 |
| `<工作区>/.dsh-research/brain.json` | **研究思考状态**：goal/hypotheses/assumptions/claims(+证据)/decisions/openQuestions/nextAction | 跨会话恢复"上次断在哪、为什么、接下来做什么" |
| `<工作区>/.dsh-research/SKILLS_REGISTRY.md`（+全局 `~/.agents/`） | 513 技能按 12 类「意图→技能」路由 | plan 步选技能，不再靠撞 |

### 15.2 六步主循环（每阶段内部多轮）

```
1. wake    读 brain.json + progress.json + goal；报告"上次断在哪、为什么、接下来做什么"
2. plan    查 SKILLS_REGISTRY.md 选本步技能与路由；写 nextAction + todo
3. execute 用 skill 工具加载选定技能执行；产物落盘；登记证据到 evidence/MANIFEST.md
4. verify  证据门 G11（产物存在+证据齐全）；D2+ 质量门需 Tier≥T2 独立评审；留痕 traces/
5. reflect 更新 brain.json（新假设/claims/决策/openQuestions）；追加 iteration-log.jsonl
6. next    继续下一循环 / 换向（连续 2 轮无新发现，watchdog-contract）/ 交付（全部阶段 done + 晨报）
```

### 15.3 硬规则

1. **wake 必做**：每轮目标轮次开始时先 wake（读 brain.json），不在空转状态上重跑。
2. **plan 必查注册表**：选技能以 `SKILLS_REGISTRY.md` 为准；找不到匹配类目时读对应 SKILL.md 再决定。
3. **brain.json 每轮末更新**：nextAction 是工作指针，必更新；claims/hypotheses 必须带证据路径。
4. **大脑能 DRIVE，不能 ACQUIT**：verify 步的质量验收仍走独立评审（§10/§11），大脑只推进、不自我判"质量达标"。
5. **能力注册表随技能库变化再生成**（新装/更新技能后重扫），保持"大脑记忆"新鲜。

### 15.4 与 light-skills / K-Dense 的关系

- light-skills 自带 13 阶段主线 + `passport.yaml` 状态机 + 机读门（`light-orchestrator` 等 23 技能），
  K-Dense 提供 163 个科研工具技能——二者作为**执行层技能**被大脑的 plan/execute 步调用，不是替代大脑。
- 若任务本身就是一条完整科研主线，可让 `light-orchestrator` 作为执行引擎，本 skill 六阶段与融合研究质量门作为外层总纲。
