import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# --- 頁面設定 ---
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ 台北生活便民地圖")

# --- 模擬資料：設施座標 ---
data = pd.DataFrame({
    "name": ["飲水機A", "廁所B", "垃圾桶C", "飲水機D"],
    "lat": [25.0335, 25.0378, 25.0302, 25.0350],
    "lon": [121.5651, 121.5635, 121.5705, 121.5668],
    "type": ["飲水機", "廁所", "垃圾桶", "飲水機"]
})

# --- 使用者目前位置 ---
user_location = [25.0345, 121.5658]  # 可改為 GPS 或輸入地址

# 計算距離，找出最近設施
def find_nearest_facility(user_loc, df):
    df["distance"] = df.apply(
        lambda row: geodesic(user_loc, (row["lat"], row["lon"])).meters,
        axis=1
    )
    return df.loc[df["distance"].idxmin()]

nearest = find_nearest_facility(user_location, data)

# --- Layer 1: 所有設施標記 ---
all_facilities_layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position='[lon, lat]',
    get_fill_color='[0, 128, 255, 160]',  # 藍色系透明
    get_radius=60,
    pickable=True,
    tooltip=True
)

# --- Layer 2: 最近設施「Glow發光效果」 ---
glow_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([nearest]),
    get_position='[lon, lat]',
    get_fill_color='[255, 215, 0, 255]',  # 金黃色
    get_radius=200,  # 半徑大，呈現光暈
    radius_min_pixels=15,
    radius_max_pixels=50,
    pickable=True,
    tooltip=True,
    opacity=0.5
)

# --- Layer 3: 最近設施中心標記（更精準） ---
center_marker_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([nearest]),
    get_position='[lon, lat]',
    get_fill_color='[255, 0, 0, 255]',  # 紅色中心點
    get_radius=80,
    radius_min_pixels=10,
    radius_max_pixels=25,
    pickable=True,
    tooltip=True
)

# --- Layer 4: 使用者位置 ---
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"lat": user_location[0], "lon": user_location[1]}]),
    get_position='[lon, lat]',
    get_fill_color='[0, 255, 0, 255]',  # 綠色代表使用者
    get_radius=120,
    radius_min_pixels=10,
    radius_max_pixels=30,
    pickable=True,
    tooltip=True
)

# --- 地圖視覺化 ---
view_state = pdk.ViewState(
    latitude=user_location[0],
    longitude=user_location[1],
    zoom=15,
    pitch=40
)

# 使用高級 Mapbox Style（乾淨淺色底圖）
map_style = "mapbox://styles/mapbox/light-v11"

st.pydeck_chart(
    pdk.Deck(
        map_style=map_style,
        initial_view_state=view_state,
        layers=[all_facilities_layer, glow_layer, center_marker_layer, user_layer],
        tooltip={"text": "{name}\n距離最近設施"}
    )
)

st.subheader(f"離你最近的設施是：{nearest['name']} ({nearest['type']})")
st.write(f"距離：{nearest['distance']:.1f} 公尺")
