import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import json
import time

from streamlit_javascript import st_javascript

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("探索台北市便民設施地圖，支援即時定位與地址搜尋")

# =========================
# 初始化 session_state
# =========================
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330  # 台北市政府預設緯度
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654  # 台北市政府預設經度
if "accuracy" not in st.session_state:
    st.session_state.accuracy = None

# =========================
# 1. 即時定位
# =========================
location = st_javascript("""
    new Promise((resolve, reject) => {
        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(
                (pos) => resolve({
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                }),
                (err) => resolve({error: err.message}),
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        } else {
            resolve({error: "瀏覽器不支援定位"});
        }
    })
""")

if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location.get("lat", st.session_state.user_lat)
    st.session_state.user_lon = location.get("lon", st.session_state.user_lon)
    st.session_state.accuracy = location.get("accuracy", None)
elif location and "error" in location:
    st.warning(f"⚠️ 取得定位失敗：{location['error']}")

# =========================
# 2. 地址轉換函式（加入錯誤處理）
# =========================
geolocator = Nominatim(user_agent="taipei_city_walk_app")

def get_coordinates(address):
    """將地址轉換成經緯度，並加入錯誤處理"""
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            st.error("❌ 找不到該地址，請確認輸入是否正確")
            return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        st.error(f"❌ 地址轉換失敗，保持原位置：{e}")
        return None, None

# =========================
# 3. 手動地址輸入
# =========================
st.subheader("📍 手動搜尋地址")
address_input = st.text_input("輸入地址（例如：西門町、中正紀念堂...）")

if st.button("搜尋"):
    if address_input.strip():
        lat, lon = get_coordinates(address_input)
        if lat and lon:
            st.session_state.user_lat = lat
            st.session_state.user_lon = lon
            st.success(f"✅ 已將地圖定位到：{address_input} ({lat:.5f}, {lon:.5f})")
    else:
        st.warning("⚠️ 請輸入有效地址")

# =========================
# 4. 地圖顯示
# =========================
# 使用者位置圖層
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"lat": st.session_state.user_lat, "lon": st.session_state.user_lon}]),
    get_position="[lon, lat]",
    get_color=[255, 0, 0, 200],  # 紅色
    get_radius=30,
    tooltip="📍 您的位置",  # ✅ 已移除誤差顯示
)

# 地圖顯示設定
view_state = pdk.ViewState(
    latitude=st.session_state.user_lat,
    longitude=st.session_state.user_lon,
    zoom=15,
    pitch=0,
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/streets-v11",
    initial_view_state=view_state,
    layers=[user_layer],
    tooltip={"text": "📍 您的位置"},
))

# =========================
# 5. 底部狀態顯示
# =========================
st.markdown("---")
st.write(f"**目前定位**：{st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f}")
if st.session_state.accuracy:
    st.caption(f"定位精準度：±{st.session_state.accuracy:.1f} 公尺")
else:
    st.caption("定位精準度未知")
