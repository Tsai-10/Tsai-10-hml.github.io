import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from streamlit_javascript import st_javascript
import json
from streamlit_autorefresh import st_autorefresh

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 載入設施資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Latitude\t": "Latitude", "Longtitude\t": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# =========================
# 設施圖標對應
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# =========================
# 側邊欄設定
# =========================
with st.sidebar:
    st.image("1.png", use_container_width=True)
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# =========================
# 預設位置
# =========================
user_lat, user_lon = 25.0330, 121.5654  # 預設台北101

# =========================
# 使用者自動定位
# =========================
location = st_javascript("""
navigator.geolocation.getCurrentPosition(
    (pos) => {
        window.parent.postMessage({type:'streamlit:setComponentValue', value: {latitude: pos.coords.latitude, longitude: pos.coords.longitude}}, '*');
    },
    (err) => {
        window.parent.postMessage({type:'streamlit:setComponentValue', value: {error: err.message}}, '*');
    },
    {enableHighAccuracy: true}
);
""", key="auto_location")

if location:
    if "error" in location:
        st.warning(f"⚠️ 定位失敗：{location['error']}")
    else:
        user_lat = location.get("latitude", user_lat)
        user_lon = location.get("longitude", user_lon)
        st.success(f"✅ 定位成功：({user_lat:.5f}, {user_lon:.5f})")

# =========================
# 手動輸入地址
# =========================
address_input = st.text_input("📍 請輸入地址（可選）")
if address_input:
    geolocator = Nominatim(user_agent="taipei_map_app")
    try:
        location_manual = geolocator.geocode(address_input, timeout=10)
        if location_manual:
            user_lat, user_lon = location_manual.latitude, location_manual.longitude
            st.success(f"✅ 已定位到輸入地址：({user_lat:.5f}, {user_lon:.5f})")
        else:
            st.error("❌ 找不到地址")
    except Exception as e:
        st.error(f"❌ 地址轉換失敗：{e}")

# =========================
# 自動刷新設定（每 5 秒刷新一次）
# =========================
st_autorefresh(interval=5000, key="auto_refresh")

# =========================
# 地圖與最近設施容器
# =========================
map_container = st.empty()

# =========================
# 篩選選擇類型
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()

# 計算距離
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user")
filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

# 一般設施 icon
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# 最近設施 icon（放大版） + 顯示距離
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 60,
    "height": 60,
    "anchorY": 60
})
nearest_df["tooltip"] = nearest_df.apply(lambda r: f"{r['Address']} ({int(r['distance_from_user'])} 公尺)", axis=1)

# 使用者位置
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

# 建立地圖圖層
layers = []

# 一般設施
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

# 最近設施
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

# 地圖視圖
view_state = pdk.ViewState(
    longitude=user_lon,
    latitude=user_lat,
    zoom=15,
    pitch=0,
    bearing=0
)

# 更新容器（不刷新整頁）
with map_container.container():
    st.pydeck_chart(pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{tooltip}"}
    ))

    st.subheader("🏆 最近的 5 個設施")
    nearest_df_display = nearest_df[["Type", "Address", "distance_from_user"]].copy()
    nearest_df_display["distance_from_user"] = nearest_df_display["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
    st.table(nearest_df_display.reset_index(drop=True))
