import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_javascript import st_javascript

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("這是一個台北市公共設施地圖，支援手機定位功能。")

# =========================
# 手機定位功能
# =========================
st.subheader("📍 使用者定位")
location = st_javascript("""
    async () => {
        if (navigator.geolocation) {
            return new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        resolve({
                            latitude: pos.coords.latitude,
                            longitude: pos.coords.longitude,
                            success: true
                        });
                    },
                    (err) => {
                        resolve({
                            success: false,
                            message: err.message
                        });
                    }
                );
            });
        } else {
            return {success: false, message: "瀏覽器不支援定位功能"};
        }
    }
""")

user_lat = None
user_lon = None

if location:
    if location.get("success"):
        user_lat = location.get("latitude")
        user_lon = location.get("longitude")
        st.success(f"✅ 定位成功！您的座標是：({user_lat}, {user_lon})")
    else:
        st.error(f"❌ 定位失敗：{location.get('message')}")
else:
    st.info("等待定位中，請允許瀏覽器存取您的位置。")

# =========================
# 資料載入
# =========================
data_path = "data.csv"  # 替換成你的資料檔案
try:
    df = pd.read_csv(data_path)

    # 檢查必要欄位
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        st.error("資料缺少 Latitude 或 Longitude 欄位")
        st.stop()

    # 清理空值
    df = df.dropna(subset=["Latitude", "Longitude"])
except FileNotFoundError:
    st.error("找不到資料檔案，請確認 data.csv 是否存在。")
    st.stop()

# =========================
# 地圖顯示
# =========================
st.subheader("🗺️ 地圖展示")

layers = []

# 1. 公共設施資料
facility_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[Longitude, Latitude]',
    get_fill_color='[0, 128, 255, 160]',
    get_radius=50,
    pickable=True
)
layers.append(facility_layer)

# 2. 使用者位置標記
if user_lat and user_lon:
    user_df = pd.DataFrame({"Latitude": [user_lat], "Longitude": [user_lon]})
    user_layer = pdk.Layer(
        "ScatterplotLayer",
        data=user_df,
        get_position='[Longitude, Latitude]',
        get_fill_color='[255, 0, 0, 200]',  # 紅色
        get_radius=80,
        pickable=True
    )
    layers.append(user_layer)

# 設定地圖中心
initial_view_state = pdk.ViewState(
    latitude=user_lat if user_lat else 25.0330,  # 預設台北 101
    longitude=user_lon if user_lon else 121.5654,
    zoom=14,
    pitch=0
)

# 建立地圖
deck = pdk.Deck(
    layers=layers,
    initial_view_state=initial_view_state,
    tooltip={"text": "經度: {Longitude}\n緯度: {Latitude}"}
)

st.pydeck_chart(deck)
