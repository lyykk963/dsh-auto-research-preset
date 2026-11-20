#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
advisor_pattern_gate.py — 论文「审稿意见模式」投稿前机检门（v1.4 / 公开版）

来源：把一篇真实论文的多轮导师/审稿意见逐条沉淀成可机检规则的做法。
      **本公开版已移除论文专属规则**（具体禁用词、口径数值、旧叙事短语），只保留
      任何论文都适用的通用反模式；论文专属部分请复制 gates/paper_redline_profile.template.json
      成自己的 profile，用 --profile 传入。

精度调优记录（当年在真实已投稿稿件上发现的误报，均已修；经验可复用）：
  v1.0→v1.1  F-ORPHAN-LABEL 只对 fig:/tab: label 报警（sec:/eq: 本就允许不被引用；实测误报 39 条）
  v1.0→v1.1  句子级检查跳过 tabular/align/作者元数据（实测把表行与单位信息当成 41 条超长句误报）
  v1.0→v1.1  数值口径窗口 ±160 → ±45 且不得跨空行（实测把无关页码当成层数口径，误报为 Critical）
  v1.1→v1.2  同规则命中过多时折叠（cap=5 + 汇总行），避免 40 条超长句淹没 1 条 em dash
  v1.2→v1.3  新增 8 条通用规则（题名一致性 / 正文出现框架 API / 括号旁白过长 / 同句重复 5-gram /
             散文分号密度 / 孤标题 / caption 实现口吻）。全部零判断·纯正则与计数、全部不设 Critical。
             规则 id 与阈值集中在 GENERIC_RULES_V13 / GENERIC_V13_DEFAULTS，可用 profile 的
             generic_v13 键覆盖阈值（不改引擎）。
  v1.2→v1.3  【修误报·新规则专用预处理】新规则的散文文本额外剥离绘图·代码·参考文献环境
             （tikzpicture/axis/verbatim/lstlisting/thebibliography …）与低层排版命令的实参：
             \setlength{\textfloatsep}{9pt plus 2pt minus 2pt} 这类 TeX 胶水参数会被当成散文，
             使「同句重复 5-gram」在真实终稿上误报 1 条（实测定位后修）。
             旧规则的预处理路径与 v1.2 逐字不变（新参数默认值 = 原行为）。
  v1.2→v1.3  【修误报·豁免条件】X-TITLE-MISMATCH 豁免「封面/补充材料题名 ⊇ 正文题名」的写法。
             理由：正文与补充材料合跑时，补充材料封面题名是
             「\vspace{…}Supplementary Material\\[4pt] + 正文题名」，两层本就允许不同；
             逐字比对会误报题名不一致（实测定位 1 条后加包含关系豁免，阈值未放宽）。
             同句重复 5-gram 另加两条反假象守卫：$…$ 占位符 MATH 不参与分词、
             重复 gram 须含 ≥3 个不同词（防 "pt plus pt minus pt" 这类残渣）。
  v1.3→v1.4  公开发布：内置 profile 去论文专属化（通用引擎 + 外置 profile）。

定位：**Type-A（机器可判）确定性门**。只判「是否触发了已知的、审稿人点过的反模式」，
      **不判**「论文写得好不好」——质量验收仍归 Tier≥T2 独立评审
      （见 contracts/reviewer-independence.md、contracts/acceptance-gate.md §0.5）。
      能判 DRIVE，不能 ACQUIT。

与既有工具的分工（不要互相重复，也不要用本工具替代它们）：

  text_gates.py            G1/G3 通用写作质量：AI 高频词密度、标点多样性、段落节奏、
                           句长变异系数、连接词多样性、开篇冗余、过度声明词、引用时效性
  advisor_pattern_gate.py  ← 本工具。**审稿人点过 / 期刊官方点过**的模式：
                           口径守恒、术语一致性、叙事口径、图表自明性、合规包装、残留物
  evidence_check.py        G11 证据门：主张是否有落盘证据
  verify_citations.py      引用核验（DOI/标题/年份/作者）
  stage_gate.py            阶段产物清单门

设计要点：**引擎通用，规则 profile 化**。换一篇论文只换 profile，不改脚本。

用法：
  python advisor_pattern_gate.py <文件...> [--profile p.json] [--json] [--strict]
  python advisor_pattern_gate.py --self-test        # 内置正/负控制自测（确定性，不读外部文件）
  python advisor_pattern_gate.py --explain          # 打印规则清单 + 来源轮次（人读）
  python advisor_pattern_gate.py <文件...> --emit-profile out.json   # 导出合并后的 profile

exit 0 = 无 Critical 失败
exit 1 = 有 Critical 失败（或 --strict 下存在任意失败）
exit 2 = 用法错误 / 文件不可读（fail-closed，不得当作通过）

