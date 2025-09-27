import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")

# =========================
# 模擬資料
# =========================
data = {
    "Name": ["設施A", "設施B", "設施C", "設施D", "設施E", "設施F"],
    "Type": ["飲水機", "廁所", "垃圾桶", "廁所", "飲水機", "垃圾桶"],
    "Latitude": [25.033964, 25.037531, 25.032805, 25.040857, 25.036123, 25.034752],
    "Longitude": [121.564468, 121.563392, 121.565123, 121.566412, 121.562345, 121.561234],
    "Address": ["地址1", "地址2", "地址3", "地址4", "地址5", "地址6"]
}
df = pd.DataFrame(data)

# =========================
# 使用者當前位置
# =========================
user_location = (25.0340, 121.5645)

# =========================
# 計算最近設施
# =========================
df["distance"] = df.apply(
    lambda row: geodesic(user_location, (row["Latitude"], row["Longitude"])).meters,
    axis=1
)
nearest_df = df.nsmallest(5, "distance")  # 最近 5 筆資料

# =========================
# Icon 設定
# =========================
# 1. 一般設施圖標
df["icon_data"] = df["Type"].map(lambda x: {
    "url": "https://cdn-icons-png.flaticon.com/512/854/854878.png",  # 一般設施小圖
    "width": 60,
    "height": 60,
    "anchorY": 60
})

# 2. 最近設施 Glow Marker
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": "https://cdn-icons-png.flaticon.com/512/875/875528.png",  # 發光圖標
    "width": 90,
    "height": 90,
    "anchorY": 90
})

# 3. 使用者位置圖標（橘紅色）
user_icon = pd.DataFrame([{
    "Latitude": user_location[0],
    "Longitude": user_location[1],
    "icon_data": {
        "url": "https://cdn-icons-png.flaticon.com/512/149/149060.png",  # 橘紅色圖標
        "width": 100,
        "height": 100,
        "anchorY": 100
    },
    "tooltip": "您的位置"
}])

# =========================
# Pydeck 圖層設定
# =========================
# 一般設施
layer_facilities = pdk.Layer(
    "IconLayer",
    data=df,
    get_icon="icon_data",
    get_position=["Longitude", "Latitude"],
    get_size=4,
    pickable=True,
    tooltip=True
)

# 最近設施 Glow
layer_nearest = pdk.Layer(
    "IconLayer",
    data=nearest_df,
    get_icon="icon_data",
    get_position=["Longitude", "Latitude"],
    get_size=6,
    pickable=True,
    tooltip=True
)

# 使用者位置
layer_user = pdk.Layer(
    "IconLayer",
    data=user_icon,
    get_icon="icon_data",
    get_position=["Longitude", "Latitude"],
    get_size=6,
    pickable=True,
    tooltip=True
)

# =========================
# 視覺化地圖
# =========================
view_state = pdk.ViewState(
    latitude=user_location[0],
    longitude=user_location[1],
    zoom=15
)

st.pydeck_chart(pdk.Deck(
    layers=[layer_facilities, layer_nearest, layer_user],
    initial_view_state=view_state,
    tooltip={"text": "{Name}\n{Address}"}
))
