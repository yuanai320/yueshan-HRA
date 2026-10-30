# -*- coding: utf-8 -*-
"""悦膳 · HRA 报告解析模块（Excel / PPT / PDF / Word / 图片 五类）

目标：从用户上传的 HRA 报告（与「悦检」同源设备：惠斯安普 HRA）中抽取关键
健康指标，自动推导饮食关注，联动膳食方案。

说明：
- 文本类（Excel/PPT/PDF/Word）可抽取正文后用正则识别指标；
- 图片类依赖本地 OCR（pytesseract + tesseract），免费云端通常不可用，
  此时如实提示「请用文本格式上传以自动读取」，表单仍可手动填写。
- 指标阈值采用国内常用临床切点（仅作参考，不替代医师诊断）。
"""

import re
import io


# ---------- 1. 文本抽取（按扩展名分派） ----------
def extract_text(data: bytes, ext: str, secrets=None):
    ext = (ext or "").lower()
    try:
        if ext in ("xlsx", "xlsm"):
            return _from_xlsx(data)
        if ext in ("xls",):
            return _from_xls_note()
        if ext in ("docx",):
            return _from_docx(data)
        if ext in ("pptx",):
            return _from_pptx(data)
        if ext in ("pdf",):
            return _from_pdf(data)
        if ext in ("png", "jpg", "jpeg", "bmp", "webp"):
            return _from_image(data, secrets)
    except Exception as e:  # 解析失败不崩溃，返回空文本 + 异常说明
        return "", f"解析失败：{e}"
    return "", "不支持的文件类型"


def _from_xlsx(data):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                out.append(" ".join(cells))
    return "\n".join(out), None


def _from_xls_note():
    return "", "旧版 .xls 需先另存为 .xlsx；当前已跳过解析。"


def _from_docx(data):
    import docx
    doc = docx.Document(io.BytesIO(data))
    out = [p.text for p in doc.paragraphs if p.text.strip()]
    for tbl in doc.tables:
        for r in tbl.rows:
            out.append(" ".join(c.text for c in r.cells if c.text.strip()))
    return "\n".join(out), None


def _from_pptx(data):
    try:
        from pptx import Presentation
    except Exception:
        return "", "未安装 python-pptx，无法解析 PPT；请用 .docx/.xlsx 等文本格式，或导出为 PDF 上传。"
    prs = Presentation(io.BytesIO(data))
    out = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    out.append(" ".join(c.text for c in row.cells))
    return "\n".join(out), None


def _from_pdf(data):
    try:
        import pdfplumber
    except Exception:
        return "", "未安装 pdfplumber，无法解析 PDF；请用 .docx/.xlsx 等文本格式。"
    out = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            out.append(t)
    return "\n".join(out), None


_OCR_ENGINE = None
def _get_ocr_engine():
    """RapidOCR(ONNX) 引擎单例：快、轻、中文准，无需系统 tesseract。"""
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _prep_image(data):
    """解码并压缩：JPEG draft 低分辨率解码 + 大图缩到 1600px 上限，控内存。"""
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    try:
        im.draft("RGB", (1600, 1600))
    except Exception:
        pass
    im = im.convert("RGB")
    w, h = im.size
    mx = max(w, h)
    if mx > 1600:
        sc = 1600.0 / mx
        im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))))
    return im


