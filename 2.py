import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from streamlit_javascript import st_javascript
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from st_aggrid import AgGrid, GridOptionsBuilder

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 使用者定位
# =========================
st.subheader("📍 是否允許自動定位您的位置？")
allow_location = st.radio("請選擇：", ("是，我同意", "否，我不同意"), index=1)
user_lat, user_lon = 25.0330, 121.5654  # 預設台北101

if allow_location == "是，我同意":
    location = st_javascript("""
        navigator.geolocation.getCurrentPosition(
            (loc) => {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {latitude: loc.coords.latitude, longitude: loc.coords.longitude}
                }, '*');
            },
            (err) => {
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: null}, '*');
            }
        );
    """, key="get_location")
    if location and isinstance(location, dict):
        user_lat = location.get("latitude", user_lat)
        user_lon = location.get("longitude", user_lon)
        st.success(f"✅ 已自動定位：({user_lat:.5f}, {user_lon:.5f})")
    else:
        st.warning("⚠️ 無法取得定位，請手動輸入地址。")
else:
    st.info("ℹ️ 未啟用定位，請手動輸入地址。")

# =========================
# 手動輸入地址
# =========================
address_input = st.text_input("📍 請輸入地址（可選）")
if address_input:
    geolocator = Nominatim(user_agent="taipei_map_app")
    try:
        location = geolocator.geocode(address_input, timeout=10)
        if location:
            user_lat, user_lon = location.latitude, location.longitude
            st.success(f"✅ 已定位到輸入地址：({user_lat:.5f}, {user_lon:.5f})")
        else:
            st.error("❌ 找不到地址")
    except Exception as e:
        st.error(f"❌ 地址轉換失敗：{e}")

# =========================
# 載入設施資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# =========================
# 設施圖標對應
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "使用者位置": "https://img.icons8.com/?size=100&id=114900&format=png&color=FF4500"
}

# =========================
# 側邊欄設定
# =========================
with st.sidebar:
    st.image("1.png", use_container_width=True)

    # 設施篩選
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

    # 地圖主題
    st.markdown("---")
    st.markdown("🗺️ **地圖主題**")
    map_theme = st.radio(
        "請選擇地圖樣式：",
        ("Carto Voyager（預設，彩色）", "Carto Light（乾淨白底）", "Carto Dark（夜間風格）", "OpenStreetMap 標準"),
        index=0
    )
    MAP_STYLE = {
        "Carto Voyager（預設，彩色）": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        "Carto Light（乾淨白底）": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        "Carto Dark（夜間風格）": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        "OpenStreetMap 標準": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    }[map_theme]

# =========================
# 過濾資料 & 加入 icon
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# =========================
# 使用者位置
# =========================
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {
        "url": ICON_MAPPING["使用者位置"],
        "width": 60,
        "height": 60,
        "anchorY": 80
    },
    "tooltip": "您目前的位置"
}])

# =========================
# 計算距離 & 最近 5 個設施
# =========================
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
    "url": "https://img.icons8.com/fluency/96/marker.png",
    "width": 80,
    "height": 80,
    "anchorY": 80
})
nearest_df["tooltip"] = nearest_df["Address"]

# =========================
# 顯示最近設施列表
# =========================
nearest_df["距離(m)"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f}")
nearest_display = nearest_df[["Type", "Address", "距離(m)", "Latitude", "Longitude"]].copy()
st.subheader("🏆 最近的 5 個設施")
gb = GridOptionsBuilder.from_dataframe(nearest_display)
gb.configure_selection("single")
grid_options = gb.build()
grid_response = AgGrid(nearest_display, gridOptions=grid_options, height=200)

# =========================
# 判斷選中行
# =========================
if grid_response["selected_rows"]:
    sel_row = grid_response["selected_rows"][0]
    focus_lat, focus_lon = sel_row["Latitude"], sel_row["Longitude"]
else:
    # 預設聚焦第一個
    focus_lat, focus_lon = nearest_df.iloc[0]["Latitude"], nearest_df.iloc[0]["Longitude"]

# =========================
# 建立地圖圖層
# =========================
layers = []

# 一般設施
for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"] == f_type]
    if sub_df.empty:
        continue
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

# 最近設施 + 光暈
nearest_df["outer_color"] = [[255, 140, 0, 120]] * len(nearest_df)
layers.append(pdk.Layer(
    "ScatterplotLayer",
    data=nearest_df,
    get_position='[Longitude, Latitude]',
    get_radius=25,
    get_fill_color="outer_color",
    pickable=False
))
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
    map_style=MAP_STYLE,
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text": "{tooltip}"}
))