纯标准库（Python 3.8+）。
"""
import argparse
import json
import os
import re
import sys

VERSION = "1.4"

# ══════════════════════════════════════════════════════════════════════════
# 0. 严重度与退出码语义
# ══════════════════════════════════════════════════════════════════════════
# Critical : 导师已明确否过的立场/术语/口径；出现即不得投稿 → exit 1
# Major    : 大概率会被再次提出的问题；须修或在「局限」中列明 → exit 1 (--strict)
# Minor    : 提示性；不阻塞

SEV_ORDER = {"Critical": 0, "Major": 1, "Minor": 2}


# ══════════════════════════════════════════════════════════════════════════
# 1. 内置默认 profile
#    逐条来自真实导师意见（source_round 标注轮次），不是凭空的"写作建议"。
# ══════════════════════════════════════════════════════════════════════════

BUILTIN_PROFILE = {
    "profile_name": "builtin-generic",
    "profile_note": "内置通用规则集：只保留与领域无关的反模式（em dash、统计术语混用、"
                    "超范围卖点词、单次运行结论、残留占位符）+ 常见期刊的官方投稿要求。"
                    "论文专属规则（禁用词、口径数值、旧叙事短语）请复制 "
                    "gates/paper_redline_profile.template.json 改成自己的 profile，用 --profile 传入，"
                    "不要直接改引擎。",

    # ── 1.1 禁用词 / 措辞红线 ──────────────────────────────────────────
    "banned_terms": [
        {"id": "B-EMDASH",
         "pattern": r"---|\u2014",
         "severity": "Critical",
         "reason": "em dash 全文禁用（含补充材料）。数字区间请用 --（两个连字符）。",
         "source_round": "R4"},

        {"id": "B-TOST-NONINF",
         "pattern": r"\bnon-?inferior(?:ity)?\b|非劣效?",
         "severity": "Critical",
         "reason": "双侧 TOST 检验的是 equivalence，不是 non-inferiority。"
                   "若确有单侧非劣效设计，须在文中写明单侧并改用本规则的豁免。",
         "source_round": "R2/R3",
         "when_any": [r"\bTOST\b", r"two\s+one-?sided", r"\bequivalen"]},

        {"id": "B-PRIVACY-FRIENDLY",
         "pattern": r"privacy[-\s]friendly",
         "severity": "Major",
         "reason": "不得写 privacy-friendly → 改成「在隐私、存储或部署约束下更适用」。",
         "source_round": "R1"},

        {"id": "B-GRADIENT-FREE-SCOPE",
         "pattern": r"\bgradient[-\s]free\b",
         "severity": "Major",
         "reason": "gradient-free 只能指流程中的某一步，不得泛指整个方法。"
                   "（本规则只能提示出现位置，范围是否越界需人检。）",
         "source_round": "R1"},

        {"id": "B-SINGLE-SEED-CLAIM",
         "pattern": r"(?:a\s+)?single\s+(?:seed|run)\s+(?:shows?|indicates?|demonstrates?|suggests?)",
         "severity": "Major",
         "reason": "单次运行 / 单个 seed 的观测不得写成结论；须说明 seed 数与统计口径。",
         "source_round": "R1–R4"},
    ],

    # ── 1.2 数值 / 口径守恒（跨文件）    # ── 1.2 数值 / 口径守恒（跨文件） ──────────────────────────────────
    # 论文专属：由 --profile 提供。结构见 gates/paper_redline_profile.template.json：
    #   {"id","name","forbidden_pattern","require_context","exempt_if","severity","reason","source_round"}
    "numeric_invariants": [],

    # ── 1.3 叙事口径一致性（跨文件） ───────────────────────────────────
    # 论文专属：由 --profile 提供（forbidden_phrases / canonical_claims）。
    "narrative": {"forbidden_phrases": [], "canonical_claims": []},

    # ── 1.4 写作规范 ─────────────────────────────────────────────────
    "style": {
        "max_sentence_words": 30,
        "sentence_words_severity": "Major",
        "caption_max_chars": 400,
        "caption_severity": "Minor",
        "section_max_words": 1600,
        "section_severity": "Major",
        "filler_openers": ["notably", "importantly", "in other words", "overall",
                           "additionally", "moreover", "furthermore", "in addition"],
        "filler_severity": "Minor",
        "filler_consecutive_limit": 3,
        "spelling": {
            "us": ["behavior", "labeled", "normalize", "analyze", "modeling", "generalization",
                   "characterize", "minimize", "maximize", "color"],
            "uk": ["behaviour", "labelled", "normalise", "analyse", "modelling", "generalisation",
                   "characterise", "minimise", "maximise", "colour"],
            "severity": "Major",
        },
    },

    # ── 1.5 合规包装（Elsevier / PR 投稿阶段） ────────────────────────
    "compliance": {
        "highlights": {"min": 3, "max": 5, "max_chars_each": 85, "severity": "Critical"},
        "abstract_max_words": 250,
        "abstract_no_citation": True,
        "abstract_severity": "Critical",
    },

    # ── 1.6 残留物 ───────────────────────────────────────────────────
    "residue": {
        "patterns": [
            {"id": "RES-TODO", "pattern": r"\b(?:TODO|FIXME|XXX|TBD|PLACEHOLDER)\b",
             "severity": "Critical", "reason": "投稿前不得残留占位符。", "source_round": "R4"},
            {"id": "RES-CN-LEFTOVER", "pattern": r"待补|待定|占位|待确认|草稿",
             "severity": "Critical", "reason": "中文残留在英文稿中。", "source_round": "R4"},
        ],
    },

    # ── 1.7 声明豁免（避免误报） ─────────────────────────────────────
    "ignore_line_contains": ["advisor_pattern_gate", "text_gates"],
}

# ══════════════════════════════════════════════════════════════════════════
# 1.8 v1.3 通用规则（引擎内置逻辑，与项目无关；项目特有规则仍放 BUILTIN_PROFILE）
#     来源：导师第 4 轮的 7 类意见。全部「零判断」——纯正则/计数，不做语义判断，
#     因此规则 id、严重度与阈值都集中在这两个常量里，explain() 与 self_test() 同源，
#     不会出现「自测里有一条、explain 里没有」的漂移。
#     严重度约定：会误导读者 → Major；纯风格 → Minor；本批一律不设 Critical。
# ══════════════════════════════════════════════════════════════════════════

GENERIC_V13_DEFAULTS = {
    "max_paren_words": 40,            # 括号内 > 40 个英文词 = 括号里塞整段旁白
    "semicolon_sentence_words": 35,   # 含 ';' 且句长 > 35 词
    "semicolon_per_1000_units": 5.0,  # 全篇散文 ';' 密度上限（每 1000 计数单位）
    "min_sentence_words_5gram": 8,    # 短于 8 词的句子不判同句重复
    "ngram_size": 5,                  # 同句重复的 n-gram 阶数
    "min_distinct_tokens": 3,         # 重复 gram 至少含 3 个不同词（反残渣假象）
    "min_title_words": 3,             # 少于 3 个英文词的 \title 不参与题名一致性比对
}

GENERIC_RULES_V13 = [
    {"id": "X-TITLE-MISMATCH", "family": "一致性", "severity": "Major", "source_round": "R4",
     "reason": "同一份投稿的题名必须逐字一致（导师第 4 轮：多处题名要一致）。"
               "语料里 \\title{} 出现 ≥2 个互不相同的版本 = 有旧题名残留。"
               "豁免：封面/补充材料题名「包含」正文题名的写法（含 \\\\ 换行或 Supplementary 前缀）。"},

    {"id": "X-PROSE-API", "family": "正文纯度", "severity": "Major", "source_round": "R4",
     "reason": "论文正文不应出现框架/代码 API 符号（导师第 4 轮）。"
               "若确为正文引用 API，请包进 \\texttt{} 或删除。"
               "已排除 code/verbatim 环境与 \\texttt{}/\\verb/\\lstinline/\\url 内的用法。"},

    {"id": "X-PAREN-LONG", "family": "写作规范", "severity": "Minor", "source_round": "R4",
     "reason": "括号里塞整段旁白（>40 个英文词）应拆成独立句（导师第 4 轮 R4-06/07）。"},

    {"id": "X-REPEAT-5GRAM", "family": "写作规范", "severity": "Major", "source_round": "R4",
     "reason": "同一句内出现重复的 5-gram = 复制粘贴残留/同句重复（导师第 4 轮 R4-14/16/29）。"},

    {"id": "X-SEMI-LONGSENT", "family": "写作规范", "severity": "Minor", "source_round": "R4",
     "reason": "分号只该连接两个关系紧密的子句；长句（>35 词）里再出现分号，"
               "说明多个主命题被挤进一句（导师第 4 轮）。"},

    {"id": "X-SEMI-DENSITY", "family": "写作规范", "severity": "Minor", "source_round": "R4",
     "reason": "全篇散文分号密度过高（>5 处/1000 计数单位）= 分号滥用（导师第 4 轮）。"},

    {"id": "X-ORPHAN-HEADING", "family": "结构", "severity": "Minor", "source_round": "R4",
     "reason": "\\section/\\subsection 之后紧跟 figure/table（中间只有空白·注释）= 标题正下方"
               "直接放浮动体，排版难看且缺引导文字（导师第 4 轮 R4-26）。"},

    {"id": "X-CAPTION-IMPL", "family": "图表自明性", "severity": "Minor", "source_round": "R4",
     "reason": "caption 里出现「脚本/实现」口吻（the same script / keeps every fourth layer / "
               "in our implementation …）：表注图注应写读者需要的信息，不写实现细节（导师第 4 轮 R4-25）。"},
]

_G13_BY_ID = dict((r["id"], r) for r in GENERIC_RULES_V13)
GENERIC_V13_IDS = [r["id"] for r in GENERIC_RULES_V13]

# 正文出现框架 API：要求前一个字符不是词字符（防 inp./group. 之类误命中），
# 且点号后紧跟字母或下划线（"tf." 结尾的句号、"np. " 之类不算）。
API_IN_PROSE_PATTERN = r"(?<![A-Za-z0-9_])(?:torch|np|numpy|cv2|tf)\.[A-Za-z_]"
API_IN_PROSE_RE = re.compile(API_IN_PROSE_PATTERN)

# caption 里的「实现细节」措辞（小列表常量，刻意收紧，避免误报）
CAPTION_IMPL_PHRASES = [
    r"produced by the same script",
    r"generated by the same script",
    r"built by the same script",
    r"\bthe same script\b",
    r"keeps? every fourth layer",
    r"every fourth layer is (?:kept|retained|frozen)",
    r"\bin (?:our|the) (?:implementation|script|code)\b",
    r"\bwe (?:ran|run|used|wrote) (?:our|the) script\b",
]

# v1.3 新规则的散文预处理：额外剥离的环境（绘图 / 代码 / 参考文献 / 附录骨架）
NON_PROSE_ENVS_V13 = ["tikzpicture", "pgfpicture", "pgfplots", "axis", "scope",
                      "lstlisting", "minted", "Verbatim", "verbatim*", "comment",
                      "filecontents", "thebibliography", "biblist"]

# v1.3 新规则的散文预处理：剥离「低层排版命令」的实参。
# 这些命令的实参是长度/胶水/字体规格，不是散文；不剥会制造假象 n-gram
# （实测：\setlength{\textfloatsep}{9pt plus 2pt minus 2pt}）。
LOWLEVEL_LAYOUT_COMMANDS = ["setlength", "addtolength", "setcounter", "addtocounter",
                            "fontsize", "linespread", "captionsetup", "geometry",
                            "vspace", "hspace", "vskip", "hskip", "rule", "includegraphics",
                            "usepackage", "documentclass", "graphicspath", "pagestyle",
                            "thispagestyle", "bibliographystyle", "bibliography",
                            "newcommand", "renewcommand", "providecommand", "def",
                            "DeclareMathOperator", "hypersetup", "definecolor",
                            "newcolumntype", "renewenvironment", "newenvironment"]

# 行内代码命令：X-PROSE-API 判定时其内容不算散文（\\verb 的定界符形式单独处理）
INLINE_CODE_COMMANDS = ["texttt", "lstinline", "mintinline", "url", "path", "nolinkurl",
                        "detokenize", "code", "verb"]


def generic_v13(prof):
    """v1.3 通用规则的阈值（profile 的 generic_v13 键可覆盖）。"""
    cfg = dict(GENERIC_V13_DEFAULTS)
    cfg.update(prof.get("generic_v13") or {})
    return cfg


def mk_g(rid, path, line, detail, snippet=""):
    """按 GENERIC_RULES_V13 登记的信息建 finding（id/族/严重度/来源轮次同源）。"""
    r = _G13_BY_ID[rid]
    return mk(rid, r["family"], r["severity"], path, line, detail, snippet, r["source_round"])

# USER_PROFILE 深度合并（覆盖同名键、列表整体替换）


def _deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return over
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_profile(path):
    if not path:
        return dict(BUILTIN_PROFILE)
    if not os.path.isfile(path):
        print(f"[ERROR] profile 不存在：{path}", file=sys.stderr)
        sys.exit(2)
    with open(path, encoding="utf-8-sig") as f:
        user = json.load(f)
    return _deep_merge(BUILTIN_PROFILE, user)


# ══════════════════════════════════════════════════════════════════════════
# 2. 文本预处理
# ══════════════════════════════════════════════════════════════════════════

EN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
CJK = re.compile(r"[\u4e00-\u9fff]")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def read_text(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


# 非散文环境：表格/算法/公式的行会被误判成"超长句"，句子级检查必须跳过。
# （v1.1 修：v1.0 在已投稿上把 tabular 行与作者元数据当成 41 条超长句误报）
NON_PROSE_ENVS = ["tabular", "tabularx", "longtable", "array", "algorithm",
                  "algorithmic", "verbatim", "lstlisting", "minted",
                  "align", "align*", "equation", "equation*", "eqnarray", "split"]

# 作者/单位/脚注等元数据命令：其内容不是论文散文，不得参与句子级检查
META_COMMANDS = ["author", "affiliation", "icmlauthor", "icmlaffiliation",
                 "institute", "address", "email", "orcid", "affil"]


def _drop_braced(t, cmd):
    """删除 \\cmd{...}（括号配平）的内容。"""
    out, i = [], 0
    pat = re.compile(r"\\" + re.escape(cmd) + r"\*?\s*\{")
    while True:
        m = pat.search(t, i)
        if not m:
            out.append(t[i:])
            break
        out.append(t[i:m.start()])
        _, end = balanced_arg(t, m.end() - 1)
        i = end + 1
    return "".join(out)


def strip_non_prose(raw):
    t = raw
    for env in NON_PROSE_ENVS:
        t = re.sub(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
                   " ", t, flags=re.S)
    for cmd in META_COMMANDS:
        t = _drop_braced(t, cmd)
    return t


def strip_tex_comments(raw):
    out = []
    for line in raw.splitlines():
        i, buf, n = 0, [], len(line)
        while i < n:
            c = line[i]
            if c == "\\" and i + 1 < n and line[i + 1] == "%":
                buf.append("\\%")
                i += 2
                continue
            if c == "%":
                break
            buf.append(c)
            i += 1
        out.append("".join(buf))
    return "\n".join(out)


def clean_for_prose(raw):
    """把 tex 变成"接近散文"的文本，用于句子级检查。"""
    t = strip_tex_comments(raw)
    t = strip_non_prose(t)
    t = re.sub(r"\$[^$]*\$", " MATH ", t)
    t = re.sub(r"\\(?:cite|citep|citet|ref|eqref|autoref|label)\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}\\]", " ", t)
    t = re.sub(r"\$", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t


def prose_sentences(prose):
    """只保留真正的散文句：丢掉表格残留行、公式碎片、投稿元数据、过短的段。"""
    out = []
    for s in SENT_SPLIT.split(prose):
        s = s.strip()
        if not s or "&" in s or "\\\\" in s:
            continue
        # 投稿系统的作者/单位元数据（organization= / city= / given-names= …）不是论文散文
        if re.search(r"\b(?:organization|city|postcode|street|country|given-names|"
                     r"surname|department|institution|e-mail|email|orcid)\s*=", s, re.I):
            continue
        compact = s.replace(" ", "")
        if not compact:
            continue
        letters = len(re.findall(r"[A-Za-z]", s))
        if letters < 0.55 * len(compact):      # 大量数字/符号 = 表格或公式残渣
            continue
        if words_en(s) < 5:
            continue
        out.append(s)
    return out


def balanced_arg(raw, start):
    """raw[start] 必须是 '{'；返回 (内层文本, 结束下标)。纯括号配平。"""
    if start >= len(raw) or raw[start] != "{":
        return "", start
    depth, i = 0, start
    while i < len(raw):
        if raw[i] == "{" and (i == 0 or raw[i - 1] != "\\"):
            depth += 1
        elif raw[i] == "}" and (i == 0 or raw[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return raw[start + 1:i], i
        i += 1
    return raw[start + 1:], len(raw)


def find_commands(raw, name):
    """返回 [(args, pos)]，命令名精确匹配（含可选 *）。"""
    out = []
    for m in re.finditer(r"\\" + re.escape(name) + r"\*?\s*(?=[\{\[])", raw):
        j = m.end()
        # 跳过可选参数
        while j < len(raw) and raw[j] == "[":
            k = raw.find("]", j)
            if k == -1:
                break
            j = k + 1
        if j < len(raw) and raw[j] == "{":
            body, end = balanced_arg(raw, j)
            out.append((body, m.start()))
    return out


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def words_en(s):
    return len(EN_WORD.findall(s))


def units(s):
    return len(EN_WORD.findall(s)) + len(CJK.findall(s))


# ══════════════════════════════════════════════════════════════════════════
# 3. 检查器
# ══════════════════════════════════════════════════════════════════════════

class Finding(dict):
    pass


def mk(rule_id, family, severity, path, line, detail, snippet="", source_round=""):
    return Finding(rule_id=rule_id, family=family, severity=severity, file=path,
                   line=line, snippet=(snippet or "")[:160], detail=detail,
                   source_round=source_round)


# ── 3.1 逐文件：文本级规则 ────────────────────────────────────────────────

def check_text_rules(path, raw, prof):
    out = []
    lines = raw.splitlines()
    clean = strip_tex_comments(raw)
    low = clean.lower()
    ignores = prof.get("ignore_line_contains", [])

    for rule in prof["banned_terms"]:
        # 条件触发（如 TOST 类规则只在语料含 TOST/equivalence 时才生效）
        conds = rule.get("when_any")
        if conds and not any(re.search(c, clean, re.I) for c in conds):
            continue
        for m in re.finditer(rule["pattern"], clean, re.I):
            ln = line_of(clean, m.start())
            text_line = lines[ln - 1] if 0 <= ln - 1 < len(lines) else ""
            if any(s in text_line for s in ignores):
                continue
            out.append(mk(rule["id"], "措辞红线", rule["severity"], path, ln,
                          rule["reason"], text_line.strip(), rule.get("source_round", "")))

    for rule in prof["residue"]["patterns"]:
        for m in re.finditer(rule["pattern"], clean, re.I):
            ln = line_of(clean, m.start())
            out.append(mk(rule["id"], "残留物", rule["severity"], path, ln,
                          rule["reason"], (lines[ln - 1] if ln - 1 < len(lines) else "").strip(),
                          rule.get("source_round", "")))
    return out


# ── 3.2 逐文件：句式与拼写 ───────────────────────────────────────────────

def check_style_rules(path, raw, prof):
    out = []
    st = prof["style"]
    prose = clean_for_prose(raw)

    # 句长（只用真正的散文句）
    sents = prose_sentences(prose)
    for s in sents:
        n = words_en(s)
        if n > st["max_sentence_words"]:
            out.append(mk("S-LONGSENT", "写作规范", st["sentence_words_severity"], path, 0,
                          f"句长 {n} 词 > {st['max_sentence_words']}（超过 20 词即应检查是否含多个主命题）",
                          s[:140], "R4"))

    # 句首填充语 + 连续同构句首
    consec, run = 0, 0
    openers = []
    for s in sents:
        m = re.match(r"^([A-Za-z]+)", s)
        op = (m.group(1).lower() if m else "")
        openers.append(op)
        if op in st["filler_openers"]:
            consec += 1
        else:
            consec = 0
        if consec >= st["filler_consecutive_limit"]:
            out.append(mk("S-FILLER", "写作规范", st["filler_severity"], path, 0,
                          f"连续 {consec} 句以填充语开头（阈值 {st['filler_consecutive_limit']}）；"
                          f"导师第 4 轮要求句首不得连续同构", " / ".join(openers[-consec:]), "R4"))
            consec = 0
    # 单个填充语出现也提示（Minor）
    fill_hits = [w for w in openers if w in st["filler_openers"]]
    if fill_hits:
        out.append(mk("S-FILLER-WORDS", "写作规范", "Minor", path, 0,
                      f"句首填充语 {len(fill_hits)} 处：{sorted(set(fill_hits))}（Notably/Importantly/"
                      f"In other words/Overall/Additionally 等建议不用）", "", "R4"))

    # 拼写一致性
    sp = st["spelling"]
    us_hits = {w: len(re.findall(r"\b" + w + r"\b", prose, re.I)) for w in sp["us"]}
    uk_hits = {w: len(re.findall(r"\b" + w + r"\b", prose, re.I)) for w in sp["uk"]}
    us_hits = {k: v for k, v in us_hits.items() if v}
    uk_hits = {k: v for k, v in uk_hits.items() if v}
    if us_hits and uk_hits:
        out.append(mk("S-SPELLING-MIX", "写作规范", sp["severity"], path, 0,
                      f"美式/英式拼写混用：US={sorted(us_hits)} UK={sorted(uk_hits)}；"
                      f"须统一美式（behavior/labeled/normalize/analyze/modeling/generalization）",
                      "", "R4"))
    return out


# ── 3.3 逐文件：图表与结构 ───────────────────────────────────────────────

def corpus_ref_graph(docs):
    """全语料的 \\ref 目标集合与 \\label 定义集合。
    v1.2 修：v1.1 按文件单独判孤儿 label，导致「正文引用补充材料图表」被误判为未被引用——
    一次投稿的正文+补充材料是同一个引用域，必须跨文件合起来判。
    ⚠️ 两个方向要分别用对：
      orphan label = label(本文件) − refs(全语料)
      undefined ref = ref(本文件) − labels(全语料)
    """
    refs, labels = set(), set()
    for _, raw in docs:
        clean = strip_tex_comments(raw)
        for cmd in ("ref", "eqref", "autoref", "cref", "Cref"):
            for x, _ in find_commands(clean, cmd):
                refs.update(p.strip() for p in x.split(",") if p.strip())
        for x, _ in find_commands(clean, "label"):
            labels.add(x.strip())
    return refs, labels


def check_float_rules(path, raw, prof, refs_all=None, labels_all=None):
    out = []
    st = prof["style"]
    caps = find_commands(raw, "caption")
    for body, pos in caps:
        n = len(body)
        if n > st["caption_max_chars"]:
            out.append(mk("F-CAPTION-LONG", "图表自明性", st["caption_severity"], path,
                          line_of(raw, pos),
                          f"caption {n} 字符 > {st['caption_max_chars']}（导师第 4 轮 #13：表注不得过长）",
                          body[:140], "R4"))

    # \label 与 \ref 配对（只对图/表 label 报警：章节与公式 label 本就允许不被引用）
    labels = set(x.strip() for x, _ in find_commands(raw, "label"))
    refs = set()
    for cmd in ("ref", "eqref", "autoref", "cref", "Cref"):
        for x, _ in find_commands(raw, cmd):
            refs.update(p.strip() for p in x.split(",") if p.strip())
    labels_domain = labels | set(labels_all or ())
    refs_domain = refs | set(refs_all or ())

    for lb in sorted(labels - refs_domain):
        if not re.match(r"^(fig|tab|table|figure)[:\-]", lb):
            continue
        out.append(mk("F-ORPHAN-LABEL", "结构", "Major", path, 0,
                      f"\\label{{{lb}}} 是图/表 label 但全语料无 \\ref → 该图表从未被正文引用", "", "R4"))
    for rf in sorted(refs - labels_domain):
        out.append(mk("F-UNDEF-REF", "结构", "Critical", path, 0,
                      f"\\ref{{{rf}}} 在全语料中找不到对应 label（未定义引用）", "", "R4"))

    # 节过长
    secs = []
    for cmd in ("section", "subsection"):
        for body, pos in find_commands(raw, cmd):
            secs.append((pos, body.strip()))
    secs.sort()
    for idx, (pos, title) in enumerate(secs):
        end = secs[idx + 1][0] if idx + 1 < len(secs) else len(raw)
        body = clean_for_prose(raw[pos:end])
        n = units(body)
        if n > st["section_max_words"]:
            out.append(mk("F-SECTION-LONG", "结构", st["section_severity"], path,
                          line_of(raw, pos),
                          f"小节「{title}」{n} 计数单位 > {st['section_max_words']}"
                          f"（导师第 4 轮 #11：单节不得过长）", "", "R4"))
    return out


# ── 3.4 逐文件：合规包装 ─────────────────────────────────────────────────

def check_compliance_rules(path, raw, prof):
    out = []
    comp = prof["compliance"]
    base = os.path.basename(path).lower()

    # Abstract
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw, re.S)
    if m:
        body = m.group(1)
        n = words_en(clean_for_prose(body))
        if n > comp["abstract_max_words"]:
            out.append(mk("C-ABSTRACT-LONG", "合规", comp["abstract_severity"], path,
                          line_of(raw, m.start()),
                          f"摘要 {n} 词 > {comp['abstract_max_words']}", "", "R4"))
        if comp["abstract_no_citation"] and re.search(r"\\cite", body):
            out.append(mk("C-ABSTRACT-CITE", "合规", comp["abstract_severity"], path,
                          line_of(raw, m.start()), "摘要中不得出现引用", "", "R4"))

    # Highlights（独立文件，每行一条 bullet）
    if "highlight" in base and not base.endswith(".md"):
        bullets = [l.strip(" \t-•*") for l in raw.splitlines() if l.strip()]
        hl = comp["highlights"]
        if not (hl["min"] <= len(bullets) <= hl["max"]):
            out.append(mk("C-HL-COUNT", "合规", hl["severity"], path, 0,
                          f"Highlights 条数 {len(bullets)} 不在 [{hl['min']},{hl['max']}]", "",
                          "R9"))
        for i, b in enumerate(bullets, 1):
            if len(b) > hl["max_chars_each"]:
                out.append(mk("C-HL-CHARS", "合规", hl["severity"], path, 0,
                              f"Highlights 第 {i} 条 {len(b)} 字符 > {hl['max_chars_each']}",
                              b[:120], "R9"))
    return out


# ── 3.5 跨文件：数值口径守恒 ─────────────────────────────────────────────

def check_numeric_invariants(docs, prof):
    out = []
    for rule in prof["numeric_invariants"]:
        for path, raw in docs:
            clean = strip_tex_comments(raw)
            for m in re.finditer(rule["forbidden_pattern"], clean):
                ln = line_of(clean, m.start())
                # v1.1 修：窗口从 ±160 收紧到 ±45 且不得跨空行——
                # 否则无关的 "66"（页码/图号）会被当成层数口径误报。
                win = clean[max(0, m.start() - 45): m.end() + 45]
                if "\n\n" in win:
                    continue
                ctx = rule.get("require_context")
                if ctx and not re.search(ctx, win, re.I):
                    continue
                ex = rule.get("exempt_if")
                if ex and re.search(ex, win, re.I):
                    continue
                out.append(mk(rule["id"], "口径守恒", rule["severity"], path, ln,
                              f"{rule['name']}：{rule['reason']}", win.strip(),
                              rule.get("source_round", "")))
    return out


# ── 3.6 跨文件：叙事口径 ─────────────────────────────────────────────────

def check_narrative(docs, prof):
    out = []
    nar = prof["narrative"]

    for rule in nar["forbidden_phrases"]:
        for path, raw in docs:
            clean = strip_tex_comments(raw)
            for m in re.finditer(rule["pattern"], clean, re.I):
                ln = line_of(clean, m.start())
                out.append(mk(rule["id"], "叙事口径", rule["severity"], path, ln,
                              rule["reason"],
                              clean[max(0, m.start() - 60): m.start() + 100].strip(),
                              rule.get("source_round", "")))

    corpus = "\n".join(strip_tex_comments(raw) for _, raw in docs)
    for rule in nar.get("canonical_claims", []):
        hit_files = sum(1 for _, raw in docs
                        if any(re.search(p, strip_tex_comments(raw), re.I) for p in rule["any_of"]))
        if hit_files < rule.get("min_files", 1):
            out.append(mk(rule["id"], "叙事口径", rule["severity"], "(corpus)", 0,
                          f"全文统一口径缺失：{rule['reason']}。"
                          f"期望至少 {rule.get('min_files',1)} 个文件出现，实际 {hit_files}。",
                          "", rule.get("source_round", "")))
    return out


# ── 3.7 跨文件：术语自洽（TOST） ─────────────────────────────────────────

def check_tost_consistency(docs, prof):
    """TOST/equivalence 语料中不得同时出现 non-inferior（除非显式声明单侧）。"""
    out = []
    corpus = "\n".join(strip_tex_comments(raw) for _, raw in docs)
    has_tost = re.search(r"\bTOST\b|two\s+one-?sided", corpus, re.I)
    has_noninf = re.search(r"\bnon-?inferior(?:ity)?\b", corpus, re.I)
    if has_tost and has_noninf:
        one_sided = re.search(r"\bone-?sided\b[^.]{0,80}non-?inferior", corpus, re.I)
        if not one_sided:
            path = docs[0][0] if docs else "(corpus)"
            out.append(mk("T-TOST-NONINF-CONFLICT", "统计术语", "Critical", path, 0,
                          "同一语料同时出现 TOST 与 non-inferiority：双侧 TOST 检验 equivalence，"
                          "不是非劣效。要么全文改 equivalence，要么改做单侧非劣效并写明。",
                          "", "R2/R3"))
    return out


# ── 3.8 跨文件：图/表与正文重复（启发式） ────────────────────────────────

def check_fig_tab_dup(docs, prof):
    """图 caption 与表 caption 共享 >=4 个相同数字 → 疑似重复（导师第 4 轮 #10）。"""
    out = []
    num = re.compile(r"\d+\.\d+")
    figs, tabs = [], []
    for path, raw in docs:
        clean = strip_tex_comments(raw)
        for body, pos in find_commands(clean, "caption"):
            nums = set(num.findall(body))
            if re.search(r"\b(?:figure|fig\.)\b", body, re.I):
                figs.append((path, nums, body[:80]))
            elif re.search(r"\btable\b", body, re.I):
                tabs.append((path, nums, body[:80]))
    for p1, n1, c1 in figs:
        for p2, n2, c2 in tabs:
            shared = n1 & n2
            if len(shared) >= 4:
                out.append(mk("F-FIGTAB-DUP", "图表自明性", "Minor", p1, 0,
                              f"图与表 caption 共享 {len(shared)} 个相同数值 {sorted(shared)}："
                              f"疑似图文/表格重复（导师第 4 轮 #10）", f"{c1} || {c2}", "R4"))
    return out


