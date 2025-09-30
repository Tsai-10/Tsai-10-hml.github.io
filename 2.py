import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")

# 載入資料
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df = df.dropna(subset=["Latitude","Longitude"])

# 使用者位置初始化
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654

# 自動定位
try:
    location = streamlit_js_eval(js_expressions="""
        new Promise((resolve) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({lat: pos.coords.latitude, lon: pos.coords.longitude}),
                    (err) => resolve({error: err.message})
                );
            } else {
                resolve({error: "不支援定位"});
            }
        })
    """, key="get_geolocation")
except Exception:
    location = None

if location and "lat" in location:
    st.session_state.user_lat = location["lat"]
    st.session_state.user_lon = location["lon"]

# 選擇顯示設施
facility_types = sorted(df["Type"].unique())
selected_types = st.multiselect("選擇設施類型", facility_types, default=facility_types)

# 計算距離 & 放大最近設施
user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance"] = filtered_df.apply(
    lambda r: geodesic((user_lat,user_lon),(r["Latitude"],r["Longitude"])).meters,
    axis=1
)
nearest_idx = filtered_df.nsmallest(5,"distance").index

ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

def make_icon(row):
    size = 70 if row.name in nearest_idx else 40
    return {
        "url": ICON_MAPPING.get(row["Type"], ""),
        "width": size,
        "height": size,
        "anchorY": size
    }

filtered_df["icon_data"] = filtered_df.apply(make_icon, axis=1)
filtered_df["tooltip"] = filtered_df.apply(lambda r: f"{r['Type']}\n{r['Address']}", axis=1)

# 使用者位置圖標
user_pos_df = pd.DataFrame([{
    "Type":"使用者位置",
    "Address":"您目前位置",
    "Latitude":user_lat,
    "Longitude":user_lon,
    "tooltip":"📍 您的位置",
    "icon_data":{
        "url": ICON_MAPPING["使用者位置"],
        "width":75,
        "height":75,
        "anchorY":75
    }
}])

# 地圖
layers=[]
for t in selected_types:
    sub_df = filtered_df[filtered_df["Type"]==t]
    if not sub_df.empty:
        layers.append(pdk.Layer(
            "IconLayer",
            data=sub_df,
            get_icon="icon_data",
            get_size=4,
            size_scale=12,
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

view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=15)
st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json", tooltip={"text":"{tooltip}"}))

# 表格 + 自動刷新
st.markdown("### 🏆 最近設施")
nearest_df = filtered_df.loc[nearest_idx, ["Type","Address","distance"]].copy()
nearest_df["distance"] = nearest_df["distance"].apply(lambda x:f"{x:.0f} 公尺")
st.dataframe(nearest_df.reset_index(drop=True), use_container_width=True)
