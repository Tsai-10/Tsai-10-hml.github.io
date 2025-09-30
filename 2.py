import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
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
# 載入 JSON 資料
# =========================
data_path = "data.json"
if not os.path.exists(data_path):
    st.error(f"❌ 找不到資料檔案，請確認 `{data_path}` 是否存在於專案目錄中")
    st.stop()

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cleaned_data = []
for d in data:
    cleaned_item = {}
    for k, v in d.items():
        key = k.strip()
        if key.lower() in ["longtitude", "longitude"]:
            key = "Longitude"
        elif key.lower() == "latitude":
            key = "Latitude"
        cleaned_item[key] = v
    cleaned_data.append(cleaned_item)

df = pd.DataFrame(cleaned_data)
df = df.dropna(subset=["Latitude", "Longitude"])
if df.empty:
    st.error("⚠️ 資料檔案載入成功，但內容為空，請確認 data.json 是否有正確資料。")
    st.stop()

# =========================
# 設施圖標
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# =========================
# 側邊欄
# =========================
with st.sidebar:
    st.image("1.png", width=250)
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# =========================
# 使用者位置初始化
# =========================
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654

# =========================
# 自動 GPS 定位
# =========================
st.subheader("📍 定位方式")
with st.spinner("等待定位中，請允許瀏覽器存取您的位置..."):
    try:
        location = streamlit_js_eval(js_expressions="""
            new Promise((resolve, reject) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => resolve({lat: pos.coords.latitude, lon: pos.coords.longitude}),
                        (err) => resolve({error: err.message})
                    );
                } else {
                    resolve({error: "瀏覽器不支援定位"});
                }
            })
        """, key="get_geolocation")
    except Exception:
        location = None

if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location.get("lat", st.session_state.user_lat)
    st.session_state.user_lon = location.get("lon", st.session_state.user_lon)
    st.success(f"✅ 已取得 GPS 位置：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
else:
    st.warning("⚠️ 無法自動定位，請輸入地址或使用預設位置。")

# =========================
# 更新地圖函數（僅渲染一次，不閃爍）
# =========================
def create_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    
    # 一般設施圖標
    filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })
    
    # 使用者位置
    user_pos_df = pd.DataFrame([{
        "Type": "使用者位置",
        "Address": "您目前的位置",
        "Latitude": user_lat,
        "Longitude": user_lon,
        "tooltip": "📍 您的位置",
        "icon_data": {
            "url": ICON_MAPPING["使用者位置"],
            "width": 60,
            "height": 60,
            "anchorY": 60
        }
    }])
    
    # 圖層
    layers = []
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
    # 最近設施圖標紅色填滿
    nearest_df = filtered_df.copy()
    nearest_df["distance_from_user"] = nearest_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = nearest_df.nsmallest(5, "distance_from_user").copy()
    nearest_df["tooltip"] = nearest_df.apply(
        lambda r: f"🏆 最近設施\n類型: {r['Type']}\n地址: {r['Address']}\n距離: {r['distance_from_user']:.0f} 公尺",
        axis=1
    )
    nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 60,
        "height": 60,
        "anchorY": 60,
        "tint": [255, 0, 0]  # 紅色填滿
    })
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

    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=15,
        pitch=0,
        bearing=0
    )
    
    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{tooltip}"}
    )

# =========================
# 顯示地圖一次
# =========================
map_container = st.empty()
with map_container:
    st.pydeck_chart(create_map())

# =========================
# 最近設施即時刷新
# =========================
table_container = st.empty()
REFRESH_INTERVAL = 5  # 秒

while True:
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = filtered_df.nsmallest(5, "distance_from_user")[["Type", "Address", "distance_from_user"]].copy()
    nearest_df["distance_from_user"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
    table_container.table(nearest_df.reset_index(drop=True))
    time.sleep(REFRESH_INTERVAL)
