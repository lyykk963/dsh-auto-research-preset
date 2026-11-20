# 自动化科研 · Auto-Research Preset

**一个给本硕阶段科研用的「通宵自动执行」Agent 预设：睡前发布课题，早晨拿到可交付的调研/分析/初稿，且每个结论都有落盘证据。**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB.svg)](https://www.python.org/)
[![Host: DeepSeek Harness](https://img.shields.io/badge/Host-DSH%20Desktop-6E56CF.svg)](docs/INSTALL.md)
[![Portable: Claude Code / Codex / Trae](https://img.shields.io/badge/Portable-Claude%20Code%20%7C%20Codex%20%7C%20Trae-2E7D32.svg)](portable/INSTALL.md)

---

## 这是什么

一套把**科研流程**而不是**写作提示词**固化成文件的预设：六阶段流水线（任务解析 → 计划 → 文献调研 → 方法设计 → 执行分析 → 撰写交付）+ 14 份契约 + 20 多个纯标准库的可机检工具。

它是给**本科毕设、硕士课题、组会汇报、开题、小论文**这类"一个人从头做到尾、没人盯着你交付"的场景设计的。白天上课/实习，晚上发布任务，第二天早上读晨报、决定下一步。

两种用法：

| 目录 | 是什么 | 装到哪 |
|---|---|---|
| `preset/` | DSH（DeepSeek Harness）**Agent 预设本体**：`preset.yml` + `agent.cordis.yml` + 自带 skills + 网页右下角进度面板 | DSH Desktop 的预设下拉框，选「自动化科研」 |
| `portable/` | **宿主无关子集**：只要 Skill + 工具就能跑，去掉面板与 goal 绑定 | Claude Code / Codex CLI / Trae / Cursor |

## 适合谁

| 你在做什么 | 它帮你省掉什么 |
|---|---|
| 本科毕设（开题 → 综述 → 实验 → 论文 → 答辩） | 从零搭章节骨架、一篇篇手工总结文献、图表和正文数字对不上 |
| 硕士课题（文献地图 → 方法选型 → 实验矩阵 → 结果分析） | 每次换方向都要重读一遍领域；报告写完不知道哪里会被问倒 |
| 组会 / 开题汇报 | 把论文和结果整理成能讲 15 分钟的 PPT 与讲稿 |
| 小论文投稿 | 投稿前的口径自查（em dash、过度宣称、数字漂移、占位符残留） |

**不适合**：需要实时交互的实验操作、需要人工承担责任的决策（投稿、下单、对外承诺一律要你自己确认）。

## 为什么不用"直接问 AI"

日常问 AI 的失败模式很稳定，本项目的三个机制就是对着这三点做的：

| 常见问题 | 这里的做法 |
|---|---|
| 聊到一半上下文没了，前面白干 | 进度/计划/证据全部落盘在 `<工作区>/.dsh-research/`，重启可续跑 |
| AI 给了个漂亮结论，导师一问出处就翻车 | **证据门**：结论必须绑到 `evidence/MANIFEST.md` 里的文件，无证据不得标 `done` |
| AI 自己给自己打 9 分说"已达到发表水平" | **被评者不得打分**：机检只能 DRIVE（拦已知反模式），ACQUIT 必须由独立评审给 verdict |

## 快速开始

### A. DSH 预设（推荐，带进度面板）

前提：[DSH Desktop](https://github.com/)；Python 3.8+（工具全是标准库）。

```powershell
git clone https://github.com/lyykk963/dsh-auto-research-preset.git
cd dsh-auto-research-preset
pwsh -File install.ps1
```

脚本把 `preset/` 复制到 `%APPDATA%\dsh-desktop\harness\.agent-presets\auto-research\`，已存在会先备份。

然后：重启 DSH → 新建会话 → Agent 预设下拉选 **「自动化科研」** → 首次会话点一次授权右下角面板。

### B. 可移植版（Claude Code / Codex / Trae / Cursor）

```powershell
pwsh -File portable\adapters\claude-code\install.ps1                     # Claude Code
pwsh -File portable\adapters\codex\install.ps1 -Project "D:\我的项目"    # Codex CLI
pwsh -File portable\adapters\trae\install.ps1                            # Trae
```

Cursor 用户把 `portable\adapters\cursor\auto-research.mdc` 放进项目 `.cursor\rules\`。详见 [portable/INSTALL.md](portable/INSTALL.md)。

## 一次完整用法

```text
你：帮我做《多模态检索增强的测试时适应》的文献综述，近三年 40 篇左右，
    要方法对比表和 3 个我能接着做的切入点。

Agent：请先选执行模式（不自动推荐）——
        🌙 夜间全自动 / ⚡ 快速查证 / 🔬 专题半自主 / 📄 发表冲刺 / 💡 灵感风暴 / 🎤 组会材料

你：夜间全自动。

Agent：好的，模式快照已写入进度；建立通宵目标；开始跑文献调研……
```

第二天早上工作区是这样的：

```text
我的课题/
├── MORNING_REPORT.md          # 晨报：做了什么、结论、可信度、今天建议你先看哪 3 处
├── PLAN.md                    # 阶段拆解与时间预算
├── notes/litreview.md         # 文献笔记（含每条引用的出处）
├── results/                   # 图表、对比表、分析产物
├── evidence/MANIFEST.md       # 证据清单：每个结论 → 对应文件/命令
└── .dsh-research/
    ├── progress.json          # 进度 + 模式快照（右下角面板的数据源）
    ├── task.json              # 任务与验收标准
    └── reviews/               # 独立评审记录与留痕
```

常见的三个入口任务：

```text
① 开题/综述   「做 X 领域的文献地图，按近三年前沿/经典奠基/跨领域方法分三层」
② 实验结果   「用 results/exp1.csv 做第 4 章结果分析：配对 t 检验 + BH 多重比较校正，
              给效应量和置信区间，图要能直接进论文」
③ 答辩材料   「把论文和结果整理成 15 分钟答辩 PPT + 逐页讲稿，预判 5 个被问倒的点」
```

## 六个执行模式

发布任务后 Agent 会让你**手动选**一个模式，不自动替你决定：

| 模式 | 四轴档位（L/A/R/T/M/D） | 典型场景 |
|---|---|---|
| 🌙 夜间全自动 | L2/L3 · A4 · Autopilot · T3 · Balanced · 综述+图表+晨报 | 睡前发布，通宵无人值守 |
| ⚡ 快速查证 | L0/L1 · A1 · Co-pilot · T1 · Fidelity · 直接回答 | 几分钟内要一个能引用的结论 |
| 🔬 专题半自主 | L1/L2 · A2 · Co-pilot · T2 · Balanced · 分析报告 | 问题明确、需要中途确认 |
| 📄 发表冲刺 | L2/L3 · A3 · Co-pilot · T3 · Fidelity · 论文草稿 | 已有结果，冲投稿 |
| 💡 灵感风暴 | L0/L1 · A1 · Co-pilot · T1/T2 · Originality · 方向清单 | 找选题、找创新点 |
| 🎤 组会材料 | L1 · A1 · Co-pilot · T1 · Fidelity · PPT/讲稿 | 一周内的汇报 |

轴含义：深度 L / 介入频率 A / 介入角色 R / 时间预算 T / 模式光谱 M / 产出出口 D。

## 三道质量门（也是它最"不像 AI"的地方）

1. **L1 生成时自检**：写每个 section 时对照通用红线（过度宣称、术语与设计不匹配、单次运行当结论）。
2. **L2 投稿前机检**：`advisor_pattern_gate.py` + `text_gates.py` 扫全稿，拦 em dash、TOST 与 non-inferiority 混用、数字口径漂移、caption 过长、占位符残留等。
3. **L3 独立评审**：机检通过 ≠ 可以交。质量判断必须由 Tier≥T2 的独立视角（跨模型或冷读子代理）给出 `ready / almost`。

配套的**证据门**：`evidence_check.py` 要求每个结论都有落盘证据；缺证据只能标 `unverified`，不能标 `done`。

## 仓库结构

```text
.
├── install.ps1                    # 一键装到 .agent-presets（含备份）
├── preset/
│   ├── preset.yml                 # 预设元数据
│   ├── agent.cordis.yml           # 组合：persona + goal + 面板工具 + 自带 skill 目录
│   └── skills/
│       ├── auto-research/         # 执行协议
│       │   ├── SKILL.md
│       │   ├── contracts/ (14)    # 验收门 / 评审独立性 / 证据门 / 写作红线 / PPT 流程 …
│       │   ├── tools/  (21 .py)   # advisor_pattern_gate / text_gates / evidence_check …
│       │   ├── templates/ (9)     # 研究契约 / 实验卡 / 证据清单 / 进度样例
│       │   ├── gates/  (2)        # 论文红线画像模板 / 实验卡片门
│       │   └── plugin-host.js / plugin-client.js   # 右下角进度面板
│       └── fusion-research/       # 方法论主体的指针技能（真身可选，见下）
├── portable/                      # 宿主无关子集（14 契约 / 22 工具 / 4 适配器）
└── docs/
    ├── INSTALL.md                 # 安装与排错
    └── 发布脱敏记录.md             # 公开版相对私人开发版删改了什么
```

## 可选依赖

以下资产**不在仓库里**，缺失时自动降级，不影响主流程：

| 资产 | 默认位置 | 缺失时 |
|---|---|---|
| 「融合研究」方法论真身（44 份 references + 中文科研 PPT 模板库） | `%USERPROFILE%\.trae-cn\skills\融合研究\`，或环境变量 `TRAE_SKILLS_DIR` | 指针技能仍可加载，按本预设内置流程执行；PPT 走 `contracts/ppt-workflow.md` |
| 你自己的论文红牌规则 | 自建 profile JSON | 只跑内置通用反模式规则 |

## 自检

```bash
# 预设资产健康（编码 / JSON / 死链 / 样式 / 体积预算）
python preset/skills/auto-research/tools/selfcheck.py -v

# 机检门自身的正/负控制（确定性，不读外部文件）
python preset/skills/auto-research/tools/advisor_pattern_gate.py --self-test

# 规则清单与来源
python preset/skills/auto-research/tools/advisor_pattern_gate.py --explain

# 可移植版：宿主能力探测 / 轻量体检
python portable/tools/host_check.py
python portable/tools/selfcheck.py --fast
```

工作区路径解析顺序：`SCI_WORKSPACE` → 含 `.dsh-research/` 的当前目录 → 当前目录兜底。

## 常见问题

**面板没出现？** 它是会话级动态插件，需要一次授权；已在运行但看不到时对 Agent 说「重建进度面板」，它用 `plugin-host.js` / `plugin-client.js` 重新定义。

**任务没跑完怎么办？** 晨报会先给「阶段进展 + 次日计划」，目标保持激活，当晚继续。

**这些工具会不会替我编数据？** 不会——工具只做确定性的正则/计数/校验；结论缺证据会被标 `unverified`。**涉及真实下单、收费实验、投稿、对外承诺，只产出方案，必须你确认。**

## 隐私与脱敏

本仓库来自一次真实的私人科研自动化实践，发布前已脱敏：个人绝对路径改占位符或环境变量解析；论文专属红牌规则已移除（只留通用引擎 + 模板）；不含论文原稿、导师/审稿人批注、投稿编号；不含任何密钥。细节见 [docs/发布脱敏记录.md](docs/发布脱敏记录.md)。

## 贡献

Issue / PR 都欢迎。两点约定：

1. **改 `preset/` 记得同步 `portable/`** —— `tools/*.py` 与 `contracts/*.md` 在两边是同一份代码的镜像，只改一边会让两边漂移。
2. **新增规则要能追溯到来源**（`source_round`），不要为了"看起来严格"加无来源的规则；发现误报请修规则语义，而不是放宽阈值。

## 相关项目

- [hanmenxuezidaoshi](https://github.com/lyykk963/hanmenxuezidaoshi) —— 同作者的另一个 DeepSeek Harness 预设 + skill：从现有条件出发的人生决策参谋（个性化早报 / 点子挖掘 / 群体模拟）。

## 许可

[MIT](LICENSE)。

---

<sub>最后更新：2026-11-20 · 预设版本 v1.0.0</sub>
