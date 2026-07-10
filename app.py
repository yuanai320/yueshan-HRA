# -*- coding: utf-8 -*-
"""悦膳 · 膳食方案生成器（作品4）Streamlit 应用

零成本部署：Streamlit Cloud 免费档 + Folium + OpenStreetMap。
视觉：黄绿活力系（催人奋进、有食欲、给人信心），与「蓝抑食欲」相反。
核心：① 上传 HRA 报告（Excel/PPT/PDF/Word/图片）自动读取关键指标；
       ② 也可手动填表（未做过 HRA 的人同样可用）；③ 全国就近买菜地图。
"""

import streamlit as st
import foods as foods_mod
import poi as poi_mod
import hra_parser as hra_mod
import export as export_mod

st.set_page_config(page_title="悦膳 · 膳食方案生成器", page_icon="🥗", layout="wide")

# ---------- 黄绿活力系样式 ----------
st.markdown("""
<style>
.big-title{font-size:2.2rem;font-weight:800;color:#2E7D32;line-height:1.3;}
.big-title .accent{color:#F5A623;}
.sub{color:#5a6b3a;font-size:1.02rem;line-height:1.7;margin-top:2px;}
.value{color:#3F8E1E;font-size:1.0rem;font-weight:600;margin:10px 0 4px;line-height:1.6;}
.card{border-radius:14px;padding:16px 20px;background:#F1F8E6;border-left:5px solid #F5A623;margin:12px 0;line-height:1.7;}
.metric-box{background:#EAF5D8;border-radius:12px;padding:14px 10px;text-align:center;line-height:1.5;}
.kcal{color:#3F8E1E;font-weight:800;font-size:1.6rem;line-height:1.2;}
.disclaimer{font-size:0.84rem;color:#8a9466;line-height:1.6;}
.hra-box{border-radius:14px;padding:16px 20px;background:#FFF8E6;border:1px dashed #F5A623;margin:12px 0;line-height:1.7;}
.stButton>button{background:#F5A623;color:#3a2a00;border:none;border-radius:10px;
  font-weight:700;padding:0.55rem 1.1rem;font-size:1rem;}
.stButton>button:hover{background:#E0960F;}
.stDownloadButton>button{background:#5BA82F;color:#fff;border-radius:10px;font-size:1rem;padding:0.55rem 1rem;}
.banner{border-radius:12px;padding:12px 16px;background:#FFF8E6;border:1px solid #F5A623;
  color:#7a5a00;font-size:0.9rem;margin:14px 0;line-height:1.7;}
.banner b{color:#a3421a;}
/* 响应式：桌面限宽 940 居中，手机满宽；全局 17px / 行距 1.7，字不挤不密 */
@media (min-width: 980px){
  .block-container{max-width:940px !important;margin:0 auto;padding-top:2.2rem;padding-bottom:3rem;}
}
@media (max-width: 640px){
  .block-container{padding-left:1rem !important;padding-right:1rem !important;}
}
html, body, .stApp, .stApp p, .stApp div, .stApp span, .stApp label{
  font-size:17px !important;line-height:1.7 !important;
}
h2, h3{margin-top:1.5rem !important;margin-bottom:0.4rem !important;}
</style>
""", unsafe_allow_html=True)

