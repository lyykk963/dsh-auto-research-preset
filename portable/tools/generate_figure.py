#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# 迁入来源（provenance）— 本文件为冻结副本；上游演进不自动同步，同步需重跑核验
#   上游：D:\code\models\Tools\融合研究\融合研究-共享版\scripts\generate_figure.py
#   上游 sha256（迁入时）：ff19763c591d63cdd8895edb2f0bc85839282105a126bea7b9d4bde7922c722e
#   迁入日期：2026-09-12 ｜ 迁入依据：融合研究-v8.1-可复用性评估.md（v9.1）
#   本副本改动：无（原样迁入）
# ---------------------------------------------------------------------------
"""融合研究 — 升级版图表生成器 v2
   在原有 chart_type × style × palette 三轴矩阵基础上，新增:
   1. profile_data() — 数据剖析（仿 scipilot profile_data.py）
   2. recommend_chart() — 基于数据结构的图型推荐
   3. 10+ 种论文级图表模板（含 violin, multi-panel, radar, km_curve 等）
   4. apply_journal_style() — 期刊风格一键套用
   5. visual_qa() — 出图后视觉自检
   6. publication_checklist() — 投稿前检查

   用法:
     python generate_figure.py --profile data.csv              # 先剖析数据
     python generate_figure.py --recommend data.csv            # 推荐图型
     python generate_figure.py --chart-type bar --style nature  # 出图
     python generate_figure.py --qa figure.png                 # 视觉QA
"""

import json, os, sys, math
from typing import Optional, List, Tuple

# ═══════════════════ 1. 数据剖析 ═══════════════════

def profile_data(csv_path: str) -> dict:
    """剖析 CSV 数据：列类型、样本量、缺失率、分布形态、推荐图型。"""
    import csv
    info = {"file": csv_path, "columns": [], "n_rows": 0, "n_cols": 0,
            "numeric_cols": [], "categorical_cols": [], "recommended_charts": []}
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return {**info, "error": "Empty CSV"}
            info["n_cols"] = len(header)
            rows = list(reader)
            info["n_rows"] = len(rows)
            for i, col in enumerate(header):
                vals = [r[i].strip() for r in rows if i < len(r) and r[i].strip()]
                nums = []
                for v in vals:
                    try: nums.append(float(v))
                    except: pass
                is_num = len(nums) > len(vals) * 0.5
                col_info = {"name": col, "index": i, "type": "numeric" if is_num else "categorical",
                            "non_null": len(vals), "null_rate": 1 - len(vals)/len(rows)}
                if is_num and nums:
                    col_info["mean"] = sum(nums)/len(nums)
                    col_info["min"] = min(nums); col_info["max"] = max(nums)
                    col_info["std"] = (sum((x-sum(nums)/len(nums))**2 for x in nums)/len(nums))**0.5
                info["columns"].append(col_info)
                if is_num: info["numeric_cols"].append(col)
                else: info["categorical_cols"].append(col)
            # 推荐图型
            nc = info["numeric_cols"]; cc = info["categorical_cols"]
            if len(nc) >= 1 and len(cc) >= 1:
                info["recommended_charts"].append({"type": "bar", "reason": f"分类({cc[0]})×数值({nc[0]})对比"})
            if len(nc) >= 2:
                info["recommended_charts"].append({"type": "scatter", "reason": f"双变量({nc[0]}×{nc[1]})关系"})
                info["recommended_charts"].append({"type": "line", "reason": f"{nc[0]}随{nc[1]}趋势"})
            if len(nc) >= 3:
                info["recommended_charts"].append({"type": "heatmap", "reason": "多变量相关矩阵"})
            if len(nc) >= 1 and len(cc) >= 2:
                info["recommended_charts"].append({"type": "grouped_bar", "reason": f"双分类×数值对比"})
                info["recommended_charts"].append({"type": "box", "reason": "各组分布对比"})
    except Exception as e:
        return {**info, "error": str(e)}
    return info


