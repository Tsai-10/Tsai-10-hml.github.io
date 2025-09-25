import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from streamlit_javascript import st_javascript
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- 頁面設定 ---
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找飲水機、廁所、垃圾桶、狗便袋箱位置，並回報你發現的新地點 & 設施現況！")

# --- 使用者定位 ---
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

# --- 手動輸入地址 ---
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

# --- 載入設施資料 ---
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# --- 載入使用者回報資料 ---
feedback_file = "user_feedback.json"
if os.path.exists(feedback_file):
    with open(feedback_file, "r", encoding="utf-8") as f:
        feedback_data = json.load(f)
    df_feedback = pd.DataFrame(feedback_data)
    if not df_feedback.empty:
        if "Longtitude" in df_feedback.columns:
            df_feedback = df_feedback.rename(columns={"Longtitude": "Longitude"})
        df = pd.concat([df, df_feedback], ignore_index=True)

# --- 載入留言資料 ---
comment_file = "user_comments.json"
if os.path.exists(comment_file):
    with open(comment_file, "r", encoding="utf-8") as f:
        comments_data = json.load(f)
else:
    comments_data = []

# --- 設施圖標對應 ---
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=000000",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=000000",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=000000",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=000000",
    "使用者位置": "https://img.icons8.com/?size=100&id=114900&format=png&color=000000"
}

# --- 側邊欄 ---
with st.sidebar:
    st.image("1.png", use_container_width=True)
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# --- 過濾資料並加入 icon/tooltip ---
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# --- 使用者位置 ---
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {"url": ICON_MAPPING["使用者位置"], "width":50,"height":50,"anchorY":80},
    "tooltip": "您目前的位置"
}])

# --- 計算距離 & 最近設施 ---
for f_type in selected_types:
    filtered_df.loc[filtered_df["Type"]==f_type, "distance_from_user"] = filtered_df[filtered_df["Type"]==f_type].apply(
        lambda r: geodesic((user_lat, user_lon),(r["Latitude"], r["Longitude"])).meters, axis=1)

nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()

# --- 地圖圖層 ---
layers = []

# 設施圖層
for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"]==f_type]
    if sub_df.empty: continue
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

# 使用者位置圖層
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

# 最近設施小紅點（半透明 + 光暈）
nearest_df["fill_color"] = nearest_df.apply(lambda r:[255,0,0,180], axis=1)
nearest_df["radius"] = 15  # 小點
layers.append(pdk.Layer(
    "ScatterplotLayer",
    data=nearest_df,
    get_position='[Longitude, Latitude]',
    get_fill_color="fill_color",
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
    tooltip=True
))

# --- 地圖視圖 ---
view_state = pdk.ViewState(
    longitude=user_lon,
    latitude=user_lat,
    zoom=15,
    pitch=0,   # 俯視
    bearing=0
)

# --- 顯示地圖 ---
st.pydeck_chart(pdk.Deck(
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text":"{tooltip}"}
))
