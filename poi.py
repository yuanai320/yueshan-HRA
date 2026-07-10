# -*- coding: utf-8 -*-
"""悦膳 · 全国商超 POI 与地图模块（零成本：Folium + OpenStreetMap）

说明：
- 覆盖全国主要城市；坐标为「城市中心点 + 商超示意偏移」。
- 门店按「实际在营」标注：仅标出该市真实存在的连锁品牌，不在营的一律不标，避免出现
  「该市根本没有的店」；每城另附「本地农贸市场 / 社区生鲜超市」作为零事实风险的便民兜底。
- 价格为「参考价」（元），非实时零售价；实时价需商家数据接口（本作品不接入）。
- 定位：优先使用浏览器定位（通过 query param 回传），失败则回退到所选城市中心。
"""

# 全国主要城市中心点（lat, lng）
CITIES = {
    "北京": (39.904, 116.407), "上海": (31.230, 121.474), "广州": (23.129, 113.264),
    "深圳": (22.543, 114.058), "成都": (30.572, 104.067), "杭州": (30.274, 120.155),
    "武汉": (30.593, 114.305), "西安": (34.341, 108.940), "南京": (32.060, 118.797),
    "重庆": (29.564, 106.551), "天津": (39.130, 117.200), "苏州": (31.299, 120.619),
    "青岛": (36.067, 120.383), "沈阳": (41.805, 123.431), "昆明": (25.038, 102.718),
    "哈尔滨": (45.803, 126.535), "长沙": (28.228, 112.938), "郑州": (34.746, 113.625),
    "厦门": (24.479, 118.089), "福州": (26.074, 119.296), "济南": (36.651, 117.120),
    "合肥": (31.821, 117.227), "南昌": (28.683, 115.857), "太原": (37.870, 112.548),
    "南宁": (22.817, 108.367), "贵阳": (26.647, 106.630), "兰州": (36.061, 103.834),
    "乌鲁木齐": (43.825, 87.616), "呼和浩特": (40.842, 111.751), "银川": (38.487, 106.230),
    "西宁": (36.617, 101.778), "石家庄": (38.042, 114.514), "大连": (38.914, 121.614),
    "宁波": (29.874, 121.551), "无锡": (31.491, 120.312), "东莞": (23.021, 113.752),
    "佛山": (23.022, 113.121), "常州": (31.811, 119.974), "珠海": (22.271, 113.576),
    "海口": (20.044, 110.199), "三亚": (18.253, 109.511),
    "秦皇岛": (39.945, 119.600),  # 家乡/实习地，保留
}

# 每城必备的便民买菜点（零事实风险：任何城市都有菜市场/社区生鲜超市）
_LOCAL_POIS = [("本地农贸市场", (0.010, -0.008)), ("社区生鲜超市", (-0.011, 0.012))]

