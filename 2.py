import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
import json
import time

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="🏙 Taipei City Walk", layout="wide")
st.title("🏙 Taipei City Walk")
st.markdown("探索台北市便利設施，並自動定位最近的設施")

# =========================
# 1. 載入資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)

# 修正欄位名稱，確保經緯度欄位正確
df.columns = [col.strip() for col in df.columns]
df.rename(columns={"Longtitude": "Longitude"}, inplace=True)

# 檢查資料
st.write("資料預覽：", df.head())

# 移除經緯度缺失資料
df = df.dropna(subset=["Latitude", "Longitude"])

# =========================
# 2. 使用者定位
# =========================
st.markdown("### 📍 使用者定位")

# 模擬初始定位（可替換成自動定位）
default_location = (25.0330, 121.5654)  # 台北101

user_lat = st.number_input("輸入您的緯度", value=default_location[0], format="%.6f")
user_lon = st.number_input("輸入您的經度", value=default_location[1], format="%.6f")

user_location = (user_lat, user_lon)

st.success(f"目前定位：緯度 {user_lat:.6f}，經度 {user_lon:.6f}")

# =========================
# 3. 計算距離 & 找出最近設施
# =========================
df["Distance"] = df.apply(
    lambda row: geodesic(user_location, (row["Latitude"], row["Longitude"])).meters,
    axis=1
)

# 找出最近設施
nearest_facility = df.loc[df["Distance"].idxmin()]
st.markdown(
    f"### 🚀 最近設施：\n**{nearest_facility['Address']}**（距離 {nearest_facility['Distance']:.0f} 公尺）"
)

# =========================
# 4. 在地圖顯示距離資訊
# =========================
# 將距離資訊加入 Tooltip
df["Tooltip"] = df.apply(
    lambda row: f"{row['Address']}（距離 {row['Distance']:.0f} 公尺）",
    axis=1
)

# 設定地圖樣式
MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"

# 最近設施圖層 - 放大顯示
nearest_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([nearest_facility]),
    get_position='[Longitude, Latitude]',
    get_fill_color=[255, 0, 0, 200],
    get_radius=80,
    pickable=True
)

# 其他設施圖層
facility_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[Longitude, Latitude]',
    get_fill_color=[0, 128, 255, 160],
    get_radius=40,
    pickable=True
)

# 使用者位置圖層
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"Latitude": user_lat, "Longitude": user_lon}]),
    get_position='[Longitude, Latitude]',
    get_fill_color=[0, 255, 0, 255],
    get_radius=100,
    pickable=True
)

# 初始化地圖
view_state = pdk.ViewState(
    latitude=user_lat,
    longitude=user_lon,
    zoom=15,
    pitch=0
)

# 繪製地圖
st.pydeck_chart(pdk.Deck(
    map_style=MAP_STYLE,
    layers=[facility_layer, nearest_layer, user_layer],
    initial_view_state=view_state,
    tooltip={"text": "{Tooltip}"}
))

# =========================
# 5. 顯示最近設施詳細資訊
# =========================
st.markdown("### 📝 最近設施資訊")
st.json({
    "設施種類": nearest_facility["Type"],
    "地址": nearest_facility["Address"],
    "距離 (公尺)": round(nearest_facility["Distance"], 2)
})
