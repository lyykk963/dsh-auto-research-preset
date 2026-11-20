# 防过度防御契约（HERO）— 约束「建议怎么修」，不约束「能找什么」

> 来源：吸收 ARIS 引用的 HERO 契约（github.com/wanshuiyin/HERO-Anti-OverDefense，MIT）
> 与 auto-review-loop 评审 prompt 内嵌的 Scope Limits 块。适配 DSH 预设的 agent instructions 与评审 prompt。

## 0. 问题

长上下文 agent 在「找问题 → 提议修复」时容易**过度防御**（overdefense）：为不存在的风险制造机制，
把简单判断机械化、对边界情况着迷。ARIS 把它压缩成四种形状（约 550 token，可粘进 agent instructions）：

## 1. 四形状（H-E-R-O）

| 形状 | 含义 | 反制 |
|:--|:--|:--|
| **H — Hashing（哈希上瘾）** | 动不动建议加哈希/指纹/摘要绑定来"防篡改" | 除非证据表明当前代码确有此类缺陷，否则不提 |
| **E — Edge cases（边界情况）** | 对 exotic 编码、符号链接竞态、RTL 文本、毫秒级竞态着迷 | 除非能展示该 case 在此项目真实出现，否则 out of scope |
| **R — Rubrics（把判断换成机械）** | 把需要判断力的一句话换成没人维护的评分表 | 人类能读懂的一句话 > 无人维护的打分表 |
| **O — Overbuild（过度建设）** | 加 feature flag、迁移框架、兼容层、包装器、pin | 除非有当前仓库缺陷/不变式作为证据 |

## 2. 适用范围

- **约束的是 agent 提议怎么修**，不是它**能找什么**：发现真实问题（包括罕见但真实出现的问题）永远欢迎。
- 例外（信任边界）：代码若会运行远程命令、启动网络服务、安装 MCP server，则在这些面上的严格审查**在范围内**。
- 评审 prompt 里嵌入 Scope Limits 块（见 reviewer-independence.md §4 的约束段），要求评审「先找真问题，再控制修复范围；说清楚什么是对的，不要制造发现」。

## 3. 借鉴记录

改编自 ARIS 引用的 HERO 契约与 auto-review-loop 的 Scope Limits（MIT）。