# ══════════════════════════════════════════════════════════════════════════
# 4. 汇总
# ══════════════════════════════════════════════════════════════════════════

FAMILIES = ["措辞红线", "口径守恒", "叙事口径", "统计术语", "图表自明性",
            "结构", "写作规范", "合规", "残留物"]


def cap_findings(findings, cap=5):
    """同一 (file, rule_id) 超过 cap 条时折叠为 cap 条 + 1 条汇总。
    目的：不让 40 条超长句把 1 条 em dash 淹掉。计数不丢（汇总行 + --json 的 by_rule）。"""
    from collections import OrderedDict
    groups = OrderedDict()
    for f in findings:
        groups.setdefault((f["file"], f["rule_id"]), []).append(f)
    out = []
    for (path, rid), items in groups.items():
        if len(items) <= cap:
            out.extend(items)
            continue
        kept = items[:cap]
        out.extend(kept)
        rest = items[cap:]
        out.append(mk(rid + "-MORE", kept[0]["family"], kept[0]["severity"], path, 0,
                      f"另有 {len(rest)} 处同类命中已被折叠（共 {len(items)} 处）。"
                      f"完整清单见 --json 输出。",
                      "", kept[0].get("source_round", "")))
    return out


def _per_file_findings(docs, prof):
    refs_all, labels_all = corpus_ref_graph(docs)
    findings = []
    for path, raw in docs:
        findings += check_text_rules(path, raw, prof)
        findings += check_style_rules(path, raw, prof)
        findings += check_float_rules(path, raw, prof, refs_all, labels_all)
        findings += check_compliance_rules(path, raw, prof)
    return findings