def _rapid_ocr_pil(img):
    """用 RapidOCR 识别 PIL 图，按检测框坐标还原表格版面（同行标签+值拼一起），返回文本；引擎不可用返回 None。"""
    try:
        import numpy as np
        res, _ = _get_ocr_engine()(np.array(img.convert("RGB")))
        if not res:
            return ""
        H = img.size[1]
        thr = max(14.0, H * 0.018)   # 行聚类阈值：y 中心相差小于此值视为同一行
        items = []
        for item in res:
            box, text = item[0], item[1]
            if not text:
                continue
            ys = [pt[1] for pt in box]
            xs = [pt[0] for pt in box]
            items.append((sum(ys) / 4.0, min(xs), str(text)))
        items.sort(key=lambda t: t[0])
        lines, cur, lasty = [], [], None
        for cy, cx, text in items:
            if lasty is None or abs(cy - lasty) <= thr:
                cur.append((cx, text))
                lasty = cy if lasty is None else (lasty + cy) / 2.0
            else:
                lines.append(cur)
                cur = [(cx, text)]
                lasty = cy
        if cur:
            lines.append(cur)
        out = []
        for ln in lines:
            ln.sort(key=lambda t: t[0])
            out.append("  ".join(t[1] for t in ln))
        return "\n".join(out)
    except Exception:
        return None


def _from_image(data, secrets=None):
    """图片 OCR：① 云端 OCR（可选，配 secrets 即用）→ ② 本地 RapidOCR → ③ 兜底 tesseract → ④ 提示。"""
    url = (secrets or {}).get("OCR_API_URL") or (secrets or {}).get("ocr_api_url")
    if url:
        try:
            import base64, requests
            key = (secrets or {}).get("OCR_API_KEY") or (secrets or {}).get("ocr_api_key") or ""
            r = requests.post(url, json={"image": base64.b64encode(data).decode(), "api_key": key}, timeout=15)
            if r.ok:
                j = r.json() or {}
                txt = j.get("text") or j.get("TextDetections") or ""
                if isinstance(txt, list):
                    txt = "\n".join(str(x) for x in txt)
                if txt and txt.strip():
                    return txt, None
        except Exception:
            pass
    try:
        img = _prep_image(data)
    except Exception:
        return "", "图片解码失败，请换一张清晰的照片。"
    txt = _rapid_ocr_pil(img)
    if txt is not None:
        return txt, None
    try:
        import pytesseract
        return pytesseract.image_to_string(img, lang="chi_sim+eng"), None
    except Exception:
        return "", ("图片 OCR 未启用（需安装 rapidocr-onnxruntime，见 requirements.txt）。"
                    "请确认部署已按 requirements 安装依赖后重试，或手动填表。")


def ocr_images_to_text(files, secrets=None):
    """多张图片 OCR 合并：逐张 RapidOCR 识别，拼接成一份文本再统一解析。"""
    if not files:
        return "", None
    texts, notes = [], []
    for f in files:
        data = f.getvalue()
        url = (secrets or {}).get("OCR_API_URL") or (secrets or {}).get("ocr_api_url")
        if url:
            try:
                import base64, requests
                key = (secrets or {}).get("OCR_API_KEY") or (secrets or {}).get("ocr_api_key") or ""
                r = requests.post(url, json={"image": base64.b64encode(data).decode(), "api_key": key}, timeout=15)
                if r.ok:
                    j = r.json() or {}
                    txt = j.get("text") or j.get("TextDetections") or ""
                    if isinstance(txt, list):
                        txt = "\n".join(str(x) for x in txt)
                    if txt and txt.strip():
                        texts.append(txt)
                        continue
            except Exception:
                pass
        try:
            img = _prep_image(data)
            txt = _rapid_ocr_pil(img)
            if txt is None:
                try:
                    import pytesseract
                    txt = pytesseract.image_to_string(img, lang="chi_sim+eng")
                except Exception:
                    txt = ""
            if txt and txt.strip():
                texts.append(txt)
            else:
                notes.append(f"{f.name} 未识别到文字（请上传清晰、正向的报告照片）")
        except Exception:
            notes.append(f"{f.name} 图片识别失败（请换一张清晰照片，或手动填表）")
    merged = "\n\n".join(texts)
    note = "；".join(notes) if notes else None
    return merged, note


