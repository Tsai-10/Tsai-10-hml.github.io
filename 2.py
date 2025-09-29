import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
import time

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 使用者即時定位（每 10 秒更新一次）
# =========================
st.subheader("📍 目前位置（自動更新，每 10 秒）")

# 自動抓取使用者位置
location = streamlit_js_eval(
    js_expressions="""
    new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
            (pos) => resolve({lat: pos.coords.latitude, lon: pos.coords.longitude}),
            (err) => resolve({error: err.message}),
            {enableHighAccuracy: true, timeout: 5000}
        );
    });
    """,
    key=f"get_geolocation_{int(time.time() // 10)}"  # 每 10 秒重新取值
)

# 預設位置：台北 101
user_lat, user_lon = 25.0330, 121.5654

if location and isinstance(location, dict) and "lat" in location:
    user_lat = location.get("lat", user_lat)
    user_lon = location.get("lon", user_lon)
    st.success(f"✅ 使用者位置：({user_lat:.5f}, {user_lon:.5f})")
elif location and "error" in location:
    st.warning(f"⚠️ 無法自動定位：{location['error']}")

# =========================
# 手動輸入地址（備用）
# =========================
address_input = st.text_input("📍 或手動輸入地址：")
if address_input:
    geolocator = Nominatim(user_agent="taipei_map_app")
    try:
        addr_location = geolocator.geocode(address_input, timeout=10)
        if addr_location:
            user_lat, user_lon = addr_location.latitude, addr_location.longitude
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
df = df.rename(columns={"Longtitude": "Longitude", "Latitude": "Latitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# =========================
# 設施圖標對應
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# =========================
# 側邊欄設定
# =========================
with st.sidebar:
    st.image("1.png", width=250)

    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

    st.markdown("---")
    st.markdown("🗺️ **地圖主題**")
    map_theme = st.radio(
        "請選擇地圖樣式：",
        ("Carto Voyager（預設，彩色）", "Carto Light（乾淨白底）", "Carto Dark（夜間風格）", "OpenStreetMap 標準"),
        index=0
    )

    if map_theme == "Carto Voyager（預設，彩色）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    elif map_theme == "Carto Light（乾淨白底）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    elif map_theme == "Carto Dark（夜間風格）":
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    else:
        MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# =========================
# 計算距離 & 找最近的 5 個設施
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

# 一般設施 icon
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# 最近設施 icon（放大版）
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 60,
    "height": 60,
    "anchorY": 60
})
nearest_df["tooltip"] = nearest_df["Address"]

# 使用者位置
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {
        "url": ICON_MAPPING["使用者位置"],
        "width": 60,
        "height": 60,
        "anchorY": 60
    },
    "tooltip": "您目前的位置"
}])

# =========================
# 建立地圖圖層
# =========================
layers = []

# 一般設施
for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"] == f_type]
    if not sub_df.empty:
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

# 最近設施（放大）
layers.append(pdk.Layer(
    "IconLayer",
    data=nearest_df,
    get_icon="icon_data",
    get_size=4,
    size_scale=20,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True,
    name="最近設施"
))

# 使用者位置
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

# =========================
# 地圖視圖
# =========================
view_state = pdk.ViewState(
    longitude=user_lon,
    latitude=user_lat,
    zoom=15,
    pitch=0,
    bearing=0
)

st.pydeck_chart(pdk.Deck(
    map_style=MAP_STYLE,
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text": "{tooltip}"}
))

# =========================
# 顯示最近設施清單
# =========================
st.subheader("🏆 最近的 5 個設施")
nearest_df_display = nearest_df[["Type", "Address", "distance_from_user"]].copy()
nearest_df_display["distance_from_user"] = nearest_df_display["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
st.table(nearest_df_display.reset_index(drop=True))
