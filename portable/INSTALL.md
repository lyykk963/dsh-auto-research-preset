# 安装：把科研自动化搬到别的 AI

本包**自身就是一个技能**（`SKILL.md` + `references/` + `contracts/` + `tools/`），
另外提供三种宿主适配器。

## 通用前提

- Python 3.8+（工具全是标准库，无需 pip 安装）
- 一个工作目录，里面会生成 `.dsh-research/`（进度、证据、评审记录都落这里）
- 可选：`SCI_WORKSPACE` 环境变量指向工作区（不设则用当前目录）

## Claude Code

```powershell
# 装成用户级技能
pwsh adapters/claude-code/install.ps1
# 或手动：把整个目录复制到 ~/.claude/skills/sci-autoresearch/
```

装好后在会话里说「用科研自动化模式做 X」，或直接 `/sci-autoresearch`（若配了命令）。
**子代理评审可用** → 质量门可以走 ACQUIT。

## Codex CLI

```powershell
pwsh adapters/codex/install.ps1 -Project "D:\你的项目"
```

它会把一段 `AGENTS.md` 追加到项目根（Codex 自动读取），并提示技能目录位置。
**独立评审**：让 Codex 用 `codex exec` 起一个干净子进程复算，等价于冷读。

## Trae

```powershell
pwsh adapters/trae/install.ps1
```

复制到 `~/.trae-cn/skills/sci-autoresearch/`（ASCII 名，避开 Trae 对中文 name 的 key 依赖）。

## Cursor（可选）

把 `adapters/cursor/auto-research.mdc` 复制到项目的 `.cursor/rules/`。

## 装完自检

```bash
python tools/host_check.py        # 报告：识别到的宿主、可用能力、降级项
python tools/selfcheck.py --fast  # 技能层 + 资产层健康检查
```

## 第一次跑通（建议顺序）

1. `python tools/host_check.py` → 确认 L3 工具可用
2. 建工作区：`mkdir <工作区>/.dsh-research`
3. 把 `templates/progress.example.json` 复制成 `progress.json`，改 taskId
4. 按 `SKILL.md` 六阶段跑一个小任务（例如"查证 3 篇论文的引用是否真实"）
5. 收尾跑 `tools/check_claims.py` / `tools/check_delivery.py`

## 与 DSH 预设的关系

本包是 DSH 预设 `auto-research` 的**宿主无关子集**：
去掉了 Cordis 进度面板与 `create_goal` 绑定，保留了全部方法论、契约与机检工具。
两边工具代码保持同步（路径已改为可配置，同一份代码两处都能跑）。
## 一个已知的宿主差异（别被误导）

`tools/selfcheck.py` 的 **skills 层**是按 DSH 的技能加载规则写的（扫 `~/.agents/skills`
与 `~/.trae-cn/skills` 的 junction，检查 frontmatter `name` 是否 ASCII）。
在 Claude Code / Codex 上它**仍会跑但不代表你那边的技能健康度**。

- 日常自检建议只用：`python tools/selfcheck.py --fast`（assets 层跳过，不依赖 DSH 路径）
- 或只看 logs 层（工作区 `.dsh-research` 下的 JSON/JSONL 编码与合法性）