# 工件契约与模板（auto-research 参考文档）

> 自 `skills/auto-research/SKILL.md` 外移，2026-10-17。内容未改写，仅搬家。
> 回滚方式：从 `.backup/` 恢复 SKILL.md 即可。

# 13. 工件契约与模板（v8.1，吸收 ARIS）

> 细则：`contracts/output-manifest.md`、`contracts/citation-discipline.md`、`contracts/hero.md`。

- **产物清单**：产物超过 15 个工件时维护 `MANIFEST.md`；高价值中间产物先写时间戳文件再复制到固定名（防覆盖）；「来源 → 并入目标」关系登记（组合模式保留来源）。
- **引用纪律**：主张必带出处；检索后先核验存在性再写作引用；网络瞬时失败标 `verify_pending` 不删除；LLM 生成 BibTeX 禁止；D5 交付前引用审计（KEEP/FIX/REPLACE/REMOVE）。
- **防过度防御（HERO）**：建议修复时受 H（哈希）/E（边界）/R（机械评分表）/O（过度建设）四形状约束；约束「怎么修」，不约束「能找什么」。
- **模板**：`templates/RESEARCH_CONTRACT.md`（任务契约）、`templates/EXPERIMENT_PLAN.md`（claim 驱动实验计划）、`templates/FINDINGS.md`（发现记录）、`templates/EVIDENCE_MANIFEST.md`（证据清单）、`templates/RESEARCH_MEMORY.md`（研究记忆台账）、`templates/CHECKPOINT.md`（阶段内过程检查点，v9）——需要时加载对应模板。
- **研究记忆（跨任务沉淀）**：`.dsh-research/memory/`（claims/ideas/experiments/papers 四台账，追加式）；失败 idea 成为防重复记忆，≥3 个失败触发重新构思提醒。见 `contracts/research-memory.md`。
- **元优化（自优化闭环）**：`.dsh-research/meta/events.jsonl` 被动日志（skill 调用/工具失败/门触发/空转轮）；任务完成后 ≤15 分钟 meta 复盘 → ≤3 条改进建议 → 独立评审 → 批准落地。见 `contracts/meta-optimize.md`。
- **证据审计工具**：`tools/evidence_check.py`（纯标准库）——确定性 4 态检查（verified / value_not_found / path_missing / unparseable），幻觉证据在花评审调用前被机械拒绝，支撑 G11 证据门：
  `python tools/evidence_check.py <root> --batch claims.json`（exit 1 = 存在幻觉证据）。
- **阶段产物清单门（v9）**：`tools/stage_gate.py`（纯标准库）——每阶段收尾对产物目录跑确定性清单检查（文件存在/非空/JSON 可 parse/图片可解码/正则命中），未过则阶段不得标 done；清单声明用 gate.json，见工具 docstring。`python tools/stage_gate.py <产物根> --manifest gate.json --report stage_gate_report.md`。

**v9.2 新增（迁自融合研究 v8.1，只迁可执行的判据与工具，不迁方法论正文）：**

- **文献检索（防幻觉）**：`tools/find_papers.py`（纯标准库，无需 key）——多源检索 openalex / crossref / semanticscholar / arxiv / pubmed。
  `python tools/find_papers.py -q "<关键词>" --sources openalex,crossref --json`。
  **exit 码约定**：`0` = 全部来源成功（即使 0 条，那是"问了，没有"）；**`2` = 有来源不可达**（"没能问出去"）——
  ⚠️ 此约定为本预设修复：原实现把"来源不可达"静默折叠成"0 条结果且 exit 0"，对防幻觉工具而言会把「没搜到」误读成「不存在相关研究」。
  实测（2026-10-17 更新）：`export.arxiv.org` 曾持续返回 **HTTP 429**；改用 `tools/fetch.py` 的**退避重试 + 限速**后已可正常取到（同日 probe：arXiv API = ok）。**旧结论"arXiv 在本机不可用"作废**。若再次 429，先用 `python tools/fetch.py probe` 判源健康，再决定是否降级为"该源不可用"，不得据此断言"无相关工作"。
- **引用核验**：`tools/verify_citations.py`（纯标准库）——单条 DOI/标题/年份/作者核验 + 批量 refs JSON + BibTeX。补上 v9 升级案遗留的 **B4「引用三轴审计工具化」**。
  `python tools/verify_citations.py --doi 10.xxxx/yyyy --json`。
- **图表顾问**：`tools/generate_figure.py`（纯标准库）——CSV 剖析 → 图型推荐 → 风格（nature/science/ieee/poster）/调色板 → QA → 期刊 checklist。
  配套样式文件 `tools/styles/{nature,science,publication}.mplstyle`（发表级 matplotlib 样式，零依赖）。
- **文本质量门 G1/G3**：`tools/text_gates.py`（纯标准库）——G1 六维（AI 高频词密度 / 标点多样性 / 段落节奏 / 句长变异系数 / 连接词多样性 / 开篇冗余）+ G3 过度声明词与引用时效性。
  `python tools/text_gates.py <草稿> [--bib refs.bib] [--strict]`（exit 1 = Critical 未过，不得进入下一阶段）。
  **已裁决阈值冲突**：G1 AI 高频词密度取 **3 处/千词**（原文件总览表写 5、明细表写 3）；详见 `contracts/acceptance-gate.md` §6.4。