def run_checks(docs, prof):
    findings = _per_file_findings(docs, prof)
    findings += check_numeric_invariants(docs, prof)
    findings += check_narrative(docs, prof)
    findings += check_tost_consistency(docs, prof)
    findings += check_fig_tab_dup(docs, prof)
    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["family"], f["file"], f["line"]))
    return cap_findings(findings, prof.get("max_reported_per_rule", 5))


def run_checks_raw(docs, prof):
    """不折叠版本，供自测与统计使用。"""
    findings = _per_file_findings(docs, prof)
    findings += check_numeric_invariants(docs, prof)
    findings += check_narrative(docs, prof)
    findings += check_tost_consistency(docs, prof)
    findings += check_fig_tab_dup(docs, prof)
    return findings


def summarize(findings):
    by_sev = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV_ORDER}
    by_fam = {fam: sum(1 for f in findings if f["family"] == fam) for fam in FAMILIES}
    by_rule = {}
    for f in findings:
        by_rule[f["rule_id"]] = by_rule.get(f["rule_id"], 0) + 1
    return {"by_severity": by_sev, "by_family": {k: v for k, v in by_fam.items() if v},
            "by_rule": dict(sorted(by_rule.items(), key=lambda kv: -kv[1]))}


# ══════════════════════════════════════════════════════════════════════════
# 5. 自测（正/负控制）——确定性，不读外部文件
# ══════════════════════════════════════════════════════════════════════════

