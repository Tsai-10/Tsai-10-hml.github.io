import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from geopy.distance import geodesic
from streamlit_autorefresh import st_autorefresh

# -------------------------
# 載入資料
# -------------------------
data_path = "data.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df = df.dropna(subset=["Latitude", "Longitude"])

ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# -------------------------
# 使用者位置
# -------------------------
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654

# -------------------------
# 選擇設施類型
# -------------------------
facility_types = sorted(df["Type"].unique().tolist())
selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# -------------------------
# 建立地圖 (只建立一次)
# -------------------------
def create_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()

    filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )

    # 最近 5 個設施
    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 70,
        "height": 70,
        "anchorY": 70
    })

    # 其他設施
    other_df = filtered_df[~filtered_df.index.isin(nearest_df.index)]

    # 使用者位置
    user_pos_df = pd.DataFrame([{
        "Type": "使用者位置",
        "Address": "您目前的位置",
        "Latitude": user_lat,
        "Longitude": user_lon,
        "icon_data": {
            "url": ICON_MAPPING["使用者位置"],
            "width": 75,
            "height": 75,
            "anchorY": 75
        }
    }])

    layers = []
    if not other_df.empty:
        layers.append(pdk.Layer(
            "IconLayer",
            data=other_df,
            get_icon="icon_data",
            get_size=4,
            size_scale=12,
            get_position='[Longitude, Latitude]',
            pickable=True,
            auto_highlight=True
        ))
    layers.append(pdk.Layer(
        "IconLayer",
        data=nearest_df,
        get_icon="icon_data",
        get_size=4,
        size_scale=25,
        get_position='[Longitude, Latitude]',
        pickable=True,
        auto_highlight=True
    ))
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

    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=15
    )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{Type}"}
    )

# 只建立一次地圖
if "map" not in st.session_state:
    st.session_state.map = create_map()
st.pydeck_chart(st.session_state.map)

# -------------------------
# 最近設施表格 (自動刷新)
# -------------------------
st_autorefresh(interval=5000, key="refresh_table")

user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user")[["Type", "Address", "distance_from_user"]].copy()
nearest_df["distance_from_user"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
st.markdown("### 🏆 最近設施")
st.dataframe(nearest_df.reset_index(drop=True), use_container_width=True)
