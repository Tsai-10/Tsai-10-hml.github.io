import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置")

# =========================
# 前端抓 GPS
# =========================
st.subheader("📍 即時定位")

st.markdown("""
<div id="location_status">正在取得位置…</div>
<script>
navigator.geolocation.getCurrentPosition(
    (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        document.getElementById("location_status").innerHTML = 
            "✅ 取得位置: " + lat.toFixed(5) + ", " + lon.toFixed(5);
        // 傳回 Streamlit
        const input = window.parent.document.getElementById("user_latlon");
        if(input){
            input.value = lat + "," + lon;
            input.dispatchEvent(new Event('change'));
        }
    },
    (err) => {
        document.getElementById("location_status").innerHTML = "⚠️ 無法取得位置，請手動輸入";
    },
    { enableHighAccuracy: true }
)
</script>
""", unsafe_allow_html=True)

# 隱藏欄位存前端抓到的經緯度
user_latlon = st.text_input("user_latlon", value="", key="user_latlon")

# =========================
# 經緯度處理
# =========================
if user_latlon:
    try:
        user_lat, user_lon = map(float, user_latlon.split(","))
    except:
        user_lat, user_lon = 25.0330, 121.5654  # 預設台北101
else:
    user_lat, user_lon = 25.0330, 121.5654  # 預設台北101

st.write(f"使用者位置：({user_lat:.5f}, {user_lon:.5f})")

# =========================
# 載入設施資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

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
# 側邊欄選擇
# =========================
with st.sidebar:
    facility_types = sorted(df["Type"].unique())
    selected_types = st.multiselect("選擇設施類型", facility_types, default=facility_types)

# =========================
# 計算距離 & 找最近 5 個
# =========================
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user")

# =========================
# 建立圖層
# =========================
layers = []

for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"]==f_type]
    if not sub_df.empty:
        sub_df["icon_data"] = sub_df["Type"].map(lambda x: {"url": ICON_MAPPING[x], "width":40, "height":40, "anchorY":40})
        sub_df["tooltip"] = sub_df["Address"]
        layers.append(pdk.Layer(
            "IconLayer",
            data=sub_df,
            get_icon="icon_data",
            get_size=3,
            size_scale=12,
            get_position='[Longitude, Latitude]',
            pickable=True,
            auto_highlight=True
        ))

# 使用者位置
user_df = pd.DataFrame([{
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {"url": ICON_MAPPING["使用者位置"], "width":60, "height":60, "anchorY":60},
    "tooltip": "您目前的位置"
}])
layers.append(pdk.Layer(
    "IconLayer",
    data=user_df,
    get_icon="icon_data",
    get_size=4,
    size_scale=20,
    get_position='[Longitude, Latitude]',
    pickable=True
))

# =========================
# 地圖
# =========================
view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=15)
st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, map_style="carto-voyager"))

# 顯示最近設施清單
st.subheader("🏆 最近的 5 個設施")
nearest_df_display = nearest_df[["Type", "Address", "distance_from_user"]].copy()
nearest_df_display["distance_from_user"] = nearest_df_display["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
st.table(nearest_df_display.reset_index(drop=True))
