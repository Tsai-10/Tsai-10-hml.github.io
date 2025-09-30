import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from streamlit_javascript import st_javascript
from geopy.distance import geodesic
import os

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")

# =========================
# 讀取資料
# =========================
# 載入公共設施 JSON
if os.path.exists("data.json"):
    with open("data.json", "r", encoding="utf-8") as f:
        facility_data = json.load(f)
    df = pd.DataFrame(facility_data)
else:
    st.error("找不到 data.json，請確認檔案是否存在。")
    st.stop()

# 確認經緯度欄位
if "Latitude" not in df.columns or "Longitude" not in df.columns:
    st.error("資料缺少 Latitude 或 Longitude 欄位")
    st.stop()

# =========================
# 取得使用者定位 (自動更新)
# =========================
user_location = st_javascript(
    "navigator.geolocation.getCurrentPosition((pos) => pos.coords);",
    key="get_location"
)

if not user_location:
    st.warning("等待定位中，請允許瀏覽器存取您的位置。")
    st.stop()

user_lat = user_location.get("latitude")
user_lon = user_location.get("longitude")

if user_lat is None or user_lon is None:
    st.warning("定位失敗，請確認是否允許存取位置。")
    st.stop()

# =========================
# 計算最近設施
# =========================
def calculate_nearest(user_lat, user_lon, data):
    data = data.copy()
    data["Distance"] = data.apply(lambda row: geodesic((user_lat, user_lon), (row["Latitude"], row["Longitude"])).meters, axis=1)
    return data.loc[data["Distance"].idxmin()]

nearest_facility = calculate_nearest(user_lat, user_lon, df)

# =========================
# pydeck 圖層設定
# =========================
# 公共設施
facility_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[Longitude, Latitude]',
    get_radius=30,
    get_color=[0, 128, 255],
    pickable=True,
    tooltip=True
)

# 寵物友善環境
pet_layer = None
if not pet_df.empty:
    pet_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pet_df,
        get_position='[Longitude, Latitude]',
        get_radius=50,
        get_color=[255, 165, 0],  # 橘色
        pickable=True,
        tooltip=True
    )

# 使用者位置
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([[user_lon, user_lat]], columns=['Longitude', 'Latitude']),
    get_position='[Longitude, Latitude]',
    get_radius=80,
    get_color=[255, 0, 0],  # 紅色
    pickable=False
)

# =========================
# tooltip 設定
# =========================
tooltip = {
    "html": "<b>名稱:</b> {Name}<br/><b>地址:</b> {Address}",
    "style": {"backgroundColor": "steelblue", "color": "white"}
}

# =========================
# 地圖呈現
# =========================
layers = [facility_layer, user_layer]
if pet_layer:
    layers.append(pet_layer)

view_state = pdk.ViewState(
    latitude=user_lat,
    longitude=user_lon,
    zoom=15
)

st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/streets-v11',
    initial_view_state=view_state,
    layers=layers,
    tooltip=tooltip
))

# =========================
# 最近設施資訊
# =========================
st.subheader("📍 離你最近的設施")
distance_km = nearest_facility["Distance"] / 1000
st.write(f"**名稱**: {nearest_facility['Name']} ")
st.write(f"**地址**: {nearest_facility['Address']} ")
st.write(f"**距離**: {distance_km:.2f} 公里")
