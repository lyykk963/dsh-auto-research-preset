# Claude Code 适配器

本包本身就是 Claude Code 技能格式（`SKILL.md` + 附属目录），无需改写内容。

安装把整个包复制到 `~/.claude/skills/sci-autoresearch/`。
Claude Code 读取 SKILL.md 的 frontmatter `name` + `description` 做触发。

## 为什么这个宿主能「满血」

- **Task 子代理**满足「独立冷读评审」（评审者与被评者上下文隔离）
- 终端里能跑 Python，L3 机检工具全部可用
- 缺的只有：进度面板（无 GUI）、自动续跑（需手动或用 hooks）

## 建议加一条 hook

在 `.claude/settings.json` 的 `hooks` 里挂 Stop 钩子跑 `python tools/selfcheck.py --fast`，
让会话结束前自动体检（见 `hooks-example.json`）。
