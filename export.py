# -*- coding: utf-8 -*-
"""悦膳 · 方案导出模块（零依赖生成中文 PDF + 纯文本分享串）

- PDF 用 reportlab（已自带 Adobe CID 中文字体 STSong-Light，免外部字体文件）。
- 配色与网页「黄绿活力系」一致：深绿信任 #2E7D32 / 鲜绿 #5BA82F / 暖橙 #F5A623。
- 纯文本版便于微信转发给家人 / 营养师。
"""

import os
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
from reportlab.pdfbase.ttfonts import TTFont


def _register_cn_font():
    """优先嵌入 TrueType 中文字体，确保电脑/手机任意阅读器都能显示中文；
    找不到系统字体时回退 reportlab 内置 CID 字体（STSong-Light）。"""
    _dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        (os.path.join(_dir, "cn_font.ttc"), 0),                 # 项目内开源中文字体（跨平台一致，优先）
        ("C:/Windows/Fonts/msyh.ttc", 0),                       # 微软雅黑 (Windows)
        ("C:/Windows/Fonts/simhei.ttf", 0),                     # 黑体 (Windows)
        ("C:/Windows/Fonts/simsun.ttc", 0),                     # 宋体 (Windows)
        ("/System/Library/Fonts/PingFang.ttc", 0),              # macOS 苹方
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),    # Linux 文泉驿
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ]
    for path, idx in candidates:
        try:
            pdfmetrics.registerFont(TTFont("CN", path, subfontIndex=idx))
            return "CN"
        except Exception:
            continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


# 注册中文字体（嵌入优先，跨平台回退）
CN = _register_cn_font()

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
            Paragraph(f"{it.get('emoji','')} {it['name']}", _ST_CELL),
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


def _dish_block(d):
    """一餐内的每道菜：菜名 + 食材 + 做法步骤 + 提示（PDF 内不用 emoji，避免字体缺字）"""
    out = []
    for dish in d.get("dishes", []):
        out.append(Paragraph(f"<b>{dish['name']}</b>（约 {dish['kcal']} kcal）", _ST_BODY))
        ing = "、".join(f"{it['name']} {it['g']}g" for it in dish.get("items", []))
        if ing:
            out.append(Paragraph(f"食材：{ing}", _ST_SMALL))
        for i, st in enumerate(dish.get("steps", []), 1):
            out.append(Paragraph(f"　{i}. {st}", _ST_SMALL))
        if dish.get("tip"):
            out.append(Paragraph(f"　提示：{dish['tip']}", _ST_SMALL))
    return out


def _water_block(water):
    rows = [[Paragraph("时段", _ST_CELLH), Paragraph("水量", _ST_CELLH), Paragraph("怎么喝", _ST_CELLH)]]
    for x in water.get("plan", []):
        rows.append([Paragraph(x["slot"], _ST_CELL), Paragraph(f"{x['ml']} ml", _ST_CELL),
                     Paragraph(x["note"], _ST_CELL)])
    rows.append([Paragraph("<b>全天合计</b>", _ST_CELL), Paragraph(f"<b>{water['total']} ml</b>", _ST_CELL),
                 Paragraph("天热、运动、出汗多时再加 300–500 ml", _ST_CELL)])
    t = Table(rows, colWidths=[36 * mm, 32 * mm, 106 * mm])
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
    rows = [[Paragraph("食材", _ST_CELLH), Paragraph("建议购买量", _ST_CELLH),
             Paragraph("参考价", _ST_CELLH)]]
    for s in shopping:
        rows.append([Paragraph(f"{s.get('emoji','')} {s['name']}", _ST_CELL),
                     Paragraph(f"{s['g']} g", _ST_CELL),
                     Paragraph(f"约 ¥{s.get('price', 0)}", _ST_CELL)])
    t = Table(rows, colWidths=[80 * mm, 54 * mm, 40 * mm])
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
              hra_summary=None, water=None, split=None):
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
            _pct = f"　占全天 {d['share']}%" if d.get("share") else ""
            el.append(Paragraph(f"<b>{meal}</b>　约 {d['kcal']} kcal{_pct}　·　{d.get('set','')}", _ST_BODY))
            if d.get("dishes"):
                el.extend(_dish_block(d))
            else:
                el.append(_meal_table(meal, d))
            el.append(Spacer(1, 4))

    if water:
        el.append(Paragraph("全天饮水计划", _ST_H2))
        el.append(Paragraph(
            f"建议每日饮水约 <b>{water['total']} ml</b>（约 {water['total'] // 250} 杯，不含食物中的水分）。"
            "《中国居民膳食指南（2022）》推荐成年女性 1500 ml、男性 1700 ml 起。", _ST_SMALL))
        el.append(Spacer(1, 3))
        el.append(_water_block(water))
        el.append(Spacer(1, 6))

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


