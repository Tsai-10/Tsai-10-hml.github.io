import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並即時更新最近距離！")

# =========================
# 載入資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Latitude\t": "Latitude", "Longtitude\t": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# =========================
# 側邊欄選擇
# =========================
with st.sidebar:
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# =========================
# 地圖樣式
# =========================
MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"

# =========================
# 自動刷新頁面（非阻塞）
# =========================
st_autorefresh = st.experimental_data_editor if hasattr(st, "experimental_data_editor") else st.empty  # 保險 fallback

st.experimental_rerun() if st_autorefresh else None  # 可搭配下一段刷新機制

# =========================
# 使用者位置
# =========================
location = streamlit_js_eval(
    js_expressions="""
    navigator.geolocation.getCurrentPosition(
        (pos) => ({lat: pos.coords.latitude, lon: pos.coords.longitude}),
        (err) => ({error: err.message})
    )
    """,
    key="get_geolocation"
)

if location and "lat" in location:
    user_lat, user_lon = location["lat"], location["lon"]
    st.success(f"✅ 使用者位置：({user_lat:.5f}, {user_lon:.5f})")
else:
    user_lat, user_lon = 25.0330, 121.5654
    st.warning("⚠️ 無法取得定位，使用預設位置台北101")

# =========================
# 計算距離 & 最近五個設施
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

# 設置圖標和 tooltip
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 60,
    "height": 60,
    "anchorY": 60
})
nearest_df["tooltip"] = nearest_df.apply(
    lambda r: f"{r['Address']}\n距離 {r['distance_from_user']:.0f} 公尺", axis=1
)

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
# 建立圖層
# =========================
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

view_state = pdk.ViewState(longitude=user_lon, latitude=user_lat, zoom=15, pitch=0, bearing=0)
st.pydeck_chart(pdk.Deck(map_style=MAP_STYLE, initial_view_state=view_state, layers=layers, tooltip={"text": "{tooltip}"}))

# =========================
# 顯示最近設施清單
# =========================
st.subheader("🏆 最近的 5 個設施")
nearest_df_display = nearest_df[["Type", "Address", "distance_from_user"]].copy()
nearest_df_display["distance_from_user"] = nearest_df_display["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
st.table(nearest_df_display.reset_index(drop=True))
