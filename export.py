# -*- coding: utf-8 -*-
"""悦膳 · 方案导出模块（零依赖生成中文 PDF + 纯文本分享串）

- PDF 用 reportlab（已自带 Adobe CID 中文字体 STSong-Light，免外部字体文件）。
- 配色与网页「黄绿活力系」一致：深绿信任 #2E7D32 / 鲜绿 #5BA82F / 暖橙 #F5A623。
- 纯文本版便于微信转发给家人 / 营养师。
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 注册中文 CID 字体（reportlab 内置，无需外部 .ttf）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
CN = "STSong-Light"

# 配色
C_GREEN = colors.HexColor("#2E7D32")
C_GREEN2 = colors.HexColor("#5BA82F")
C_ORANGE = colors.HexColor("#F5A623")
C_BG = colors.HexColor("#F1F8E6")
C_LINE = colors.HexColor("#CFE3B0")
C_TEXT = colors.HexColor("#33422A")
C_GREY = colors.HexColor("#8A9466")

# 样式
_ST_TITLE = ParagraphStyle("t", fontName=CN, fontSize=20, leading=24,
                           textColor=C_GREEN, spaceAfter=2)
_ST_SUB = ParagraphStyle("s", fontName=CN, fontSize=9.5, leading=13,
                         textColor=C_GREY, spaceAfter=8)
_ST_H2 = ParagraphStyle("h2", fontName=CN, fontSize=13, leading=16,
                        textColor=C_GREEN2, spaceBefore=10, spaceAfter=4)
_ST_BODY = ParagraphStyle("b", fontName=CN, fontSize=9.5, leading=14,
                          textColor=C_TEXT, spaceAfter=2)
_ST_CELL = ParagraphStyle("c", fontName=CN, fontSize=9, leading=12,
                          textColor=C_TEXT)
_ST_CELLH = ParagraphStyle("ch", fontName=CN, fontSize=9, leading=12,
                           textColor=colors.white)
_ST_SMALL = ParagraphStyle("sm", fontName=CN, fontSize=8, leading=11,
                           textColor=C_GREY)
_ST_METRIC = ParagraphStyle("m", fontName=CN, fontSize=11, leading=13,
                            textColor=C_GREEN, alignment=1)
_ST_METRIC_SUB = ParagraphStyle("ms", fontName=CN, fontSize=8, leading=10,
                                textColor=C_GREY, alignment=1)

DISCLAIMER = ("免责声明：本方案为健康服务与管理专业的学习性示例推算，依据《中国居民膳食指南"
              "2022》《地中海饮食》《DASH 饮食》原则生成，不替代注册营养师或执业医师的诊断"
              "与治疗建议。如有疾病或特殊膳食需求，请咨询专业人士。")


def _metric_table(targets):
    def cell(v, sub):
        return Paragraph(f"<b>{v}</b><br/>{sub}", _ST_METRIC if False else
                         ParagraphStyle("mc", parent=_ST_METRIC, fontSize=13, leading=15))
    data = [[
        Paragraph(f"<b>{targets['kcal']}</b><br/>总热量 kcal", _ST_METRIC),
        Paragraph(f"<b>{targets['protein_g']}g</b><br/>蛋白质", _ST_METRIC),
        Paragraph(f"<b>{targets['fat_g']}g</b><br/>脂肪", _ST_METRIC),
        Paragraph(f"<b>{targets['carb_g']}g</b><br/>碳水", _ST_METRIC),
    ]]
    t = Table(data, colWidths=[43 * mm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, C_GREEN2),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _meal_table(meal, d):
    rows = [[Paragraph("食材", _ST_CELLH), Paragraph("份量", _ST_CELLH),
             Paragraph("热量 / 营养", _ST_CELLH)]]
    for it in d["items"]:
        rows.append([
            Paragraph(it["name"], _ST_CELL),
            Paragraph(f"{it['g']} g", _ST_CELL),
            Paragraph(f"{it['kcal']} kcal", _ST_CELL),
        ])
    rows.append([
        Paragraph("<b>小计</b>", _ST_CELL),
        Paragraph("", _ST_CELL),
        Paragraph(f"<b>{d['kcal']} kcal</b>　蛋白 {d['p']}g / 脂肪 {d['f']}g / 碳水 {d['c']}g",
                  _ST_CELL),
    ])
    t = Table(rows, colWidths=[70 * mm, 38 * mm, 66 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_GREEN),
        ("BACKGROUND", (0, -1), (-1, -1), C_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, C_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _shopping_table(shopping):
    rows = [[Paragraph("食材", _ST_CELLH), Paragraph("一日建议购买量", _ST_CELLH)]]
    for s in shopping:
        rows.append([Paragraph(s["name"], _ST_CELL), Paragraph(f"{s['g']} g", _ST_CELL)])
    t = Table(rows, colWidths=[90 * mm, 84 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_GREEN2),
        ("GRID", (0, 0), (-1, -1), 0.4, C_LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def build_pdf(user_label, targets, days, shopping_total, explanation_lines,
              hra_summary=None):
    """返回 PDF 字节（bytes）。"""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="悦膳 · 膳食方案", author="悦膳",
    )
    el = []
    el.append(Paragraph("🥗 悦膳 · 膳食方案", _ST_TITLE))
    el.append(Paragraph("源自「悦检」HRA 生态 · 检测 → 饮食干预闭环", _ST_SUB))
    el.append(Paragraph(user_label, _ST_BODY))
    el.append(Spacer(1, 6))
    el.append(_metric_table(targets))
    el.append(Paragraph(
        f"基础代谢 BMR ≈ {targets['bmr']} kcal　｜　每日总消耗 TDEE ≈ {targets['tdee']} kcal",
        _ST_SMALL))

    _nd = len(days)
    _day_title = (f"每日膳食方案（共 {_nd} 天循环 · 食材亲民、厨房可操作）"
                  if _nd > 1 else "今日膳食方案（示例一天 · 食材亲民、厨房可操作）")
    el.append(Paragraph(_day_title, _ST_H2))
    for day in days:
        el.append(Paragraph(day["label"], _ST_H2))
        for meal, d in day["meals"].items():
            el.append(Paragraph(f"{meal}（约 {d['kcal']} kcal）", _ST_BODY))
            el.append(_meal_table(meal, d))
            el.append(Spacer(1, 3))

    _shop_title = f"购物清单（{_nd} 天汇总）" if _nd > 1 else "购物清单（当日）"
    el.append(Paragraph(_shop_title, _ST_H2))
    el.append(_shopping_table(shopping_total))

    el.append(Paragraph("为什么这样安排（归源权威指南）", _ST_H2))
    for line in explanation_lines:
        el.append(Paragraph(f"· {line}", _ST_BODY))

    if hra_summary:
        el.append(Paragraph("来自你的 HRA 报告", _ST_H2))
        box = Table([[Paragraph(hra_summary, _ST_BODY)]], colWidths=[174 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E6")),
            ("BOX", (0, 0), (-1, -1), 0.6, C_ORANGE),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        el.append(box)

    el.append(Spacer(1, 8))
    el.append(HRFlowable(width="100%", color=C_LINE))
    el.append(Paragraph(DISCLAIMER, _ST_SMALL))

    doc.build(el)
    return buf.getvalue()


def build_plan_text(user_label, targets, days, shopping_total, explanation_lines,
                    hra_summary=None):
    """返回纯文本方案（便于微信转发）。"""
    L = []
    L.append("🥗 悦膳 · 膳食方案")
    L.append("源自「悦检」HRA 生态 · 检测→饮食干预闭环")
    L.append("─" * 30)
    L.append(user_label)
    L.append(f"每日目标：总热量 {targets['kcal']} kcal｜蛋白质 {targets['protein_g']}g｜"
             f"脂肪 {targets['fat_g']}g｜碳水 {targets['carb_g']}g")
    L.append(f"（基础代谢 BMR≈{targets['bmr']} kcal，每日总消耗 TDEE≈{targets['tdee']} kcal）")
    L.append("")
    _nd = len(days)
    L.append(f"【膳食方案（共 {_nd} 天循环）】")
    for day in days:
        L.append(f"▶ {day['label']}")
        for meal, d in day["meals"].items():
            L.append(f"· {meal}（约 {d['kcal']} kcal，蛋白{d['p']}g/脂肪{d['f']}g/碳水{d['c']}g）")
            for it in d["items"]:
                L.append(f"    - {it['name']} {it['g']} g · {it['kcal']} kcal")
    L.append("")
    L.append(f"【购物清单（{'%d 天汇总' % _nd if _nd > 1 else '当日'}）】")
    for s in shopping_total:
        L.append(f"· {s['name']} {s['g']} g")
    L.append("")
    L.append("【为什么这样安排】")
    for line in explanation_lines:
        L.append(f"· {line}")
    if hra_summary:
        L.append("")
        L.append("【来自 HRA 报告】")
        L.append(hra_summary)
    L.append("")
    L.append("⚠️ " + DISCLAIMER)
    return "\n".join(L)
