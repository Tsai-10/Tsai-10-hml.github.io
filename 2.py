import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from streamlit_js_eval import streamlit_js_eval

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 自動刷新頁面，每 5 秒刷新一次
# =========================
REFRESH_INTERVAL = 5  # 秒
st_autorefresh = st.experimental_rerun
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="autorefresh")

# =========================
# 載入 JSON 資料
# =========================
data_path = "data.json"
if not os.path.exists(data_path):
    st.error(f"❌ 找不到資料檔案，請確認 `{data_path}` 是否存在於專案目錄中")
    st.stop()

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

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
if df.empty:
    st.error("⚠️ 資料檔案載入成功，但內容為空，請確認 data.json 是否有正確資料。")
    st.stop()

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
# 使用者位置初始化
# =========================
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654

# =========================
# 自動 GPS 定位
# =========================
st.subheader("📍 定位方式")
with st.spinner("等待定位中，請允許瀏覽器存取您的位置..."):
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
        """, key=f"get_geolocation_{st.time()}")
    except Exception:
        location = None

if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location.get("lat", st.session_state.user_lat)
    st.session_state.user_lon = location.get("lon", st.session_state.user_lon)
    st.success(f"✅ 已取得 GPS 位置：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
else:
    st.warning("⚠️ 無法自動定位，請輸入地址或使用預設位置。")

# =========================
# 手動地址輸入表單
# =========================
with st.form(key="address_form"):
    address_input = st.text_input("📍 手動輸入地址（可選）")
    submit_button = st.form_submit_button(label="更新位置")
    
    if submit_button and address_input.strip():
        geolocator = Nominatim(user_agent="taipei_city_walk_app")
        try:
            loc = geolocator.geocode(address_input, timeout=10)
            if loc:
                st.session_state.user_lat = loc.latitude
                st.session_state.user_lon = loc.longitude
                st.success(f"✅ 已定位到輸入地址：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
            else:
                st.error("❌ 找不到該地址，保持原位置")
        except Exception as e:
            st.error(f"❌ 地址轉換失敗，保持原位置：{e}")

# =========================
# 建立地圖（只渲染一次）
# =========================
def create_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon

    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })

    user_pos_df = pd.DataFrame([{
        "Type": "使用者位置",
        "Address": "您目前的位置",
        "Latitude": user_lat,
        "Longitude": user_lon,
        "tooltip": "📍 您的位置",
        "icon_data": {
            "url": ICON_MAPPING["使用者位置"],
            "width": 60,
            "height": 60,
            "anchorY": 60
        }
    }])

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
        data=user_pos_df,
        get_icon="icon_data",
        get_size=4,
        size_scale=20,
        get_position='[Longitude, Latitude]',
        pickable=True,
        auto_highlight=True
    ))

    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=15,
        pitch=0,
        bearing=0
    )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{tooltip}"}
    )

map_container = st.empty()
with map_container:
    st.pydeck_chart(create_map())

# =========================
# 最近設施距離表格
# =========================
table_container = st.empty()
user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["distance_from_user"] = filtered_df.apply(
    lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters,
    axis=1
)
nearest_df = filtered_df.nsmallest(5, "distance_from_user")[["Type", "Address", "distance_from_user"]].copy()
nearest_df["distance_from_user"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
table_container.table(nearest_df.reset_index(drop=True))