POS_TEX = r"""
\section{Introduction}
Our method attains parity with the distilled baseline --- a result we describe as strong.
The non-inferiority (TOST) analysis uses a two-sided margin, which we treat as equivalence.
The design is privacy-friendly and gradient-free, and a single seed shows a clear improvement.
TODO: add the full numbers.
\section{Results}
This sentence is deliberately made extremely long so that it certainly exceeds the thirty word limit which the style rule imposes and which the workflow requires be enforced mechanically in every future paper without exception whatsoever.
"""

NEG_TEX = r"""
\section{Introduction}
Our method reaches parity with the distilled baseline without keeping a live teacher.
The analysis reports results that are statistically equivalent within a practical margin of plus or minus 0.01.
All numbers are computed over the retained layers and reported per run.
\label{fig:demo}
\caption{Overview of the proposed pipeline.}
"""


def self_test():
    prof = dict(BUILTIN_PROFILE)
    results = []

    docs_pos = [("POSTEST.tex", POS_TEX)]
    docs_neg = [("NEGTEST.tex", NEG_TEX)]
    fp = run_checks_raw(docs_pos, prof)
    fn = run_checks_raw(docs_neg, prof)

    # ── 正控制：必须命中 ──
    must_hit = ["B-EMDASH", "B-TOST-NONINF", "B-PRIVACY-FRIENDLY", "B-GRADIENT-FREE-SCOPE",
                "B-SINGLE-SEED-CLAIM", "T-TOST-NONINF-CONFLICT", "RES-TODO", "S-LONGSENT"]
    got = {f["rule_id"] for f in fp}
    for r in must_hit:
        results.append({"control": f"positive:{r}", "ok": r in got,
                        "detail": "命中" if r in got else f"**漏报**（正控制失败）"})

    # ── 负控制：不得命中 ──
    must_not = ["B-EMDASH", "B-TOST-NONINF", "B-PRIVACY-FRIENDLY", "B-GRADIENT-FREE-SCOPE",
                "B-SINGLE-SEED-CLAIM", "T-TOST-NONINF-CONFLICT", "RES-TODO",
                "S-LONGSENT", "S-SPELLING-MIX", "F-UNDEF-REF"]
    gotn = {f["rule_id"] for f in fn}
    for r in must_not:
        results.append({"control": f"negative:{r}", "ok": r not in gotn,
                        "detail": "未命中（正确）" if r not in gotn
                                  else f"**误报**（负控制失败）"})

    # 负控制里 label 定义了但没引用 → 允许出现 F-ORPHAN-LABEL，不算失败（故意设计）
    ok = all(r["ok"] for r in results)
    fails = [r for r in results if not r["ok"]]
    print("=" * 70)
    print(f"advisor_pattern_gate.py 自测（正/负控制）  v{VERSION}")
    print("=" * 70)
    for r in results:
        print(f"  [{'OK  ' if r['ok'] else 'FAIL'}] {r['control']:38s} {r['detail']}")
    print(f"\n控制项 {len(results)}  通过 {len(results)-len(fails)}  失败 {len(fails)}")
    print(f"正控制命中 {len(got)} 条规则（含非必须命中项）；负控制命中 {len(gotn)} 条")
    if gotn:
        print(f"负控制实际命中（供人工判断是否合理）：{sorted(gotn)}")
    print("\n结论：" + ("自测通过" if ok else "**自测失败** —— 不得交付"))
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════
# 6. --explain：规则清单 + 来源轮次
# ══════════════════════════════════════════════════════════════════════════

