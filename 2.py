import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from streamlit_javascript import st_javascript
from geopy.distance import geodesic
import time

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("探索台北市的公共設施位置，支援自動定位與最近設施推薦")

# =========================
# 使用者定位（自動更新）
# =========================
def get_user_location():
    """透過瀏覽器取得使用者定位"""
    loc = st_javascript("""
        async function getLocation() {
            return new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({latitude: pos.coords.latitude, longitude: pos.coords.longitude}),
                    (err) => resolve(null),
                    {enableHighAccuracy: true}
                );
            });
        }
        return await getLocation();
    """)
    return loc

with st.spinner("等待定位中，請允許瀏覽器存取您的位置..."):
    user_location = get_user_location()

if user_location is None:
    st.warning("無法取得您的位置，請確認瀏覽器定位權限已開啟。")
else:
    st.success(f"目前定位：Lat {user_location['latitude']}, Lng {user_location['longitude']}")

# =========================
# 載入 JSON 資料
# =========================
json_file = "data.json"

if not os.path.exists(json_file):
    st.error("找不到資料檔案，請確認 data.json 是否存在於目錄中。")
    st.stop()

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# JSON 轉 DataFrame
facilities = pd.DataFrame(data)

# 檢查必要欄位
if "Latitude" not in facilities.columns or "Longitude" not in facilities.columns:
    st.error("資料缺少 Latitude 或 Longitude 欄位，請確認 JSON 格式。")
    st.stop()

# =========================
# 篩選功能
# =========================
facility_types = sorted(facilities["Type"].unique())
selected_types = st.multiselect(
    "選擇設施類型",
    facility_types,
    default=facility_types
)
filtered_df = facilities[facilities["Type"].isin(selected_types)]

# =========================
# 計算最近設施
# =========================
def find_nearest_facility(user_lat, user_lng, df):
    """找出距離使用者最近的設施"""
    min_distance = float("inf")
    nearest_facility = None
    for _, row in df.iterrows():
        facility_location = (row["Latitude"], row["Longitude"])
        distance = geodesic((user_lat, user_lng), facility_location).meters
        if distance < min_distance:
            min_distance = distance
            nearest_facility = row
    return nearest_facility, min_distance

nearest_facility, nearest_distance = None, None
if user_location is not None:
    nearest_facility, nearest_distance = find_nearest_facility(
        user_location["latitude"],
        user_location["longitude"],
        filtered_df
    )

# =========================
# 地圖視覺化
# =========================
layers = []

# 設施點圖層
layers.append(pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position='[Longitude, Latitude]',
    get_fill_color=[255, 0, 0, 160],
    get_radius=50,
    pickable=True
))

# 使用者定位圖層
if user_location is not None:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([user_location]),
        get_position='[longitude, latitude]',
        get_fill_color=[0, 0, 255, 200],
        get_radius=80,
        pickable=True
    ))

# =========================
# Tooltip 設定
# =========================
tooltip = {
    "html": "<b>名稱:</b> {Name}<br/>"
            "<b>地址:</b> {Address}<br/>"
            "<b>類型:</b> {Type}",
    "style": {"backgroundColor": "steelblue", "color": "white"}
}

# =========================
# 地圖呈現
# =========================
if user_location is not None:
    initial_view_state = pdk.ViewState(
        latitude=user_location["latitude"],
        longitude=user_location["longitude"],
        zoom=15
    )
else:
    # 沒有定位資料時，預設中心在台北市政府
    initial_view_state = pdk.ViewState(latitude=25.0375, longitude=121.5637, zoom=13)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/streets-v11",
    layers=layers,
    initial_view_state=initial_view_state,
    tooltip=tooltip
))

# =========================
# 顯示最近設施資訊
# =========================
if nearest_facility is not None:
    st.subheader("📍 最近的設施")
    st.write(f"**名稱**: {nearest_facility['Name']}")
    st.write(f"**地址**: {nearest_facility['Address']}")
    st.write(f"**距離**: {nearest_distance:.2f} 公尺")