- **技能层健康检查**：`tools/skill_health.py`（纯标准库）——扫描技能根目录，报出 `name` 不合规（非 ASCII kebab-case）因而被 DSH **静默丢弃**的技能；并可选校验 PPT 模板索引漂移。
  `python tools/skill_health.py [--ppt-index assets/ppt-templates.index.json]`。
  ⚠️ **启动协议建议执行一次**：本机实测 **14 个技能**因此不可加载。**截至 2026-10-17 已全部处置**：
  `senior-computer-vision`（frontmatter 缺 name + 假 junction）已重建为真 Junction；其余 **13 个真身 `name` 一律未动**
  （Trae 的 `~/.trae-cn/skill-config.json` 以 `name` 作 `managedSkills` 的键，改名会打断 Trae 侧调用），
  改建 **12 个 ASCII 指针技能**（`~/.agents/skills/<ascii-name>/`）+ 预设内置 `fusion-research` 指针。
  脚本 v9.2 起按路径**动态识别代偿**：不合规项照常列出供审计，但**待修 0 时 exit 0**（否则真身永远中文、脚本永远报红，报警就废了）。
  批量工具（幂等）：`<工作区>/tools/install_ascii_skill_pointers.py`。文件缺失即故障不可见。
- **自检总入口（v9.2 新增）**：`tools/selfcheck.py` —— 一条命令跑「技能层（`skill_health.py`）+ 资产层（`audit_preset_assets.py`）」，正常只输出一行 `SELFCHECK: OK | skills=… | assets=…`，**只有 fail 才展开**；`--fast` 只跑技能层（约 1.9 s，全量约 2.6 s）。
  资产层检查 py/json/md 可解析、SKILL.md 交叉引用无死链、`.mplstyle` 能 apply **且声明的颜色数真的生效**（matplotlib 会把 `#` 之后当注释 → 十六进制色值必须写成 RGB 元组）、主 SKILL.md 体积预算。**预算超支只算 warn 不阻断**——永远报红的报警等于没有报警。
- **实验卡片门**：`templates/experiment_card.template.json`（迁自 `reproducibility-protocol.md`：seed_map / hardware / data.sha256 / code.commit / R1–R4 等级）
  + `gates/experiment_card.gate.json`（execute 阶段 Type-A 门：卡片可 parse、关键字段正则命中、HASHES.txt 含 sha256、run.log 非空）。
  落点 `<工作区>/.dsh-research/evidence/execute/`；补强 v9 `execute` 阶段原先最薄的证据链。
- **PPT 工作流契约**：`contracts/ppt-workflow.md`——中文科研场景的「场景 → 配色 → 字体 → 布局」四步强制询问、15 行字体总表、4 种布局模式、9 行默认推荐；模板以 `assets/ppt-templates.index.json`（15 套 / 591.7 MB，含 sha256）**索引引用而非复制**。执行仍走本预设 PPTD 管线（`pptd_import` → 编辑 → `pptd_check` → `pptd_render`），**不得另起生成链路**。
- **交付出口 → 质量门子集**：`contracts/acceptance-gate.md` §6（D0–D7 映射 + 命名模式对齐 + 微调硬约束三条 + 自评红线）。
- **方法论主体入口**：`skills/fusion-research`（指针技能）——只含真身路径、按需加载索引与红线；方法论正文仍在 Trae 侧 `%USERPROFILE%\.trae-cn\skills\融合研究\`。

**论文写作门（v9.3 新增；规则来自一次真实论文的多轮审稿意见，已脱敏）：**

- **写作红线契约**：`contracts/writing-red-lines.md`——把「审稿人点过的问题」变成可事先执行的动作。
  三层机制（生成时自检 → 投稿前机检 → Tier≥T2 独立评审）；**37 条通用红线**（措辞立场 / 口径守恒 /
  叙事口径 / 结构篇幅 / 图表自明性 / 合规伦理）+ profile 外置「本项目特有」规则 + 规则维护流程
  （每条新意见 → 一条规则 → `source_round` 留痕）+ 意见数据结构规范（`rounds-<n>.jsonl`）。
  **触发时机**：任何论文写作/修改/投稿任务，`write` 阶段收尾必读。
- **审稿意见模式机检门**：`tools/advisor_pattern_gate.py`（纯标准库，v1.4+ 公开版）——扫 tex/md 自动拦下
  「审稿人点过 / 期刊官方点过」的反模式：em dash、TOST 与 non-inferiority 冲突、`privacy-friendly`
  等不可证的卖点词、口径漂移（数值/seed 数）、旧数值残留、被推翻的旧叙事短语、caption/小节过长、
  孤儿图/表 label、句长与填充语、高亮与摘要合规、残留占位符。
  `python tools/advisor_pattern_gate.py <稿...> [--profile p.json] [--strict] [--json]`；
  `--self-test` 跑内置正/负控制；`--explain` 打印规则清单与来源轮次；`--emit-profile` 导出合并后 profile。
  **与 `text_gates.py` 分工**：后者管通用写作质量（G1/G3），本工具管「被具体提过的模式」。
- **profile（规则外置）**：`gates/paper_redline_profile.template.json`（复制成自己的 profile 后 `--profile` 传入）。
  **换论文只换 profile，不改引擎**；内置规则只保留通用反模式。
- **经验结论**：论文类任务的主要失败源是**流程缺失**而非能力不足——把每条意见落成一条能自动跑的检查，
  比「下次注意」有效得多（原始稿件、导师批注与个案统计不随包分发）。