def explain(prof):
    print("=" * 78)
    print(f"advisor_pattern_gate 规则清单（profile: {prof.get('profile_name')}）  v{VERSION}")
    print("=" * 78)
    print("\n【1】禁用词 / 措辞红线")
    for r in prof["banned_terms"]:
        cond = f"  条件: {'|'.join(r['when_any'])}" if r.get("when_any") else ""
        print(f"  {r['id']:26s} [{r['severity']:8s}] 源:{r.get('source_round','-'):7s} {r['reason'][:60]}{cond}")
    print("\n【2】数值 / 口径守恒（跨文件）")
    for r in prof["numeric_invariants"]:
        print(f"  {r['id']:26s} [{r['severity']:8s}] 源:{r.get('source_round','-'):7s} {r['name']}：{r['reason'][:60]}")
    print("\n【3】叙事口径（跨文件）")
    for r in prof["narrative"]["forbidden_phrases"]:
        print(f"  {r['id']:26s} [{r['severity']:8s}] 源:{r.get('source_round','-'):7s} 禁用：{r['reason'][:60]}")
    for r in prof["narrative"]["canonical_claims"]:
        print(f"  {r['id']:26s} [{r['severity']:8s}] 源:{r.get('source_round','-'):7s} 必须有：{r['reason'][:60]}")
    print("\n【4】统计术语自洽")
    print("  T-TOST-NONINF-CONFLICT      [Critical] 源:R2/R3   TOST 与 non-inferiority 不得同现（非单侧设计时）")
    print("\n【5】图表自明性 / 结构")
    st = prof["style"]
    print(f"  F-CAPTION-LONG   caption > {st['caption_max_chars']} 字符       源:R4")
    print(f"  F-SECTION-LONG   小节 > {st['section_max_words']} 计数单位      源:R4")
    print("  F-ORPHAN-LABEL   label 未被引用                   源:R4")
    print("  F-UNDEF-REF      \\ref 指向不存在 label           源:R4")
    print("  F-FIGTAB-DUP     图/表 caption 共享 >=4 数值       源:R4")
    print("\n【6】写作规范")
    print(f"  S-LONGSENT       句长 > {st['max_sentence_words']} 词                         源:R4")
    print(f"  S-FILLER         连续 > {st['filler_consecutive_limit']} 句以填充语开头            源:R4")
    print("  S-FILLER-WORDS   填充语出现（Minor）              源:R4")
    print("  S-SPELLING-MIX   美/英拼写混用                    源:R4")
    print("\n【7】合规包装")
    hl = prof["compliance"]["highlights"]
    print(f"  C-HL-COUNT       Highlights 条数 ∉ [{hl['min']},{hl['max']}]               源:R9")
    print(f"  C-HL-CHARS       Highlights 单条 > {hl['max_chars_each']} 字符             源:R9")
    print(f"  C-ABSTRACT-LONG  摘要 > {prof['compliance']['abstract_max_words']} 词                     源:R4")
    print("  C-ABSTRACT-CITE  摘要含引用                       源:R4")
    print("\n【8】残留物")
    for r in prof["residue"]["patterns"]:
        print(f"  {r['id']:26s} [{r['severity']:8s}] 源:{r.get('source_round','-'):7s} {r['reason'][:60]}")