# 表单字段默认值（也用于 HRA 读取后回填）
_DEFAULTS = {
    "hra_sex": "女", "hra_age": 20, "hra_height": 162, "hra_weight": 55,
    "hra_activity": "轻度活动", "hra_goal": "减脂", "hra_conditions": [],
    "hra_prefs": "无特殊", "hra_allergy": "",
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

st.markdown('<p class="big-title">🥗 悦膳 <span class="accent">·</span> 膳食方案生成器</p>', unsafe_allow_html=True)
st.markdown('<p class="sub">把健康管理专业知识变成能上线的产品 · 健康服务与管理 作品4 · 源自「悦检」HRA 生态</p>', unsafe_allow_html=True)
st.markdown('<p class="value">3 步拿到专属膳食方案：① 上传 HRA 报告自动读取（或手动填表） ② 生成一日三餐 + 购物清单 ③ 一键导出 PDF / 就近买菜地图</p>', unsafe_allow_html=True)
st.markdown('<div class="banner">⚠️ 本方案为依据《中国居民膳食指南2022》《地中海饮食》《DASH 饮食》的示例性推算，<b>不替代医师或注册营养师的诊断</b>。如有疾病或特殊膳食需求，请遵医嘱或咨询专业人士。</div>', unsafe_allow_html=True)
st.markdown("---")

# ================= ① HRA 报告上传（五个窗口） =================
st.markdown("### 📄 已有 HRA 报告？上传自动读取（与「悦检」同源）")
st.caption("支持 Excel / PPT / PDF / Word / 拍照图片 五种；没做过 HRA 也能直接往下填表 👇")
up_cols = st.columns(5)
with up_cols[0]:
    up_xlsx = st.file_uploader("📊 Excel", type=["xlsx", "xls"], key="up_xlsx")
with up_cols[1]:
    up_pptx = st.file_uploader("📽️ PPT", type=["pptx"], key="up_pptx")
with up_cols[2]:
    up_pdf = st.file_uploader("📄 PDF", type=["pdf"], key="up_pdf")
with up_cols[3]:
    up_docx = st.file_uploader("📝 Word", type=["docx"], key="up_docx")
with up_cols[4]:
    up_img = st.file_uploader("📷 拍照", type=["png", "jpg", "jpeg"], key="up_img")

uploaded = [u for u in (up_xlsx, up_pptx, up_pdf, up_docx, up_img) if u is not None]
current_names = tuple(sorted(u.name for u in uploaded))

if uploaded and st.session_state.get("hra_applied_for") != current_names:
    merged_ind, merged_conds, notes = {}, set(), []
    try:
        _sec = st.secrets
    except Exception:
        _sec = None
    for u in uploaded:
        res = hra_mod.parse_hra_file(u.name, u.getvalue(), secrets=_sec)
        if res["indicators"]:
            merged_ind.update(res["indicators"])
        merged_conds.update(res["conditions"])
        if res["note"]:
            notes.append(f"· {u.name}：{res['note']}")
    # 回填表单
    if merged_ind.get("sex"): st.session_state["hra_sex"] = merged_ind["sex"]
    if merged_ind.get("age"): st.session_state["hra_age"] = int(merged_ind["age"])
    if merged_ind.get("height"): st.session_state["hra_height"] = float(merged_ind["height"])
    if merged_ind.get("weight"): st.session_state["hra_weight"] = float(merged_ind["weight"])
    if merged_conds:
        st.session_state["hra_conditions"] = list(merged_conds)
    st.session_state["hra_applied_for"] = current_names
    st.session_state["hra_last_summary"] = hra_mod.summarize({
        "indicators": merged_ind, "conditions": list(merged_conds)})
    st.session_state["hra_notes"] = notes

if not uploaded:
    st.session_state["hra_applied_for"] = None

if "hra_last_summary" in st.session_state and uploaded:
    st.markdown(f'<div class="hra-box">✅ {st.session_state["hra_last_summary"]}'
                f'<br><span class="disclaimer">指标阈值参考国内常用临床切点，仅供膳食参考，不替代医师诊断。</span></div>',
                unsafe_allow_html=True)
    if st.session_state.get("hra_notes"):
        for n in st.session_state["hra_notes"]:
            st.caption(n)

st.markdown("---")

# ================= ② 手动表单（HRA 用户已回填） =================
with st.form("yueshan_form"):
    st.markdown("### ① 先告诉我你的情况")
    c1, c2, c3 = st.columns(3)
    with c1:
        sex = st.selectbox("性别", ["女", "男"], key="hra_sex")
        age = st.number_input("年龄", 14, 80, key="hra_age")
    with c2:
        height = st.number_input("身高 (cm)", 140, 210, key="hra_height")
        weight = st.number_input("体重 (kg)", 35, 150, key="hra_weight")
    with c3:
        activity = st.selectbox("活动强度", ["久坐", "轻度活动", "中度活动", "高强度"], key="hra_activity")
        goal = st.selectbox("目标", ["减脂", "维持", "增肌", "健康管理"], key="hra_goal")

    st.markdown("### ② 健康关注（可多选）")
    conditions = st.multiselect("有无需要留意的指标？",
                                ["高血压", "高血糖", "高血脂", "痛风"], key="hra_conditions")
    prefs = st.radio("饮食偏好", ["无特殊", "素食"], horizontal=True, key="hra_prefs")
    allergy = st.text_input("忌口 / 过敏 / 不爱吃（选填，如：海鲜、花生）", key="hra_allergy")

    st.markdown("### ③ 方案微调（份量 / 口味 / 天数）")
    c4, c5, c6 = st.columns(3)
    with c4:
        days_sel = st.selectbox("循环天数", [1, 3, 5, 7], index=0, key="hra_days")
    with c5:
        portion_sel = st.selectbox("份量", ["标准", "偏少", "偏多"], index=0, key="hra_portion")
    with c6:
        taste_sel = st.radio("口味", ["家常", "清淡", "浓郁"], horizontal=True, key="hra_taste")

    submitted = st.form_submit_button("✨ 生成我的膳食方案", use_container_width=True)

if not submitted:
    st.info("填好上面（或上传 HRA 自动读取），点按钮，立刻生成专属膳食方案 + 购物清单 + 全国就近买菜地图 🗺️")
    st.markdown('<p class="disclaimer">说明：本工具为健康服务与管理专业的学习性作品，方案依《中国居民膳食指南2022》《地中海饮食》'
                '《DASH饮食》原则做示例推算，不替代注册营养师或医师的诊断与治疗建议。</p>', unsafe_allow_html=True)
    st.stop()

# ================= ③ 计算与展示 =================
conds = list(conditions)
if allergy.strip():
    conds.append(f"忌口:{allergy.strip()}")
targets = foods_mod.compute_targets(sex, age, height, weight, activity, goal)
portion = {"标准": 1.0, "偏少": 0.85, "偏多": 1.15}[portion_sel]
plan = foods_mod.build_plan(targets, conds, prefs, days=days_sel, portion=portion, taste=taste_sel)

st.markdown("### 📊 你的每日营养目标")
m1, m2, m3, m4 = st.columns(4)
m1.markdown(f'<div class="metric-box"><div class="kcal">{targets["kcal"]}</div><div>总热量 kcal</div></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="metric-box"><div class="kcal">{targets["protein_g"]}g</div><div>蛋白质</div></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="metric-box"><div class="kcal">{targets["fat_g"]}g</div><div>脂肪</div></div>', unsafe_allow_html=True)
m4.markdown(f'<div class="metric-box"><div class="kcal">{targets["carb_g"]}g</div><div>碳水</div></div>', unsafe_allow_html=True)
st.caption(f"基础代谢 BMR ≈ {targets['bmr']} kcal ｜ 每日总消耗 TDEE ≈ {targets['tdee']} kcal")

_nd = len(plan["days"])
st.markdown(f"### 🍱 膳食方案（共 {_nd} 天循环 · 食材亲民、厨房可操作）")
for _day in plan["days"]:
    st.markdown(f"#### 📅 {_day['label']}")
    for meal, d in _day["meals"].items():
        with st.expander(f"{meal} · {d['kcal']} kcal（蛋白 {d['p']}g / 脂肪 {d['f']}g / 碳水 {d['c']}g）",
                         expanded=(meal == "早餐" and _day is plan["days"][0])):
            for it in d["items"]:
                st.markdown(f"- **{it['name']}**　{it['g']} g　·　{it['kcal']} kcal")

_shop_title = f"### 🛒 购物清单（{_nd} 天汇总）" if _nd > 1 else "### 🛒 购物清单（当日）"
st.markdown(_shop_title)
shop_lines = "、".join([f"{s['name']}（{s['g']}g）" for s in plan["shopping_total"]])
st.markdown(f'<div class="card">{shop_lines}</div>', unsafe_allow_html=True)

st.markdown("### 💡 为什么这样安排（归源权威指南）")
for line in foods_mod.explanation(goal, conditions, taste_sel):
    st.markdown(f"- {line}")

if "hra_last_summary" in st.session_state and st.session_state.get("hra_applied_for"):
    st.markdown("### 🔗 来自你的 HRA 报告（检测 → 饮食干预 闭环）")
    st.markdown(f'<div class="hra-box">本方案已读取你上传的 HRA 报告关键指标，'
                f'并据此自动纳入饮食关注：<b>{("、".join(conditions) if conditions else "暂无异常提示")}</b>。'
                f'「悦检」读懂报告，「悦膳」把指标变成一日三餐与购物清单——'
                f'从「知道自己哪里要留意」到「每天知道吃什么」，形成可执行的检测→饮食干预闭环。</div>', unsafe_allow_html=True)

st.markdown("---")

# ================= ③-⑤ 方案导出 / 分享 =================
st.markdown("### 📤 方案导出 / 分享")
_real_conds = [c for c in conditions if not c.startswith("忌口:")]
_user_label = (f"{sex} · {age}岁 · {height}cm/{weight}kg · {activity} · 目标：{goal}"
               + (f" · 关注：{'、'.join(_real_conds)}" if _real_conds else "")
               + f" · 份量：{portion_sel} · 口味：{taste_sel} · {days_sel}天循环")
_expl_lines = foods_mod.explanation(goal, conditions, taste_sel)
_hra_sum = None
if "hra_last_summary" in st.session_state and st.session_state.get("hra_applied_for"):
    _hra_sum = st.session_state["hra_last_summary"]
_pdf_bytes = export_mod.build_pdf(_user_label, targets, plan["days"], plan["shopping_total"], _expl_lines, _hra_sum)
_txt_bytes = export_mod.build_plan_text(_user_label, targets, plan["days"], plan["shopping_total"], _expl_lines, _hra_sum).encode("utf-8")
_d1, _d2 = st.columns(2)
with _d1:
    st.download_button("📄 下载 PDF 版方案", data=_pdf_bytes, file_name="悦膳膳食方案.pdf",
                       mime="application/pdf", use_container_width=True)
with _d2:
    st.download_button("📋 下载 文本版（可微信转发）", data=_txt_bytes, file_name="悦膳膳食方案.txt",
                       mime="text/plain", use_container_width=True)
st.caption("PDF 版可直接打印交给营养师 / 家人；文本版方便微信转发。导出方案不含任何第三方标识，可放心分享。")

st.markdown("---")

# ================= ④ 全国就近买菜地图 =================
st.markdown("### 🗺️ 全国就近买菜地图（参考价）")
st.markdown(poi_mod.GEO_JS, unsafe_allow_html=True)
city = st.selectbox("选择城市（或授权定位）", ["全国概览"] + list(poi_mod.CITIES.keys()), index=0)

try:
    _qp = st.query_params
    _lat = _qp.get("lat"); _lng = _qp.get("lng")
except Exception:
    _raw = st.experimental_get_query_params()
    _lat = (_raw.get("lat") or [None])[0]
    _lng = (_raw.get("lng") or [None])[0]

user_center = None
if _lat and _lng:
    try:
        user_center = (float(_lat), float(_lng))
        st.success("已使用您的实时定位 📍")
    except Exception:
        pass

map_html = poi_mod.build_map_html(city=city, shopping=plan["shopping"], user_center=user_center)
st.components.v1.html(map_html, height=540)

st.markdown('<p class="disclaimer">地图门店坐标为「城市中心 + 全国连锁商超示意偏移」，以地图实际为准；'
            '标价为「参考价」非实时零售价。实时价格需商家数据接口，本作品为免费学习项目，不接入付费数据源。</p>', unsafe_allow_html=True)
st.markdown('<p class="disclaimer">免责声明：本方案为示例性推算，不构成医疗或营养诊断建议；'
            '如有疾病或特殊膳食需求，请咨询注册营养师或执业医师。</p>', unsafe_allow_html=True)
