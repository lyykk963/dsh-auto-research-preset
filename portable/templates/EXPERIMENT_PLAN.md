# 实验计划（EXPERIMENT PLAN）— claim-driven 路线图

> 依据 ARIS experiment-plan 的设计（claim → evidence → run order）；不虚构结果——规划证据，绝不宣称证据。

## 1. 问题与方法论点

- Problem（要解决的瓶颈）：
- Method Thesis（方法主张）：
- Date / 运行环境（compute-env 快照）：

## 2. Claim 地图（Claim Map）

| Claim | 为什么重要 | 最低可信证据（Minimum Convincing Evidence） | 关联实验块 |
|-------|-----------|-------------------------------------------|-----------|
| C1（主） |  |  | B1, B2 |
| C2（辅） |  |  | B2 |
| Anti-claim（排除） |  |  | B3 |

## 3. 论文故事线（Paper Storyline）

- Main paper 必须证明：
- Appendix 可支撑：
- Cut（明确不做）：

## 4. 实验块（Experiment Blocks）

每块：Claim tested / 为什么存在 / 数据集-划分-任务 / 对比系统（只留最强基线+消融+变体）/ 指标（决定性在前）/ 配置（骨干、冻训、关键超参、预算、seeds）/ 成功标准 / 失败解读 / 表格-图目标。

| 块 | 优先级（MUST-RUN / NICE-TO-HAVE） | 目标 | 关键配置 | 成功标准 |
|----|--------------------------------|------|---------|---------|
| B1 Main anchor | MUST-RUN | 解决真正瓶颈 |  |  |
| B2 Novelty isolation | MUST-RUN | 主导贡献是否重要 |  |  |
| B3 Simplicity | MUST-RUN | 能否避免更大/更碎版本 |  |  |
| B4 Frontier necessity | 视情况 | 现代组件是否真对 |  |  |
| B5 Failure analysis | NICE-TO-HAVE | 定性诊断 |  |  |

## 5. 运行顺序与里程碑（Run Order and Milestones）

| Milestone | 目标 | Runs | 决策门（stop-go） | 成本 | 风险 |
|-----------|------|------|------------------|------|------|
| M0 Sanity | 数据管线/指标对齐 |  |  |  |  |
| M1 Baseline | 复现最强基线 |  |  |  |  |
| M2 Main | 最终方法主设定 |  |  |  |  |
| M3 Decision | 决定性消融 |  |  |  |  |
| M4 Polish | 鲁棒/定性 |  |  |  |  |

## 6. 计算与数据预算

- 总 GPU 时数/算力：____（估算方法：____）
- 数据准备：____
- 最大瓶颈：____

## 7. 风险与缓解

## 8. 最终清单（Final Checklist）

- [ ] Main paper tables covered
- [ ] Novelty isolated
- [ ] Simplicity defended
- [ ] Frontier justified 或显式不声称
- [ ] must-run 与 nice-to-have 已分离
- [ ] 种子/环境/参数可复现（G5）

## 9. 运行契约（v9，对齐 LMR-Bench 教训——真实运行/环境是最大失败点）

> 执行实验时本契约强制，未满足 = 该 run 不算"跑过"（Beel/AI-Scientist 批评的"绕开验证"在此拦截）。

- [ ] **运行命令留痕**：每个实验记录实际执行命令 + cwd + 环境版本（python/torch/CUDA/依赖），写入 `results/<block>/RUN.md`
- [ ] **哈希留痕**：产物目录生成 `sha256sum results/* > results/HASHES.txt`（图片/JSON/权重/日志全列）
- [ ] **失败留痕**：任何失败必须留 stderr/log 文件（`results/<block>/fail-<ts>.log`），不得口头"试了没成功"
- [ ] **真实运行证明**：claim 引用结果时，能指出对应 `results/` 文件 + 运行时间戳；找不到文件 = claim 无证据（G11 门拒绝）
- [ ] 环境快照：`pip freeze` 或等价锁文件（如可复现要求高时）

