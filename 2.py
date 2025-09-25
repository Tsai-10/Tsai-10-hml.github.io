import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic

# ========== 頁面設定 ==========
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙 台北生活便民地圖")

# ========== 模擬設施資料 ==========
data = {
    "name": ["飲水機A", "廁所B", "垃圾桶C", "飲水機D"],
    "lat": [25.033968, 25.035, 25.032, 25.036],
    "lon": [121.564468, 121.565, 121.566, 121.563],
    "type": ["飲水機", "廁所", "垃圾桶", "飲水機"]
}
df = pd.DataFrame(data)

# ========== 使用者位置 ==========
user_location = [25.0335, 121.5651]  # 預設在台北101附近
st.sidebar.subheader("📍 使用者定位")
st.sidebar.write(f"經度: {user_location[1]:.6f}, 緯度: {user_location[0]:.6f}")

# ========== 找出最近的設施 ==========
def find_nearest(user_loc, df):
    df["distance"] = df.apply(
        lambda row: geodesic(user_loc, (row["lat"], row["lon"])).meters,
        axis=1
    )
    return df.loc[df["distance"].idxmin()]

nearest = find_nearest(user_location, df)

# ========== pydeck 圖層 ==========
# 其他設施標記
other_facilities_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df[df["name"] != nearest["name"]],
    get_position='[lon, lat]',
    get_color='[120,120,120,150]',  # 半透明灰色
    get_radius=40,
    pickable=True
)

# 最近設施特殊 ICON 標記
nearest_layer = pdk.Layer(
    "IconLayer",
    data=pd.DataFrame([nearest]),
    get_position='[lon, lat]',
    get_icon='icon_data',
    get_size=6,
    size_scale=8,
    pickable=True,
    icon_atlas="https://cdn-icons-png.flaticon.com/512/684/684908.png",  # 自訂 ICON
    get_icon_size=5,
)

# 使用者位置
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"lat": user_location[0], "lon": user_location[1]}]),
    get_position='[lon, lat]',
    get_color='[0, 150, 255, 255]',
    get_radius=80,
    pickable=False
)

# ========== Mapbox 樣式 ==========
map_style = "mapbox://styles/mapbox/light-v11"  # 專業乾淨

# ========== pydeck 視覺組合 ==========
view_state = pdk.ViewState(
    latitude=user_location[0],
    longitude=user_location[1],
    zoom=16,
    pitch=40,
)

r = pdk.Deck(
    map_style=map_style,
    initial_view_state=view_state,
    layers=[other_facilities_layer, user_layer, nearest_layer],
    tooltip={"text": "{name}\n類型: {type}\n距離: {distance}公尺"}
)

st.pydeck_chart(r)

# ========== 側邊資訊 ==========
st.sidebar.markdown("### 最近設施資訊")
st.sidebar.write(f"**名稱：** {nearest['name']}")
st.sidebar.write(f"**類型：** {nearest['type']}")
st.sidebar.write(f"**距離：** {nearest['distance']:.2f} 公尺")