# 各城市「实际在营」的全国连锁商超（保守标注：仅含确认在营的；不确定的一律不标，避免虚标）
# 说明：永辉 / 华润万家覆盖极广，几乎所有地级市在营；大润发仅在确认在营的城市标注；
#       秦皇岛、三亚、银川、西宁、呼和浩特、北京（大润发已大面积撤出）等均不标大润发。
_CITY_CHAINS = {
    "上海": ["永辉超市", "华润万家", "大润发"],
    "广州": ["永辉超市", "华润万家", "大润发"],
    "深圳": ["永辉超市", "华润万家", "大润发"],
    "成都": ["永辉超市", "华润万家", "大润发"],
    "杭州": ["永辉超市", "华润万家", "大润发"],
    "武汉": ["永辉超市", "华润万家", "大润发"],
    "西安": ["永辉超市", "华润万家", "大润发"],
    "南京": ["永辉超市", "华润万家", "大润发"],
    "重庆": ["永辉超市", "华润万家", "大润发"],
    "天津": ["永辉超市", "华润万家", "大润发"],
    "苏州": ["永辉超市", "华润万家", "大润发"],
    "青岛": ["永辉超市", "华润万家", "大润发"],
    "沈阳": ["永辉超市", "华润万家", "大润发"],
    "大连": ["永辉超市", "华润万家", "大润发"],
    "昆明": ["永辉超市", "华润万家", "大润发"],
    "哈尔滨": ["永辉超市", "华润万家", "大润发"],
    "长沙": ["永辉超市", "华润万家", "大润发"],
    "郑州": ["永辉超市", "华润万家", "大润发"],
    "厦门": ["永辉超市", "华润万家", "大润发"],
    "福州": ["永辉超市", "华润万家", "大润发"],
    "济南": ["永辉超市", "华润万家", "大润发"],
    "合肥": ["永辉超市", "华润万家", "大润发"],
    "南昌": ["永辉超市", "华润万家", "大润发"],
    "太原": ["永辉超市", "华润万家", "大润发"],
    "南宁": ["永辉超市", "华润万家", "大润发"],
    "贵阳": ["永辉超市", "华润万家", "大润发"],
    "石家庄": ["永辉超市", "华润万家", "大润发"],
    "兰州": ["永辉超市", "华润万家", "大润发"],
    "乌鲁木齐": ["永辉超市", "华润万家", "大润发"],
    "海口": ["永辉超市", "华润万家", "大润发"],
    "宁波": ["永辉超市", "华润万家", "大润发"],
    "无锡": ["永辉超市", "华润万家", "大润发"],
    "东莞": ["永辉超市", "华润万家", "大润发"],
    "佛山": ["永辉超市", "华润万家", "大润发"],
    "常州": ["永辉超市", "华润万家", "大润发"],
    "珠海": ["永辉超市", "华润万家", "大润发"],
    # 以下城市：仅标普惠连锁，不标大润发（实际无在营 / 已撤出）
    "北京": ["永辉超市", "华润万家"],
    "秦皇岛": ["永辉超市", "华润万家"],
    "三亚": ["永辉超市", "华润万家"],
    "银川": ["永辉超市", "华润万家"],
    "西宁": ["永辉超市", "华润万家"],
    "呼和浩特": ["永辉超市", "华润万家"],
}

# 盒马鲜生仅在部分一二线城市在营
_BOX_CITIES = {"北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安",
               "南京", "重庆", "苏州", "青岛", "长沙", "福州", "厦门", "宁波", "合肥", "东莞"}


def _pois_for(city, lat, lng):
    """生成单城市的 POI 列表：本地便民点 + 实际在营连锁 + 盒马（部分城市）。"""
    items = []
    for name, (dlat, dlng) in _LOCAL_POIS:
        items.append({"name": f"{name}（{city}）", "type": "菜场", "city": city,
                      "lat": round(lat + dlat, 5), "lng": round(lng + dlng, 5),
                      "note": "本地便民买菜点 · 示意坐标，以地图实际为准"})
    chains = _CITY_CHAINS.get(city, [])
    for i, name in enumerate(chains):
        items.append({"name": f"{name}（{city}店）", "type": "超市", "city": city,
                      "lat": round(lat + 0.013 - 0.004 * i, 5),
                      "lng": round(lng - 0.011 + 0.007 * i, 5),
                      "note": "全国连锁 · 示意坐标，以地图实际为准"})
    if city in _BOX_CITIES:
        items.append({"name": f"盒马鲜生（{city}店）", "type": "超市", "city": city,
                      "lat": round(lat - 0.006, 5), "lng": round(lng - 0.015, 5),
                      "note": "新零售 · 示意坐标，以地图实际为准"})
    return items


# 预生成各城市 POI
CITY_POIS = {_city: _pois_for(_city, _lat, _lng) for _city, (_lat, _lng) in CITIES.items()}

# 常见食材参考价（元 / 单位），全国通用近似值
REF_PRICE = {
    "燕麦(干)": (10.0, "元/500g"), "全麦面包": (12.0, "元/袋"), "红薯": (4.0, "元/500g"),
    "玉米": (5.0, "元/根"), "米饭(熟)": (3.0, "元/500g(米)"), "糙米饭(熟)": (6.0, "元/500g(米)"),
    "鸡胸肉": (12.0, "元/500g"), "鸡蛋": (5.0, "元/斤"), "豆腐": (3.0, "元/块"),
    "无糖豆浆": (4.0, "元/杯"), "牛奶": (6.0, "元/盒"), "无糖酸奶": (7.0, "元/杯"),
    "瘦猪肉": (15.0, "元/500g"), "瘦牛肉": (38.0, "元/500g"),
    "鲫鱼": (12.0, "元/500g"), "带鱼": (14.0, "元/500g"), "虾": (35.0, "元/500g"), "猪肝": (8.0, "元/500g"),
    "毛豆(熟)": (6.0, "元/300g"),
    "西兰花": (6.0, "元/500g"), "菠菜": (4.0, "元/500g"), "西红柿": (5.0, "元/500g"),
    "黄瓜": (3.0, "元/500g"), "小白菜": (3.5, "元/500g"), "胡萝卜": (3.0, "元/500g"),
    "冬瓜": (2.5, "元/500g"), "生菜": (4.0, "元/500g"), "青椒": (4.5, "元/500g"),
    "南瓜": (3.0, "元/500g"), "香菇": (9.0, "元/500g"), "土豆": (3.0, "元/500g"),
    "苹果": (6.0, "元/500g"), "蓝莓": (20.0, "元/盒"), "橙子": (7.0, "元/500g"),
    "猕猴桃": (10.0, "元/500g"), "香蕉": (4.5, "元/500g"),
    "核桃": (30.0, "元/500g"), "杏仁": (35.0, "元/500g"),
    "橄榄油": (45.0, "元/500ml"),
}