# ══════════════════════════════════════════════════════════════════════════
# 7. main
# ══════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="论文「导师意见模式」投稿前机检门（Type-A 确定性门；不判写得好不好）")
    ap.add_argument("files", nargs="*", help="待检查文件（.tex/.md/.txt）")
    ap.add_argument("--profile", default=None, help="JSON profile（与内置规则深度合并）")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    ap.add_argument("--strict", action="store_true", help="Major 失败也返回 exit 1")
    ap.add_argument("--self-test", action="store_true", help="运行内置正/负控制自测")
    ap.add_argument("--explain", action="store_true", help="打印规则清单")
    ap.add_argument("--emit-profile", default=None, help="导出合并后的 profile 到指定路径")
    args = ap.parse_args()

    prof = load_profile(args.profile)

    if args.emit_profile:
        with open(args.emit_profile, "w", encoding="utf-8") as f:
            json.dump(prof, f, ensure_ascii=False, indent=2)
        print(f"profile 已导出：{args.emit_profile}")
        if not args.files and not args.explain and not args.self_test:
            return 0

    if args.explain:
        explain(prof)
        return 0

    if args.self_test:
        return self_test()

    if not args.files:
        ap.print_help()
        return 2

    docs = []
    for p in args.files:
        if not os.path.isfile(p):
            # fail-closed：文件读不到 ≠ 通过
            print(f"[ERROR] 文件不存在或不可读：{p}", file=sys.stderr)
            return 2
        docs.append((p, read_text(p)))

    findings = run_checks(docs, prof)
    summ = summarize(findings)
    crit = summ["by_severity"].get("Critical", 0)
    major = summ["by_severity"].get("Major", 0)
    verdict = "fail" if (crit or (args.strict and major)) else "pass"

    if args.json:
        print(json.dumps({"version": VERSION, "profile": prof.get("profile_name"),
                          "files": [p for p, _ in docs], "findings": findings,
                          "summary": summ, "critical": crit, "major": major,
                          "verdict": verdict}, ensure_ascii=False, indent=2))
    else:
        print("=" * 78)
        print(f"导师意见模式机检门（advisor_pattern_gate v{VERSION}）  profile={prof.get('profile_name')}")
        print("=" * 78)
        if not findings:
            print("\n无命中。")
        cur = None
        for f in findings:
            if f["family"] != cur:
                cur = f["family"]
                print(f"\n▸ {cur}")
            loc = f"{os.path.basename(f['file'])}:{f['line']}" if f["line"] else os.path.basename(f["file"])
            print(f"  [{f['severity']:8s}] {f['rule_id']:26s} {loc}")
            print(f"             {f['detail']}")
            if f["snippet"]:
                print(f"             › {f['snippet'][:120]}")
        print("\n" + "-" * 78)
        print(f"按严重度：Critical {crit}｜Major {major}｜Minor {summ['by_severity'].get('Minor',0)}")
        if summ["by_family"]:
            print("按族：" + "｜".join(f"{k} {v}" for k, v in summ["by_family"].items()))
        if summ["by_rule"]:
            print("Top 规则：" + "｜".join(f"{k}×{v}" for k, v in list(summ["by_rule"].items())[:8]))
        print("-" * 78)
        if crit:
            print("结论：**不得投稿**（Critical 未过）。逐条修掉或给出豁免理由后再跑。")
        elif major:
            print("结论：可通过（无 Critical），但须修掉 Major 或在交付物「局限」中逐条列明。")
        else:
            print("结论：通过。")
        print("注：本门只判「是否触发已知反模式」（Type-A）。论文是否够好仍须 Tier≥T2 独立评审。")

    return 1 if (crit or (args.strict and major)) else 0


if __name__ == "__main__":
    sys.exit(main())
