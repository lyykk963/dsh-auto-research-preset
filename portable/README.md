# 科研自动化（可移植版）

把「自动化科研」这套工作法搬到任何能读文件、能跑 Python 的 AI 宿主上。

**不是**又一个论文写作提示词，而是：
- 六阶段流水线（intake → plan → litreview → method → execute → write）
- 13 份契约（验收门 / 引用纪律 / 评审独立性 / 评审留痕 / 写作红线 / PPT / 幻灯片设计…）
- **可机检**的质量工具（纯标准库）：数字声明重算、口径预注册、交付完整性、幻灯片体检、取数快照
- 一条硬红线：**被评者不得打分**，机检只能 DRIVE，ACQUIT 必须独立评审

## 三条路径

| 你想 | 做什么 |
|---|---|
| 在 **Claude Code** 用 | `powershell -File adapters/claude-code/install.ps1` |
| 在 **Codex CLI** 用 | `powershell -File adapters/codex/install.ps1 -Project <你的项目>` |
| 在 **Trae** 用 | `powershell -File adapters/trae/install.ps1` |
| 先看看能干什么 | 读 `SKILL.md` 与 `CAPABILITY-MATRIX.md` |

## 30 秒自检

```bash
python tools/host_check.py        # 我是谁、四层能力剩多少、哪些降级
python tools/selfcheck.py --fast  # 轻量体检
```

## 目录

```
SKILL.md                 主协议（宿主无关；DSH 专属部分已剥离）
CAPABILITY-MATRIX.md     宿主能力对照：搬到哪还剩多少「满血」
INSTALL.md               逐宿主安装步骤
contracts/ (14)          验收门、引用纪律、评审独立性、评审留痕、写作红线、PPT…
references/ (4)          产物契约、ARIS 集成、科研大脑、技能情报
templates/ (9)           进度/证据清单/实验卡/研究契约等模板
gates/ (2)               论文红线画像模板、实验卡片门
tools/ (22)              claims / prereg / delivery / fetch / claimlog / check_deck / stage_gate / selfcheck / host_check …
adapters/                claude-code / codex / trae / cursor
docs/PLUGIN-DSH.md       DSH 专属的进度面板说明（可选）
```

## 已知边界

- 进度面板只有 DSH 有；其他宿主用「进度文件 + PLAN.md」等价替代
- 无独立子代理的宿主上，质量门降级为 DRIVE-only，交付里必须写明
- `selfcheck` 的 skills 层是 DSH 规则，跨宿主时用 `--fast`