def haversine(a, b):
    import math
    lat1, lng1 = a; lat2, lng2 = b
    r = 6371.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dl = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def nearest_pois(pois, center, top_n=3):
    scored = []
    for p in pois:
        d = haversine(center, (p["lat"], p["lng"]))
        scored.append((d, p))
    scored.sort(key=lambda x: x[0])
    return scored[:top_n]


def price_for(food_name):
    if food_name in REF_PRICE:
        val, unit = REF_PRICE[food_name]
        return f"约{val}{unit}"
    return "参考价以门店为准"


def build_map_html(city=None, shopping=None, user_center=None, height=520):
    """生成 Folium 地图 HTML。user_center 优先；否则按城市；否则全国概览。"""
    try:
        import folium
    except Exception as e:  # pragma: no cover
        return f"<p style='color:#888'>地图组件未安装（folium）。请在 requirements 中包含 folium 后部署。{e}</p>"

    if user_center:
        center = list(user_center); zoom = 12
    elif city and city in CITIES:
        center = list(CITIES[city]); zoom = 12
    else:
        center = [35.0, 105.0]; zoom = 4

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    if user_center:
        folium.Marker(center, tooltip="您的位置（浏览器定位）",
                      icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(m)
        pois = []
        if city in CITY_POIS:
            pois = CITY_POIS[city]
    elif city in CITY_POIS:
        pois = CITY_POIS[city]
    else:
        # 全国概览：主要城市打点
        pois = []
        for c, (la, ln) in CITIES.items():
            folium.Marker([la, ln], tooltip=c,
                          icon=folium.Icon(color="green", icon="map-marker", prefix="fa")).add_to(m)
        html = m._repr_html_()
        return html

    near = nearest_pois(pois, center, top_n=3) if pois else []
    for d, p in near:
        popup = f"<b>{p['name']}</b><br>类型：{p['type']}<br>距中心约 {d:.1f} km<br>{p['note']}"
        folium.Marker([p["lat"], p["lng"]], tooltip=f"{p['name']} ({d:.1f}km)", popup=popup,
                      icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa")).add_to(m)

    if shopping:
        lines = ["<b>购物清单 · 就近参考价</b>"]
        for s in shopping:
            lines.append(f"· {s['name']}（{s['g']}g）：{price_for(s['name'])}")
        if near:
            lines.append(f"<br>最近商超：{near[0][1]['name']}（{near[0][0]:.1f}km）")
        folium.Marker([center[0] + 0.02, center[1]], tooltip="购物清单", popup="<br>".join(lines),
                      icon=folium.Icon(color="orange", icon="list", prefix="fa")).add_to(m)
    return m._repr_html_()


# 浏览器定位 JS：成功后通过 query param 回传，触发 Streamlit 重跑
GEO_JS = """
<script>
function yueshanGeo(){
  if(!navigator.geolocation){alert('当前浏览器不支持定位');return;}
  navigator.geolocation.getCurrentPosition(function(pos){
    var u=new URL(window.location.href);
    u.searchParams.set('lat', pos.coords.latitude.toFixed(5));
    u.searchParams.set('lng', pos.coords.longitude.toFixed(5));
    window.location.href = u.toString();
  }, function(err){alert('定位失败或被拒绝，已使用所选城市中心。');});
}
</script>
<button onclick="yueshanGeo()" style="background:#F5A623;color:#3a2a00;border:none;
  padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">
  使用我的位置（授权定位）
</button>
"""
