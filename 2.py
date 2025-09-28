import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 使用者定位（自動 GPS + fallback）
# =========================
user_lat, user_lon = 25.0330, 121.5654  # 預設台北101

st.subheader("📍 定位方式")
try:
    location = streamlit_js_eval(js_expressions="""
        new Promise((resolve, reject) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({lat: pos.coords.latitude, lon: pos.coords.longitude}),
                    (err) => resolve({error: err.message})
                );
            } else {
                resolve({error: "瀏覽器不支援定位"});
            }
        })
    """, key="get_geolocation")
except Exception as e:
    location = None

if location and isinstance(location, dict) and "lat" in location:
    user_lat = location.get("lat", user_lat)
    user_lon = location.get("lon", user_lon)
    st.success(f"✅ 已取得 GPS 位置：({user_lat:.5f}, {user_lon:.5f})")
else:
    st.warning("⚠️ 無法自動定位，請輸入地址或使用預設位置。")
    address_input = st.text_input("📍 請輸入地址（可選）")
    if address_input:
        geolocator = Nominatim(user_agent="taipei_map_app")
        try:
            loc = geolocator.geocode(address_input, timeout=10)
            if loc:
                user_lat, user_lon = loc.latitude, loc.longitude
                st.success(f"✅ 已定位到輸入地址：({user_lat:.5f}, {user_lon:.5f})")
            else:
                st.error("❌ 找不到地址，使用預設位置")
        except Exception as e:
            st.error(f"❌ 地址轉換失敗，使用預設位置：{e}")

# =========================
# 載入設施資料
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 清理欄位名稱
cleaned_data = []
for d in data:
    cleaned_item = {}
    for k, v in d.items():
        key = k.strip()
        if key.lower() in ["longtitude", "longitude"]:
            key = "Longitude"
        elif key.lower() == "latitude":
            key = "Latitude"
        cleaned_item[key] = v
    cleaned_data.append(cleaned_item)

df = pd.DataFrame(cleaned_data)
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
# 側邊欄
# =========================
with st.sidebar:
    st.image("1.png", width=250)
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# =========================
# 動態更新地圖函數
# =========================
def update_map(user_lat, user_lon, df, selected_types):
    # 計算距離 & 最近 5 個設施
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

    # 設備 icon
    filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })
    nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 60,
        "height": 60,
        "anchorY": 60
    })

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

    # 建立圖層
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

    # 地圖視圖
    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=15,
        pitch=0,
        bearing=0
    )
    st.pydeck_chart(pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{tooltip}"}
    ))

    # 顯示最近設施清單
    st.subheader("🏆 最近的 5 個設施")
    nearest_df_display = nearest_df[["Type", "Address", "distance_from_user"]].copy()
    nearest_df_display["distance_from_user"] = nearest_df_display["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
    st.table(nearest_df_display.reset_index(drop=True))

# =========================
# 顯示地圖
# =========================
update_map(user_lat, user_lon, df, selected_types)
