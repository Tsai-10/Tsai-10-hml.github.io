import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.distance import geodesic

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 使用者位置（預設台北101）
# =========================
user_lat, user_lon = 25.0330, 121.5654

# =========================
# 載入資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# 設施圖標
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/?size=100&id=114900&format=png&color=FF4500"
}

# =========================
# 計算距離 & 最近5個設施
# =========================
df["distance_m"] = df.apply(lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1)
nearest_df = df.nsmallest(5, "distance_m").copy()
nearest_df["距離(公尺)"] = nearest_df["distance_m"].round(0)
nearest_df_display = nearest_df[["Type", "Address", "距離(公尺)"]]

st.subheader("🏆 最近 5 個設施")
selected_index = st.data_editor(
    nearest_df_display,
    num_rows="dynamic",
    use_container_width=True,
    key="nearest_table",
    disabled=False
)

# =========================
# 決定地圖聚焦
# =========================
if selected_index and selected_index.selected_rows:
    focus_row = nearest_df.iloc[selected_index.selected_rows[0]]
else:
    focus_row = nearest_df.iloc[0]  # 預設第一個最近設施
focus_lat, focus_lon = focus_row["Latitude"], focus_row["Longitude"]

# =========================
# 圖層
# =========================
layers = []

# 所有設施圖層
df["icon_data"] = df["Type"].map(lambda x: {"url": ICON_MAPPING.get(x, ""), "width": 40, "height": 40, "anchorY": 40})
layers.append(pdk.Layer(
    "IconLayer",
    data=df,
    get_icon="icon_data",
    get_size=3,
    size_scale=12,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True,
    name="所有設施"
))

# 使用者位置
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {"url": ICON_MAPPING["使用者位置"], "width": 60, "height": 60, "anchorY": 80},
    "tooltip": "您目前的位置"
}])
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

# 最近設施圖層
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {"url": "https://img.icons8.com/fluency/96/marker.png", "width": 80, "height": 80, "anchorY": 80})
layers.append(pdk.Layer(
    "IconLayer",
    data=nearest_df,
    get_icon="icon_data",
    get_size=6,
    size_scale=15,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True
))

# =========================
# 地圖視圖
# =========================
view_state = pdk.ViewState(
    longitude=focus_lon,
    latitude=focus_lat,
    zoom=17,
    pitch=0,
    bearing=0
)

# =========================
# 顯示地圖
# =========================
st.pydeck_chart(pdk.Deck(
    map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text": "{Address}"}
))
