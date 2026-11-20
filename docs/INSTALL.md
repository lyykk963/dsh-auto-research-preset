# 安装与排错

## A. DSH 预设（主路径）

### 自动

```powershell
pwsh -File install.ps1
# 自定义位置：
pwsh -File install.ps1 -Target "D:\somewhere\agent-presets\auto-research"
```

脚本行为：目标已存在 → 先整目录备份成 `auto-research.backup-<时间戳>`，再复制 `preset/` 内容；
robocopy 退出码 ≥ 8 才算失败。

### 手动

把仓库里的 `preset/` **整个目录**复制成：

```
%APPDATA%\dsh-desktop\harness\.agent-presets\auto-research\
```

（即该目录下应直接看到 `preset.yml`、`agent.cordis.yml`、`skills/`。）

### 验证安装

1. 重启 DSH Desktop，新建会话；
2. 左侧 Agent 预设下拉中出现 **「自动化科研」**；
3. 选它发一句话，Agent 启动协议第一步应加载 `auto-research` skill 并请你选执行模式；
4. 首次会话会请求授权右下角进度面板（会话级动态插件）。

命令行侧验证：

```powershell
cd "$env:APPDATA\dsh-desktop\harness\.agent-presets\auto-research"
python skills\auto-research\tools\selfcheck.py -v
```

`selfcheck` 正常只输出一行 `SELFCHECK: OK | ...`；`-v` 展开每项（技能层 / 资产层 / 日志层）。

## B. 可移植版（Claude Code / Codex / Trae / Cursor）

见 `portable/INSTALL.md`。要点：

```powershell
pwsh -File portable\adapters\claude-code\install.ps1                    # Claude Code
pwsh -File portable\adapters\codex\install.ps1 -Project "D:\你的项目"   # Codex CLI
pwsh -File portable\adapters\trae\install.ps1                           # Trae
# Cursor：把 portable\adapters\cursor\auto-research.mdc 放到项目 .cursor\rules\
```

## 可选：接上你自己的「融合研究」方法论真身

`preset/skills/fusion-research/SKILL.md` 是**指针技能**：只含真身位置、按需加载索引与红线，不含正文。
真身默认按下面顺序查找：

1. 环境变量 `TRAE_SKILLS_DIR`（指向技能根，如 `D:\my-skills`）；
2. 否则 `%USERPROFILE%\.trae-cn\skills`（Trae 平台技能目录）。

目录不存在时：指针技能仍可加载，Agent 按本预设内流程（`auto-research/SKILL.md` + `contracts/`）执行，
只是少了外部方法论正文与中文科研 PPT 模板库。

## 常见问题

**Q：预设下拉里没有「自动化科研」？**
检查目录层级是否多套了一层（应为 `...\.agent-presets\auto-research\preset.yml`），
再确认 `agent.cordis.yml` 能被 YAML 解析（`!!js` 标签由 DSH 的加载器支持，普通 js-yaml 会报错，属正常）。

**Q：会话起来了但 skill 加载不到？**
DSH 的 skill 名必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（纯 ASCII kebab-case）。中文 `name` 会被**静默丢弃**。
跑 `python skills/auto-research/tools/skill_health.py` 看哪些技能因此失效。

**Q：右下角面板没出现？**
面板是会话级动态插件，需要一次授权；已在运行但看不到时，直接对 Agent 说「重建进度面板」，
它会按 `auto-research/SKILL.md` 的面板维护章节用 `plugin-host.js` / `plugin-client.js` 重新定义并运行。

**Q：`text_gates.py` / `advisor_pattern_gate.py` 报 `SyntaxWarning: invalid escape sequence`？**
历史脚本里有 LaTeX 片段，可用 `python -W ignore::SyntaxWarning` 运行；不影响结论。

**Q：工具脚本报找不到工作区？**
工作区解析顺序：环境变量 `SCI_WORKSPACE` → 当前目录（若含 `.dsh-research/`）→ 当前目录兜底。
显式指定：`set SCI_WORKSPACE=D:\my-project`。
