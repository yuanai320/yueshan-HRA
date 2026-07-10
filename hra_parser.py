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


def _from_image(data, secrets=None):
    """图片 OCR：① 云端免费额度 OCR（可选，配 secrets 即用）→ ② 本地 pytesseract → ③ 友好提示。

    云端 OCR 说明：腾讯云 / 百度智能云等通用文字识别均有「每月 1000 次」免费额度，
    注册后在 Streamlit secrets 配置 OCR_API_URL（与 OCR_API_KEY）即可启用，默认不接、零麻烦。
    接口约定：POST JSON {image: base64, api_key: key}，返回 {text: "识别文本"}。
    """
    # 1) 云端 OCR（可选）
    url = (secrets or {}).get("OCR_API_URL") or (secrets or {}).get("ocr_api_url")
    if url:
        try:
            import base64, requests
            key = (secrets or {}).get("OCR_API_KEY") or (secrets or {}).get("ocr_api_key") or ""
            r = requests.post(url, json={"image": base64.b64encode(data).decode(), "api_key": key},
                              timeout=15)
            if r.ok:
                j = r.json() or {}
                txt = j.get("text") or j.get("TextDetections") or ""
                if isinstance(txt, list):
                    txt = "\n".join(str(x) for x in txt)
                if txt and txt.strip():
                    return txt, None
        except Exception:
            pass  # 云端失败则回退本地 / 提示
    # 2) 本地 pytesseract（自托管 / 本地运行免费可用）
    try:
        from PIL import Image, ImageOps
        import pytesseract
        img = Image.open(io.BytesIO(data)).convert("RGB")
        # 增强预处理（与「悦检」同源）：灰度 + 自动对比度 + 小字放大，提升识别率
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        w, h = img.size
        if max(w, h) < 2000:
            scale = 2000.0 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))
        txt = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return txt, None
    except Exception as e:
        return "", ("图片 OCR 在当前环境不可用。两种免费方案：① 本地/自托管运行（已装 tesseract）"
                    "可自动识别；② 云端部署可接入免费额度 OCR（腾讯云/百度每月 1000 次免费），"
                    "把接口地址填到 Streamlit secrets 的 OCR_API_URL 即可。建议用 PDF/Excel/Word "
                    "上传以自动读取关键指标。")


def ocr_images_to_text(files, secrets=None):
    """多张图片 OCR 合并（与「悦检」同源）：逐张增强后识别，拼接成一份文本再统一解析。

    返回 (合并文本, 提示信息或 None)。无 tesseract 时给出友好提示，不崩溃。
    """
    if not files:
        return "", None
    texts, notes = [], []
    for f in files:
        data = f.getvalue()
        # 1) 云端 OCR（可选，配 secrets 即用）
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
        # 2) 本地 pytesseract（增强预处理：灰度 + 自动对比度 + 放大，提升识别率）
        try:
            from PIL import Image, ImageOps
            import pytesseract
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)
            w, h = img.size
            if max(w, h) < 2000:
                scale = 2000.0 / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)))
            txt = pytesseract.image_to_string(img, lang="chi_sim+eng")
            if txt and txt.strip():
                texts.append(txt)
            else:
                notes.append(f"{f.name} 未识别到文字")
        except Exception as e:
            notes.append(f"{f.name} OCR 不可用（需本机/自托管安装 tesseract+chi_sim）：{e}")
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

    m = re.search(r"性别[：:\s]*([男女])", text)
    if m:
        ind["sex"] = m.group(1)

    first(r"年龄[：:\s]*(\d{1,3})", "age", int)
    if "age" not in ind:
        m = re.search(r"(\d{2,3})\s*岁", text)
        if m:
            ind["age"] = int(m.group(1))

    first(r"(?:身高|身髙)[：:\s]*(\d{2,3}(?:\.\d)?)\s*(?:cm|厘米|公分|CM)", "height")
    first(r"(?:体重|重量)[：:\s]*(\d{2,3}(?:\.\d)?)\s*(?:kg|千克|公斤|KG)", "weight")
    first(r"BMI[：:\s]*(\d{1,2}(?:\.\d)?)", "bmi")

    m = re.search(r"(?:血压|收缩压|高压)[^0-9]*(\d{2,3})\s*[/／]\s*(\d{2,3})", text)
    if m:
        ind["sbp"] = float(m.group(1)); ind["dbp"] = float(m.group(2))
    else:
        ms = re.search(r"收缩压[^0-9]*(\d{2,3})", text)
        md = re.search(r"舒张压[^0-9]*(\d{2,3})", text)
        if ms: ind["sbp"] = float(ms.group(1))
        if md: ind["dbp"] = float(md.group(1))

    first(r"(?:空腹血糖|血糖)[^0-9]*(\d(?:\.\d)?)", "glucose")
    first(r"总胆固醇[^0-9]*(\d(?:\.\d)?)", "tc")
    first(r"甘油三酯[^0-9]*(\d(?:\.\d)?)", "tg")
    first(r"(?:低密度脂蛋白|低密度)[^0-9]*(\d(?:\.\d)?)", "ldl")
    first(r"(?:高密度脂蛋白|高密度)[^0-9]*(\d(?:\.\d)?)", "hdl")
    first(r"尿酸[^0-9]*(\d{2,3})", "uric", int)
    return ind


# ---------- 3. 由指标推导饮食关注 ----------
def derive_conditions(ind, sex="女"):
    conds = []
    if ind.get("glucose") is not None and ind["glucose"] >= 6.1:
        conds.append("高血糖")
    sbp = ind.get("sbp"); dbp = ind.get("dbp")
    if (sbp and sbp >= 140) or (dbp and dbp >= 90):
        conds.append("高血压")
    tg = ind.get("tg"); ldl = ind.get("ldl")
    if (tg and tg >= 1.7) or (ldl and ldl >= 3.4):
        conds.append("高血脂")
    uric = ind.get("uric")
    if uric is not None:
        cap = 420 if sex == "男" else 360
        if uric > cap:
            conds.append("痛风")
    return conds


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
    if ind.get("bmi"): parts.append(f"BMI {ind['bmi']}")
    if ind.get("sbp") and ind.get("dbp"):
        parts.append(f"血压 {int(ind['sbp'])}/{int(ind['dbp'])} mmHg")
    if ind.get("glucose"): parts.append(f"空腹血糖 {ind['glucose']} mmol/L")
    if ind.get("tg"): parts.append(f"甘油三酯 {ind['tg']} mmol/L")
    if ind.get("ldl"): parts.append(f"低密度脂蛋白 {ind['ldl']} mmol/L")
    if ind.get("uric"): parts.append(f"尿酸 {ind['uric']} μmol/L")
    if not parts:
        return "未从报告中识别到可读取的关键指标。"
    cond = result.get("conditions", [])
    s = "已识别：" + "、".join(parts)
    if cond:
        s += f" ｜ 系统提示关注：{('、'.join(cond))}"
    return s


if __name__ == "__main__":
    sample = """
    姓名：张三  性别：男  年龄：45 岁
    身高：175 cm  体重：82 kg  BMI：26.8
    血压：145/95 mmHg
    空腹血糖：7.2 mmol/L
    总胆固醇：5.8  甘油三酯：2.3  低密度脂蛋白：3.6  高密度脂蛋白：1.1
    尿酸：450 μmol/L
    """
    ind = parse_indicators(sample)
    print("指标:", ind)
    print("饮食关注:", derive_conditions(ind, "男"))
