import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from streamlit_javascript import st_javascript
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math
import time

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 使用者定位
# =========================
st.subheader("📍 是否允許自動定位您的位置？")
allow_location = st.radio("請選擇：", ("是，我同意", "否，我不同意"), index=1)
user_lat, user_lon = 25.0330, 121.5654  # 預設台北101

if allow_location == "是，我同意":
    location = st_javascript("""
        navigator.geolocation.getCurrentPosition(
            (loc) => {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {latitude: loc.coords.latitude, longitude: loc.coords.longitude}
                }, '*');
            },
            (err) => {
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: null}, '*');
            }
        );
    """, key="get_location")
    if location and isinstance(location, dict):
        user_lat = location.get("latitude", user_lat)
        user_lon = location.get("longitude", user_lon)
        st.success(f"✅ 已自動定位：({user_lat:.5f}, {user_lon:.5f})")
    else:
        st.warning("⚠️ 無法取得定位，請手動輸入地址。")
else:
    st.info("ℹ️ 未啟用定位，請手動輸入地址。")

# =========================
# 手動輸入地址
# =========================
address_input = st.text_input("📍 請輸入地址（可選）")
if address_input:
    geolocator = Nominatim(user_agent="taipei_map_app")
    try:
        location = geolocator.geocode(address_input, timeout=10)
        if location:
            user_lat, user_lon = location.latitude, location.longitude
            st.success(f"✅ 已定位到輸入地址：({user_lat:.5f}, {user_lon:.5f})")
        else:
            st.error("❌ 找不到地址")
    except Exception as e:
        st.error(f"❌ 地址轉換失敗：{e}")

# =========================
# 載入設施資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# =========================
# 設施圖標對應
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/?size=100&id=114900&format=png&color=FF4500"
}

# =========================
# 側邊欄設定
# =========================
with st.sidebar:
    st.image("1.png", use_container_width=True)

    # 設施篩選
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

    # 切換地圖主題
    st.markdown("---")
    st.markdown("🗺️ **地圖主題**")
    map_theme = st.radio(
        "請選擇地圖樣式：",
        ("Carto Voyager（預設，彩色）", "Carto Light（乾淨白底）", "Carto Dark（夜間風格）", "OpenStreetMap 標準"),
        index=0
    )

    # 設定不同風格的 Map Style
    if map_theme == "Carto Voyager（預設，彩色）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    elif map_theme == "Carto Light（乾淨白底）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    elif map_theme == "Carto Dark（夜間風格）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    else:  # OSM 標準
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# =========================
# 過濾資料 & 加入 icon
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# =========================
# 使用者位置
# =========================
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {
        "url": ICON_MAPPING["使用者位置"],
        "width": 60,
        "height": 60,
        "anchorY": 80
    },
    "tooltip": "您目前的位置"
}])

# =========================
# 計算距離 & 找最近的 5 個設施
# =========================
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()

# 最近設施 icon + 動態外圈
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": "https://img.icons8.com/emoji/96/red-circle-emoji.png",  # 內圈紅色
    "width": 80,
    "height": 80,
    "anchorY": 80
})
nearest_df["tooltip"] = nearest_df["Address"]

# =========================
# 建立地圖圖層
# =========================
layers = []

# 一般設施圖層
for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"] == f_type]
    if sub_df.empty:
        continue
    layers.append(pdk.Layer(
        "IconLayer",
        data=sub_df,
        get_icon="icon_data",
        get_size=3,
        size_scale=12,
        get_position='[Longitude, Latitude]',
        pickable=True,
        auto_highlight=True,
        name=f_type
    ))

# 使用者位置圖層
layers.append(pdk.Layer(
    "IconLayer",
    data=user_pos_df,
    get_icon="icon_data",
    get_size=4,
    size_scale=20,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True
))

# 最近設施圖層：金色星形 + 光暈
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": "https://img.icons8.com/fluency/48/star.png",  # 金色星形
    "width": 80,
    "height": 80,
    "anchorY": 80
})
nearest_df["tooltip"] = nearest_df["Address"]

# IconLayer：顯示星形
layers.append(pdk.Layer(
    "IconLayer",
    data=nearest_df,
    get_icon="icon_data",
    get_size=6,
    size_scale=15,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True
))

# ScatterplotLayer：光暈
nearest_df["glow_radius"] = 150  # 固定半徑
nearest_df["glow_color"] = [[255, 69, 0, 120]] * len(nearest_df)  # 半透明紅橘色
layers.append(pdk.Layer(
    "ScatterplotLayer",
    data=nearest_df,
    get_position='[Longitude, Latitude]',
    get_radius="glow_radius",
    get_fill_color="glow_color",
    pickable=False
))

# =========================
# 地圖視圖
# =========================
view_state = pdk.ViewState(
    longitude=user_lon,
    latitude=user_lat,
    zoom=15,
    pitch=0,  # 保持平視
    bearing=0
)

# =========================
# 顯示地圖
# =========================
st.pydeck_chart(pdk.Deck(
    map_style=MAP_STYLE,
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text": "{tooltip}"}
))