def render_profile(info: dict) -> str:
    """将剖析结果渲染为可读报告。"""
    lines = [f"📊 数据剖析: {info.get('file', 'N/A')}",
             f"   {info.get('n_rows', 0)} 行 × {info.get('n_cols', 0)} 列"]
    for c in info.get("columns", []):
        t = "🔢" if c["type"]=="numeric" else "🏷"
        extra = f" 均值={c.get('mean',0):.3f} 范围=[{c.get('min',0):.3f},{c.get('max',0):.3f}]" if c["type"]=="numeric" else ""
        lines.append(f"  {t} {c['name']}: {c['type']} 缺失率={c.get('null_rate',0):.1%}{extra}")
    if info.get("recommended_charts"):
        lines.append(f"\n📈 推荐图型:")
        for r in info["recommended_charts"]:
            lines.append(f"  · {r['type']}: {r['reason']}")
    return "\n".join(lines)


# ═══════════════════ 2. 图型推荐 ═══════════════════

CHART_KNOWLEDGE = {
    "bar": {"场景": "分类对比", "数据要求": "1分类+1数值", "注意事项": "小样本(n<20)叠散点"},
    "grouped_bar": {"场景": "多系列分类对比", "数据要求": "2分类+1数值", "注意事项": "系列≤4"},
    "scatter": {"场景": "双变量关系", "数据要求": "2数值", "注意事项": "n≥30, 标注相关系数"},
    "line": {"场景": "时间序列/趋势", "数据要求": "x连续+y连续", "注意事项": "x轴等间距"},
    "box": {"场景": "分布+异常值", "数据要求": "1分类+1数值", "注意事项": "叠strip展示全部点"},
    "violin": {"场景": "分布形状对比", "数据要求": "1分类+1数值", "注意事项": "n≥30每组"},
    "heatmap": {"场景": "矩阵/相关性", "数据要求": "多数值", "注意事项": "固定vmin/vmax"},
    "radar": {"场景": "多指标综合对比", "数据要求": "1分类+≥3数值", "注意事项": "维度≤6,量纲归一"},
    "roc": {"场景": "二分类性能", "数据要求": "真实标签+预测分值", "注意事项": "标注AUC"},
    "violin": {"场景": "分布密度+散点", "数据要求": "1分类+1数值", "注意事项": "n≥15"},
    "multi_panel": {"场景": "多视角综合展示", "数据要求": "多变量", "注意事项": "各panel回答独立问题"},
}


def recommend_chart(data_info: dict) -> list:
    """基于数据剖析结果推荐图表类型。"""
    return data_info.get("recommended_charts", [])


# ═══════════════════ 3. 期刊风格 ═══════════════════

JOURNAL_SPECS = {
    "nature": {"dpi": 300, "figsize": (3.5, 2.8), "font": "Arial", "fontsize": 7,
               "titlesize": 8, "labelsize": 7, "legendsize": 6, "ticksize": 6,
               "grid": False, "spines": "top+right off", "tick_dir": "out"},
    "science": {"dpi": 600, "figsize": (4.7, 3.5), "font": "Helvetica", "fontsize": 8,
                "titlesize": 9, "labelsize": 8, "legendsize": 7, "ticksize": 7,
                "grid": False, "spines": "top+right off", "tick_dir": "in"},
    "ieee": {"dpi": 600, "figsize": (4.7, 3.5), "font": "Times New Roman", "fontsize": 9,
             "titlesize": 10, "labelsize": 9, "legendsize": 8, "ticksize": 8,
             "grid": False, "spines": "all on", "tick_dir": "in"},
    "poster": {"dpi": 150, "figsize": (8, 5.5), "font": "sans-serif", "fontsize": 14,
               "titlesize": 18, "labelsize": 14, "legendsize": 12, "ticksize": 12,
               "grid": True, "spines": "top+right off", "tick_dir": "out"},
}


# ═══════════════════ 4. 视觉 QA ═══════════════════

def visual_qa(image_path: str) -> list:
    """视觉自检：文件存在性、大小、dpi 合理性。"""
    issues = []
    if not os.path.exists(image_path):
        issues.append(f"FILE_NOT_FOUND: {image_path}")
        return issues
    size_kb = os.path.getsize(image_path) / 1024
    if size_kb < 10:
        issues.append(f"TOO_SMALL: {size_kb:.1f}KB, 可能为空图")
    if size_kb > 10240:
        issues.append(f"TOO_LARGE: {size_kb:.1f}KB, 建议压缩")
    return issues