# ---------- 2. 指标识别 ----------
def parse_indicators(text: str):
    if not text:
        return {}
    ind = {}

    def first(pat, key, cast=float):
        m = re.search(pat, text)
        if m:
            try:
                ind[key] = cast(m.group(1))
            except Exception:
                pass

    m = re.search(r"性别.{0,20}?([男女])", text)
    if m:
        ind["sex"] = m.group(1)

    first(r"年龄[：:\s]*(\d{1,3})", "age", int)
    if "age" not in ind:
        m = re.search(r"(\d{2,3})\s*岁", text)
        if m:
            ind["age"] = int(m.group(1))
    # HRA 报告含"出生日期"，无直接年龄 → 由出生日期推算
    if "age" not in ind:
        m = re.search(r"出生日期.{0,30}?(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
        if m:
            try:
                from datetime import date
                by, bm, bd = int(m.group(1)), int(m.group(2)), int(m.group(3))
                t = date.today()
                age = t.year - by - ((t.month, t.day) < (bm, bd))
                if 0 < age < 130:
                    ind["age"] = age
            except Exception:
                pass

    # 身高：标签后同行找 140–210 的三位数（表格版式 OCR 会错位，用范围校验兜住）
    _m = re.search(r"(?:身高|身髙)[^0-9]*(.*)", text)
    if _m:
        for _n in re.findall(r"\d{3}", _m.group(1)):
            if 140 <= int(_n) <= 210:
                ind["height"] = float(_n); break
    # 体重：标签后同行找 30–150 的数字
    _m = re.search(r"(?:体重|重量)[^0-9]*(.*)", text)
    if _m:
        for _n in re.findall(r"\d{2,3}", _m.group(1)):
            if 30 <= int(_n) <= 150:
                ind["weight"] = float(_n); break

    # HRA 为功能医学评估，不测血压/血糖/血脂/尿酸/BMI 等临床生化与体征数值
    # 仅解析报告里真实存在的：性别、出生日期(→年龄)、身高、体重
    # BMI 由识别到的身高/体重自动推算（报告本身不含 BMI 直接值）
    if ind.get("height") and ind.get("weight"):
        try:
            _hm = ind["height"] / 100.0
            ind["bmi"] = round(ind["weight"] / (_hm * _hm), 1)
        except Exception:
            pass
    return ind


# ---------- 3. 由指标推导饮食关注 ----------
def derive_conditions(ind, sex="女"):
    # HRA 为功能医学评估，不测血压/血糖/血脂/尿酸/BMI 等，无临床体征可推导饮食关注
    return []


# ---------- 4. 对外入口 ----------
def parse_hra_file(filename, data: bytes, secrets=None):
    """返回 {filename, ext, text_len, indicators, conditions, note}"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    text, note = extract_text(data, ext, secrets)
    ind = parse_indicators(text)
    sex = ind.get("sex", "女")
    conds = derive_conditions(ind, sex)
    return {
        "filename": filename, "ext": ext, "text_len": len(text),
        "indicators": ind, "conditions": conds, "note": note,
    }


def summarize(result):
    """生成给人看的一句话摘要。"""
    ind = result.get("indicators", {})
    parts = []
    if ind.get("sex"): parts.append(f"性别 {ind['sex']}")
    if ind.get("age"): parts.append(f"年龄 {ind['age']} 岁")
    if ind.get("height"): parts.append(f"身高 {ind['height']} cm")
    if ind.get("weight"): parts.append(f"体重 {ind['weight']} kg")
    if ind.get("bmi"): parts.append(f"BMI {ind['bmi']}（推算）")
    if not parts:
        return "未从报告中识别到可读取的关键指标。"
    cond = result.get("conditions", [])
    s = "已识别：" + "、".join(parts)
    if cond:
        s += f" ｜ 系统提示关注：{('、'.join(cond))}"
    return s


if __name__ == "__main__":
    sample = """
    会员基本信息
    姓名：测试  性别：男  出生日期：1971-01-01
    身高：176 cm  体重：83 Kg
    检测日期：2025-06-03
    """
    ind = parse_indicators(sample)
    print("指标:", ind)
    print("饮食关注:", derive_conditions(ind, "男"))