def _disp_width(s):
    """按显示宽度计算（中文/全角算 2，英文数字算 1），用于纯文本列对齐。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in str(s))


def _pad(s, n):
    s = str(s)
    return s + " " * max(1, n - _disp_width(s))


def build_plan_text(user_label, targets, days, shopping_total, explanation_lines,
                    hra_summary=None, water=None):
    """返回纯文本方案（便于微信转发）：对齐表格 + 留白，手机窄屏不挤。"""
    L = []
    L.append("🥗 悦膳 · 膳食方案")
    L.append("源自「悦检」HRA 生态 · 检测→饮食干预闭环")
    L.append("─" * 28)
    L.append(user_label)
    L.append("每日目标：总热量 %d kcal｜蛋白 %s g｜脂肪 %s g｜碳水 %s g"
             % (targets['kcal'], targets['protein_g'], targets['fat_g'], targets['carb_g']))
    L.append("（基础代谢 BMR≈%d，每日总消耗 TDEE≈%d）" % (targets['bmr'], targets['tdee']))
    L.append("")
    _nd = len(days)
    L.append("【膳食方案 · %d天循环】" % _nd)
    for day in days:
        L.append("")
        L.append("▶ %s" % day['label'])
        for meal, d in day["meals"].items():
            L.append("")
            L.append("  %s（约 %d kcal）%s" % (meal, d['kcal'], d.get("set", "")))
            for _dish in d.get("dishes", []):
                L.append("     · %s（约 %s kcal）" % (_dish["name"], _dish["kcal"]))
                _ing = "、".join("%s %sg" % (it["name"], it["g"]) for it in _dish.get("items", []))
                if _ing:
                    L.append("       食材：%s" % _ing)
                for _i, _st in enumerate(_dish.get("steps", []), 1):
                    L.append("       %d. %s" % (_i, _st))
                if _dish.get("tip"):
                    L.append("       提示：%s" % _dish["tip"])
            L.append("    %s %s %s %s" % (
                _pad("食材", 15), _pad("份量", 9), _pad("热量", 11), "参考价"))
            for it in d["items"]:
                _name = "%s%s" % (it.get('emoji', ''), it['name'])
                L.append("    %s %s %s %s" % (
                    _pad(_name, 15), _pad("%g g" % it['g'], 9),
                    _pad("%g kcal" % it['kcal'], 11), "约 ¥%s" % it.get('price', 0)))
            L.append("    %s" % ("─" * 32))
            L.append("    小计：%d kcal　蛋白 %s g / 脂肪 %s g / 碳水 %s g"
                     % (d['kcal'], d['p'], d['f'], d['c']))
    L.append("")
    if water:
        L.append("")
        L.append("【全天饮水计划】建议约 %d ml（约 %d 杯）" % (water["total"], water["total"] // 250))
        for x in water.get("plan", []):
            L.append("  %s　%d ml　%s" % (x["slot"], x["ml"], x["note"]))
        L.append("")
    L.append("【购物清单 · %d天汇总】" % _nd)
    L.append("  %s %s %s" % (_pad("食材", 17), _pad("购买量", 11), "参考价"))
    for s in shopping_total:
        _name = "%s%s" % (s.get('emoji', ''), s['name'])
        L.append("  %s %s %s" % (
            _pad(_name, 17), _pad("%g g" % s['g'], 11), "约 ¥%s" % s.get('price', 0)))
    L.append("")
    L.append("【为什么这样安排】")
    for line in explanation_lines:
        L.append("· %s" % line)
    if hra_summary:
        L.append("")
        L.append("【来自 HRA 报告】")
        L.append(hra_summary)
    L.append("")
    L.append("⚠️ " + DISCLAIMER)
    return "\n".join(L)
