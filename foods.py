# -*- coding: utf-8 -*-
"""悦膳 · 营养知识库与膳食方案生成逻辑（零成本，无外部 API）

科学框架（均归源，不伪称独创）：
- 《中国居民膳食指南（2022）》八大准则：食物多样/谷类为主、吃动平衡、
  多吃蔬果奶类全谷大豆、适量鱼禽蛋瘦肉、少盐少油控糖、规律进餐足量饮水、
  会烹会选会看标签、公筷分餐杜绝浪费。
- 地中海饮食（Mediterranean diet）：以橄榄油为首选油脂、丰富蔬果与全谷、
  适量鱼类与禽肉、每周适量坚果、限制红肉与加工肉——被 NEJM、PREDIMED 等
  研究证明对心血管有益。
- DASH 饮食（得舒饮食）：高钾高镁高钙、低钠、丰富蔬果与低脂奶制品，用于
  血压管理。
- 食物营养成分近似取自《中国食物成分表》，每 100g 可食部。

本模块仅做示例性推算，不替代注册营养师或执业医师的专业评估。
"""

# 食物库：每 100g 可食部。flags 用于健康关注过滤。
# 类别 cat: 谷薯 / 蛋白 / 蔬菜 / 水果 / 坚果 / 油脂
# flags: low_gi, low_purine, moderate_purine, high_purine,
#        low_sodium, low_fat, high_fat, vegetarian, lean
FOODS = [
    # ---- 谷薯类（主食，粗细搭配） ----
    {"name": "燕麦(干)", "cat": "谷薯", "kcal": 367, "p": 15.0, "f": 6.7, "c": 61.0, "flags": ["low_gi", "low_purine", "low_sodium", "vegetarian"]},
    {"name": "糙米(干)", "cat": "谷薯", "kcal": 368, "p": 7.9, "f": 2.9, "c": 77.0, "flags": ["low_gi", "low_purine", "low_sodium", "vegetarian"]},
    {"name": "糙米饭(熟)", "cat": "谷薯", "kcal": 123, "p": 2.9, "f": 0.9, "c": 25.5, "flags": ["low_gi", "low_purine", "low_sodium", "vegetarian"]},
    {"name": "全麦面包", "cat": "谷薯", "kcal": 246, "p": 9.0, "f": 3.4, "c": 49.0, "flags": ["low_gi", "low_sodium", "vegetarian"]},
    {"name": "红薯", "cat": "谷薯", "kcal": 86, "p": 1.6, "f": 0.1, "c": 20.0, "flags": ["low_gi", "low_purine", "low_sodium", "vegetarian"]},
    {"name": "玉米", "cat": "谷薯", "kcal": 112, "p": 4.0, "f": 1.2, "c": 22.0, "flags": ["low_gi", "low_purine", "low_sodium", "vegetarian"]},
    {"name": "米饭(熟)", "cat": "谷薯", "kcal": 116, "p": 2.6, "f": 0.3, "c": 25.9, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    # ---- 蛋白类（亲民、易获得优先） ----
    {"name": "鸡胸肉", "cat": "蛋白", "kcal": 133, "p": 19.4, "f": 5.0, "c": 2.5, "flags": ["low_purine", "low_sodium", "low_fat", "lean"]},
    {"name": "鸡蛋", "cat": "蛋白", "kcal": 144, "p": 13.3, "f": 8.8, "c": 1.1, "flags": ["low_purine", "low_sodium", "low_fat"]},
    {"name": "豆腐", "cat": "蛋白", "kcal": 81, "p": 8.1, "f": 3.7, "c": 3.8, "flags": ["low_purine", "low_sodium", "vegetarian", "low_fat"]},
    {"name": "无糖豆浆", "cat": "蛋白", "kcal": 31, "p": 3.0, "f": 1.6, "c": 1.2, "flags": ["low_purine", "low_sodium", "vegetarian", "low_fat"]},
    {"name": "牛奶", "cat": "蛋白", "kcal": 54, "p": 3.0, "f": 3.2, "c": 3.4, "flags": ["low_purine", "low_sodium", "low_fat"]},
    {"name": "无糖酸奶", "cat": "蛋白", "kcal": 72, "p": 2.5, "f": 2.7, "c": 9.0, "flags": ["low_purine", "low_sodium", "low_fat"]},
    {"name": "瘦猪肉", "cat": "蛋白", "kcal": 143, "p": 20.3, "f": 6.2, "c": 1.5, "flags": ["moderate_purine", "low_sodium", "low_fat", "lean"]},
    {"name": "瘦牛肉", "cat": "蛋白", "kcal": 125, "p": 19.0, "f": 4.2, "c": 2.0, "flags": ["moderate_purine", "low_sodium", "low_fat", "lean"]},
    {"name": "鲫鱼", "cat": "蛋白", "kcal": 108, "p": 17.1, "f": 2.7, "c": 0.0, "flags": ["high_purine", "low_sodium", "low_fat"]},
    {"name": "带鱼", "cat": "蛋白", "kcal": 127, "p": 17.7, "f": 4.9, "c": 3.1, "flags": ["moderate_purine", "low_sodium", "low_fat"]},
    {"name": "虾", "cat": "蛋白", "kcal": 93, "p": 18.6, "f": 0.8, "c": 1.5, "flags": ["high_purine", "low_sodium", "low_fat"]},
    {"name": "猪肝", "cat": "蛋白", "kcal": 129, "p": 19.3, "f": 3.5, "c": 1.5, "flags": ["high_purine", "high_fat", "low_sodium"]},
    {"name": "毛豆(熟)", "cat": "蛋白", "kcal": 131, "p": 13.1, "f": 5.0, "c": 10.5, "flags": ["moderate_purine", "low_sodium", "low_gi", "vegetarian"]},
    # ---- 蔬菜类（餐餐有蔬菜） ----
    {"name": "西兰花", "cat": "蔬菜", "kcal": 34, "p": 4.1, "f": 0.6, "c": 7.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "菠菜", "cat": "蔬菜", "kcal": 24, "p": 2.6, "f": 0.3, "c": 4.5, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    {"name": "西红柿", "cat": "蔬菜", "kcal": 18, "p": 0.9, "f": 0.2, "c": 3.9, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "黄瓜", "cat": "蔬菜", "kcal": 15, "p": 0.8, "f": 0.1, "c": 2.9, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "小白菜", "cat": "蔬菜", "kcal": 15, "p": 1.5, "f": 0.2, "c": 2.5, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    {"name": "胡萝卜", "cat": "蔬菜", "kcal": 39, "p": 1.0, "f": 0.2, "c": 9.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "冬瓜", "cat": "蔬菜", "kcal": 11, "p": 0.4, "f": 0.2, "c": 2.6, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "生菜", "cat": "蔬菜", "kcal": 15, "p": 1.4, "f": 0.2, "c": 2.9, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "青椒", "cat": "蔬菜", "kcal": 22, "p": 1.0, "f": 0.2, "c": 5.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "南瓜", "cat": "蔬菜", "kcal": 23, "p": 0.7, "f": 0.1, "c": 5.3, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    {"name": "香菇", "cat": "蔬菜", "kcal": 26, "p": 2.2, "f": 0.3, "c": 5.2, "flags": ["moderate_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "土豆", "cat": "蔬菜", "kcal": 77, "p": 2.0, "f": 0.1, "c": 17.0, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    # ---- 水果类（每天 200–350g） ----
    {"name": "苹果", "cat": "水果", "kcal": 52, "p": 0.3, "f": 0.2, "c": 14.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "蓝莓", "cat": "水果", "kcal": 57, "p": 0.7, "f": 0.3, "c": 14.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "橙子", "cat": "水果", "kcal": 47, "p": 0.8, "f": 0.2, "c": 12.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "猕猴桃", "cat": "水果", "kcal": 61, "p": 1.1, "f": 0.6, "c": 14.0, "flags": ["low_purine", "low_sodium", "low_gi", "vegetarian"]},
    {"name": "香蕉", "cat": "水果", "kcal": 89, "p": 1.1, "f": 0.3, "c": 23.0, "flags": ["low_purine", "low_sodium", "vegetarian"]},
    # ---- 坚果类（每周适量） ----
    {"name": "核桃", "cat": "坚果", "kcal": 654, "p": 15.0, "f": 65.0, "c": 14.0, "flags": ["low_purine", "low_sodium", "vegetarian", "high_fat"]},
    {"name": "杏仁", "cat": "坚果", "kcal": 578, "p": 21.0, "f": 51.0, "c": 22.0, "flags": ["low_purine", "low_sodium", "vegetarian", "high_fat"]},
    # ---- 油脂类（首选橄榄油） ----
    {"name": "橄榄油", "cat": "油脂", "kcal": 884, "p": 0.0, "f": 100.0, "c": 0.0, "flags": ["low_purine", "low_sodium", "vegetarian", "high_fat"]},
]

_FOOD_BY_NAME = {f["name"]: f for f in FOODS}


# ---------- 目标计算（Mifflin-St Jeor，国际通用） ----------
def compute_targets(sex, age, height, weight, activity, goal):
    """用 Mifflin-St Jeor 公式估算基础代谢 BMR，再按活动系数得 TDEE。

    蛋白质按 1.2–1.6 g/kg（中国居民膳食指南建议一般成人 1.0 g/kg 以上，
    运动/减脂/增肌人群可取更高；此处参考运动营养常用区间）。
    脂肪占 25–30%（指南建议 <30%）；碳水为剩余热量。
    """
    if sex == "男":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    factor = {"久坐": 1.2, "轻度活动": 1.375, "中度活动": 1.55, "高强度": 1.725}[activity]
    tdee = bmr * factor
    if goal == "减脂":
        kcal = tdee - 450
    elif goal == "增肌":
        kcal = tdee + 300
    elif goal == "健康管理":
        kcal = tdee - 120
    else:  # 维持
        kcal = tdee
    prot_per_kg = {"减脂": 1.6, "增肌": 1.6, "健康管理": 1.3, "维持": 1.2}[goal]
    protein_g = prot_per_kg * weight
    fat_g = (kcal * 0.27) / 9
    carb_g = (kcal - protein_g * 4 - fat_g * 9) / 4
    if carb_g < 0:
        carb_g = 0
    return {
        "bmr": round(bmr), "tdee": round(tdee), "kcal": round(kcal),
        "protein_g": round(protein_g, 1), "fat_g": round(fat_g, 1),
        "carb_g": round(carb_g, 1),
    }


# ---------- 基准餐次模板（真实可操作，非随机克数） ----------
# 设计原则（科学+可行性）：
#  · 早餐温和易得：全谷主食 + 蛋/奶/豆浆 + 水果（绝不用海鲜/红肉）
#  · 午晚餐：主食 + 一份优质蛋白（禽肉/豆制品/鱼轮换）+ 两份蔬菜 + 橄榄油
#  · 加餐：奶类/酸奶 + 少量坚果（地中海饮食特征）
#  · 食材均为菜市场/超市常见、价格亲民
# 每餐结构模板（真实可操作，非随机克数）。
# 每个 slot = (角色, 基准食材, 基准克数, 候选池, 是否整份不缩放)
# 候选池用于「多日循环」轮换：同类别、营养近似、菜场超市常见、价格亲民，
# 保证每天食材有变化但都达标、都可行、都不破坏健康关注约束。
MEAL_SLOTS = {
    "早餐": [
        ("主食", "燕麦(干)", 40, ["燕麦(干)", "糙米饭(熟)", "全麦面包", "红薯", "玉米"], False),
        ("蛋白蛋奶", "鸡蛋", 50, ["鸡蛋", "牛奶", "无糖酸奶", "豆腐"], False),
        ("蛋白蛋奶", "牛奶", 250, ["牛奶", "无糖豆浆", "无糖酸奶"], True),
        ("水果", "苹果", 150, ["苹果", "蓝莓", "橙子", "猕猴桃", "香蕉"], False),
    ],
    "午餐": [
        ("主食", "米饭(熟)", 200, ["米饭(熟)", "糙米饭(熟)", "燕麦(干)", "全麦面包", "红薯", "玉米"], False),
        ("优质蛋白", "鸡胸肉", 120, ["鸡胸肉", "瘦猪肉", "瘦牛肉", "豆腐", "带鱼", "鲫鱼"], False),
        ("蔬菜", "西兰花", 150, ["西兰花", "菠菜", "西红柿", "黄瓜", "小白菜", "生菜", "青椒", "冬瓜", "南瓜", "香菇", "胡萝卜", "土豆"], False),
        ("蔬菜", "西红柿", 150, ["西红柿", "菠菜", "黄瓜", "小白菜", "生菜", "青椒", "冬瓜", "南瓜", "西兰花", "胡萝卜"], False),
        ("油脂", "橄榄油", 10, ["橄榄油"], True),
    ],
    "晚餐": [
        ("主食", "糙米饭(熟)", 150, ["糙米饭(熟)", "米饭(熟)", "燕麦(干)", "全麦面包", "红薯", "玉米"], False),
        ("优质蛋白", "豆腐", 150, ["豆腐", "鸡胸肉", "瘦猪肉", "鸡蛋", "带鱼", "鲫鱼"], False),
        ("蔬菜", "菠菜", 150, ["菠菜", "西兰花", "西红柿", "黄瓜", "小白菜", "生菜", "青椒", "冬瓜", "南瓜", "香菇"], False),
        ("蔬菜", "胡萝卜", 100, ["胡萝卜", "西红柿", "黄瓜", "小白菜", "生菜", "青椒", "冬瓜", "南瓜", "西兰花"], False),
        ("油脂", "橄榄油", 8, ["橄榄油"], True),
    ],
    "加餐": [
        ("奶类", "无糖酸奶", 200, ["无糖酸奶", "牛奶"], True),
        ("坚果", "核桃", 15, ["核桃", "杏仁"], True),
    ],
}
# 这些「整份」食材不随热量缩放（避免半个鸡蛋/半盒奶的尴尬）
FIXED_PORTION = {"鸡蛋", "牛奶", "无糖酸奶", "核桃", "橄榄油", "杏仁"}

# 动物性蛋白（素食方案需替换为植物蛋白）
ANIMAL_PROTEIN = {"鸡胸肉", "瘦猪肉", "瘦牛肉", "带鱼", "鲫鱼", "虾", "猪肝"}
# 高 / 中嘌呤（痛风方案需规避，替换为植物蛋白或蔬菜）
_HIGH_PURINE = {"虾", "鲫鱼", "带鱼", "猪肝"}
_MOD_PURINE = {"毛豆(熟)", "瘦牛肉"}

# 条件替换规则：原食材 -> 替换食材（按健康关注）
_SWAP = {
    "高血糖": {"米饭(熟)": "糙米饭(熟)"},
    "高血脂": {"瘦猪肉": "豆腐", "核桃": "核桃"},  # 高血脂时核桃减量为 10g（见下方处理）
    "素食": {"鸡胸肉": "豆腐", "瘦猪肉": "毛豆(熟)"},
}


def _swap_name(name, conditions):
    for cond in conditions:
        if cond in _SWAP and name in _SWAP[cond]:
            return _SWAP[cond][name]
    return name


def _build_day(conds, factor, day_index, taste):
    """生成第 day_index 天的一日方案（含当日购物清单）。"""
    meals = {}
    day_shop = {}
    oil_adj = {"清淡": -2, "家常": 0, "浓郁": 1}.get(taste, 0)
    for meal, slots in MEAL_SLOTS.items():
        items = []
        for (role, base_name, base_g, pool, fixed) in slots:
            cand = pool[day_index % len(pool)]
            name = _swap_name(cand, conds)
            # 素食：规避一切动物蛋白
            if "素食" in conds and name in ANIMAL_PROTEIN:
                name = "豆腐"
            nf = _FOOD_BY_NAME[name]
            # 痛风：规避高 / 中嘌呤
            if "痛风" in conds and name in _HIGH_PURINE:
                name = "豆腐"; nf = _FOOD_BY_NAME["豆腐"]
            elif "痛风" in conds and name in _MOD_PURINE:
                name = "西兰花"; nf = _FOOD_BY_NAME["西兰花"]
            # 份量
            if name == "橄榄油":
                ng = max(5, base_g + oil_adj)
            elif name in FIXED_PORTION or fixed:
                ng = base_g
            else:
                ng = max(10, round(base_g * factor / 5) * 5)
            # 高血脂坚果减量
            if name == "核桃" and "高血脂" in conds:
                ng = 10
            # 忌口过滤
            skip = False
            for c in conds:
                if c.startswith("忌口:"):
                    key = c[3:].strip()
                    if key and key in name:
                        skip = True
            if skip:
                continue
            it = _item(nf, ng)
            items.append(it)
            day_shop[name] = day_shop.get(name, 0) + it["g"]
        if items:
            meals[meal] = _sum_meal(items)
    return meals, [{"name": k, "g": round(v)} for k, v in day_shop.items()]


def build_plan(targets, conditions, prefs=None, days=1, portion=1.0, taste="家常"):
    """生成 1~N 天循环膳食方案。

    conditions: list[str]，可含 高血压/高血糖/高血脂/痛风/忌口:xxx
    prefs: str，可选 "素食"（按蛋奶素处理，最易执行且营养完整）
    days: 循环天数（1/3/5/7）；portion: 份量系数（0.85/1.0/1.15）；taste: 家常/清淡/浓郁
    """
    conds = list(conditions or [])
    is_veg = (prefs == "素食")
    if is_veg and "素食" not in conds:
        conds = conds + ["素食"]

    # 基准总热量（第 0 天模板）用于缩放
    base_kcal = 0
    for meal, slots in MEAL_SLOTS.items():
        for (role, base_name, base_g, pool, fixed) in slots:
            f = _FOOD_BY_NAME[base_name]
            base_kcal += f["kcal"] * base_g / 100.0
    factor = (targets["kcal"] / base_kcal) * portion if base_kcal else 1.0

    day_plans = []
    total_shop = {}
    for d in range(max(1, int(days))):
        meals, shop = _build_day(conds, factor, d, taste)
        day_plans.append({"label": f"第{d + 1}天", "meals": meals, "shopping": shop})
        for s in shop:
            total_shop[s["name"]] = total_shop.get(s["name"], 0) + s["g"]

    shopping_total = [{"name": k, "g": round(v)} for k, v in total_shop.items()]
    first = day_plans[0]
    return {
        "days": day_plans,
        "shopping_total": shopping_total,
        "targets": targets,
        # 兼容旧调用（单日等价于第 1 天）
        "meals": first["meals"],
        "shopping": first["shopping"],
    }


def _item(food, g):
    return {
        "name": food["name"], "g": round(g),
        "kcal": round(food["kcal"] * g / 100.0),
        "p": round(food["p"] * g / 100.0, 1),
        "f": round(food["f"] * g / 100.0, 1),
        "c": round(food["c"] * g / 100.0, 1),
    }


def _sum_meal(items):
    tot = {"kcal": 0, "p": 0.0, "f": 0.0, "c": 0.0}
    for it in items:
        tot["kcal"] += it["kcal"]; tot["p"] += it["p"]
        tot["f"] += it["f"]; tot["c"] += it["c"]
    return {
        "items": items,
        "kcal": tot["kcal"],
        "p": round(tot["p"], 1), "f": round(tot["f"], 1), "c": round(tot["c"], 1),
    }


# ---------- 解释（归源权威指南） ----------
def explanation(goal, conditions, taste="家常"):
    base = [
        "【中国居民膳食指南2022】食物多样、谷类为主：每天谷薯类 250–400g，其中全谷物和杂豆 50–150g；餐餐有蔬菜（300–500g/天），天天吃水果（200–350g/天，不能代替蔬菜）。",
        "【中国居民膳食指南2022】适量吃鱼、禽、蛋、瘦肉，优先白肉与豆制品；每天奶及奶制品 300ml 以上；大豆及坚果类 25–35g/天。",
        "【地中海饮食】以橄榄油为首选烹饪油，丰富蔬果与全谷，适量鱼类禽肉、每周少量坚果，限制红肉与加工肉——对心血管代谢有益。",
        "【中国居民膳食指南2022】少盐（<5g/天）、少油（25–30g/天）、控糖，清淡饮食；吃动平衡，规律三餐，足量饮水。",
    ]
    if taste == "清淡":
        base.append("【口味·清淡】少盐少油，多用蒸、煮、凉拌；以葱姜蒜、柠檬、醋、香草提鲜，减少酱油与烹调用油。")
    elif taste == "浓郁":
        base.append("【口味·浓郁】可用天然香辛料（黑胡椒、孜然、花椒、姜蒜、番茄）提味，少靠盐与糖；橄榄油可略增。")
    if "减脂" in (goal or ""):
        base.append("减脂：制造约 450 kcal/天 缺口，蛋白质足量（1.6 g/kg）以保留瘦体重，主食粗细搭配稳住血糖，避免节食导致的肌肉流失。")
    if "增肌" in (goal or ""):
        base.append("增肌：适度盈余热量（+300 kcal/天），蛋白质提高至 1.6 g/kg，并配合抗阻训练才能见效。")
    if "高血糖" in conditions:
        base.append("【血糖管理】主食选低 GI 的燕麦/糙米/杂粮，少吃精白米面与粥；水果选低 GI 品种（苹果、蓝莓、猕猴桃），避开荔枝、熟透香蕉等高糖水果；定时定量进餐。")
    if "高血压" in conditions:
        base.append("【血压管理·DASH】严格限盐（<5g/天），多用蔬菜瓜果补钾，少吃腌制与加工食品，控制饮酒；本方案已用橄榄油并控制钠。")
    if "高血脂" in conditions:
        base.append("【血脂管理】限制肥肉、内脏与过量坚果油，优选鱼类、禽肉、豆制品；本方案已去掉猪肝、减少坚果用量，并以橄榄油替代动物油。")
    if "痛风" in conditions:
        base.append("【痛风注意】避免动物内脏、带壳海鲜（虾蟹）与浓肉汤（高嘌呤）；多选蛋、奶、蔬菜、低糖水果；豆类在缓解期可适量，急性发作期遵医嘱。")
    if "素食" in conditions:
        base.append("【素食方案】按蛋奶素设计，以豆腐/豆浆/毛豆补充植物蛋白，搭配蛋奶保证优质蛋白与钙；注意补充铁（深绿色蔬菜）与维生素 B12（必要时强化食品）。")
    return base


if __name__ == "__main__":
    t = compute_targets("女", 20, 162, 55, "轻度活动", "减脂")
    plan = build_plan(t, ["高血糖"])
    print("目标:", t)
    for m, d in plan["meals"].items():
        print(f"{m}: {d['kcal']}kcal P{d['p']} F{d['f']} C{d['c']}")
        for it in d["items"]:
            print("   -", it["name"], it["g"], "g")
    print("购物清单:", [(s["name"], s["g"]) for s in plan["shopping"]])
    print("---- 解释 ----")
    for line in explanation("减脂", ["高血糖"]):
        print("·", line)
