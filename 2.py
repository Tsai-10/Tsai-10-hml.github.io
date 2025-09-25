import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic

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
user_location = [25.0345, 121.5658]  # 可改成 GPS 或地址搜尋

# 計算最近設施
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
    get_fill_color='[0, 128, 255, 160]',
    get_radius=60,
    pickable=True
)

# --- Layer 2: 最近設施的光暈（柔和大圈） ---
glow_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([nearest]),
    get_position='[lon, lat]',
    get_fill_color='[255, 215, 0, 80]',  # 金黃色低透明
    get_radius=200,
    radius_min_pixels=30,
    radius_max_pixels=60,
    pickable=False
)

# --- Layer 3: 最近設施的星形Icon ---
star_icon = {
    "url": "https://img.icons8.com/?size=100&id=21632&format=png&color=FFD700",
    "width": 100,
    "height": 100,
    "anchorY": 100
}

icon_data = pd.DataFrame([{
    "name": nearest["name"],
    "lat": nearest["lat"],
    "lon": nearest["lon"],
    "icon": star_icon
}])

icon_layer = pdk.Layer(
    "IconLayer",
    data=icon_data,
    get_icon="icon",
    get_position='[lon, lat]',
    get_size=5,
    size_scale=6,
    pickable=True
)

# --- Layer 4: 使用者位置 ---
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"lat": user_location[0], "lon": user_location[1]}]),
    get_position='[lon, lat]',
    get_fill_color='[0, 255, 0, 255]',
    get_radius=120,
    radius_min_pixels=10,
    radius_max_pixels=30,
    pickable=False
)

# --- 地圖設定 ---
view_state = pdk.ViewState(
    latitude=user_location[0],
    longitude=user_location[1],
    zoom=15,
    pitch=0
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v11",
    initial_view_state=view_state,
    layers=[all_facilities_layer, glow_layer, icon_layer, user_layer],
    tooltip={"text": "{name}"}
))

st.subheader(f"離你最近的設施：{nearest['name']} ({nearest['type']})")
st.write(f"距離：{nearest['distance']:.1f} 公尺")