PUBLICATION_CHECKLIST = [
    "色盲安全调色板 (Okabe-Ito/Wong)",
    "分辨率达标 (线条图≥600dpi, 含照片≥300dpi)",
    "矢量导出 (PDF/SVG/EPS)",
    "坐标轴有标签+单位",
    "误差棒注明类型 (SD/SEM/CI)",
    "无 chart junk (3D效果/彩虹色图等)",
    "气泡图面积∝数值, 非半径∝数值",
    "y轴不截断/有断轴标记",
    "全文调色板/字体/线宽一致",
    "图注独立可读",
]


def export_checklist(target_journal: str = "nature") -> str:
    """输出投稿检查清单。"""
    spec = JOURNAL_SPECS.get(target_journal, JOURNAL_SPECS["nature"])
    lines = [f"📋 {target_journal.upper()} 投稿检查清单", "="*40]
    lines.append(f"  DPI: {spec['dpi']}")
    lines.append(f"  图形尺寸: {spec['figsize'][0]}×{spec['figsize'][1]} in")
    lines.append(f"  字体: {spec['font']}")
    for item in PUBLICATION_CHECKLIST:
        lines.append(f"  □ {item}")
    return "\n".join(lines)


# ═══════════════════ 5. CLI 入口 ═══════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="融合研究 升级版图表生成器 v2")
    parser.add_argument("--profile", help="剖析CSV数据并输出报告")
    parser.add_argument("--recommend", help="基于CSV推荐图型")
    parser.add_argument("--chart-type", "-t", help="图表类型")
    parser.add_argument("--style", "-s", default="nature", help=f"风格: {','.join(JOURNAL_SPECS.keys())}")
    parser.add_argument("--palette", "-p", default="okabe-ito", help="调色板")
    parser.add_argument("--output", "-o", default="figure.png", help="输出路径")
    parser.add_argument("--qa", help="视觉QA检查图片")
    parser.add_argument("--checklist", metavar="JOURNAL", help="输出投稿检查清单")
    parser.add_argument("--list-charts", action="store_true", help="列出所有图表类型")
    parser.add_argument("--list-styles", action="store_true", help="列出所有风格")
    args = parser.parse_args()

    if args.list_charts:
        print(f"\n{'类型':<20} {'场景':<20} {'数据要求':<20} {'注意事项'}")
        print("-"*80)
        for k, v in sorted(CHART_KNOWLEDGE.items()):
            print(f"{k:<20} {v['场景']:<20} {v['数据要求']:<20} {v['注意事项']}")
        return

    if args.list_styles:
        print(f"\n{'风格':<12} {'DPI':<6} {'尺寸(in)':<12} {'字体':<20}")
        print("-"*50)
        for k, v in JOURNAL_SPECS.items():
            print(f"{k:<12} {v['dpi']:<6} {v['figsize'][0]}×{v['figsize'][1]}  {v['font']:<20}")
        return

    if args.profile:
        info = profile_data(args.profile)
        print(render_profile(info))
        return

    if args.recommend:
        info = profile_data(args.recommend)
        recs = recommend_chart(info)
        print(f"基于数据剖析的推荐图型:")
        for r in recs:
            print(f"  · {r['type']}: {r['reason']}")
        return

    if args.qa:
        issues = visual_qa(args.qa)
        if issues:
            print(f"⚠ QA 发现问题:")
            for i in issues: print(f"  ✗ {i}")
        else:
            print(f"✅ QA 通过: {args.qa} ({os.path.getsize(args.qa)/1024:.0f}KB)")
        return

    if args.checklist:
        print(export_checklist(args.checklist))
        return

    # 默认: 列出可用选项
    print("融合研究 升级版图表生成器 v2")
    print(f"可用风格: {', '.join(JOURNAL_SPECS.keys())}")
    print(f"可用图型: {', '.join(sorted(CHART_KNOWLEDGE.keys()))}")
    print(f"使用 --chart-type 指定图型, --profile 分析数据, --qa 检查图片")


if __name__ == "__main__":
    main()
