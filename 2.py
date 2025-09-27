import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from streamlit_javascript import st_javascript
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math
import time

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
    "垃圾桶": "https://img.icons8.com/?size
