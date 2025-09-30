import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
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
# 載入 JSON 資料
# =========================
data_path = "data.json"

if not os.path.exists(data_path):
    st.error(f"❌ 找不到資料檔案，請確認 `{data_path}` 是否存在於專案目錄中")
    st.stop()

# 讀取 JSON
with open(data_path, "r", encoding="utf-8") as f:
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
if "accuracy" not in st.session_state:
    st.session_state.accuracy = None

# =========================
# 即時 GPS 定位（使用 watchPosition）
# =========================
st.subheader("📍 即時定位")
location = streamlit_js_eval(
    js_expressions="""
    new Promise((resolve, reject) => {
        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(
                (pos) => {
                    resolve({
                        lat: pos.coords.latitude,
                        lon: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    });
                },
                (err) => resolve({error: err.message}),
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        } else {
            resolve({error: "瀏覽器不支援定位"});
        }
    })
    """,
    key="live_geolocation"
)

# 更新使用者位置
if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location["lat"]
    st.session_state.user_lon = location["lon"]
    st.session_state.accuracy = location.get("accuracy", None)
    st.success(f"即時定位中：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})
else:
    st.warning("⚠️ 無法取得即時定位，請確認瀏覽器定位權限是否開啟")

# =========================
# 手動地址輸入表單
# =========================
with st.form(key="address_form"):
    address_input = st.text_input("📍 手動輸入地址（可選）")
    submit_button = st.form_submit_button(label="更新位置")
    if submit_button and address_input:
        geolocator = Nominatim(user_agent="taipei_map_app")
        try:
            loc = geolocator.geocode(address_input, timeout=10)
            if loc:
                st.session_state.user_lat = loc.latitude
                st.session_state.user_lon = loc.longitude
                st.success(f"✅ 已定位到輸入地址：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
            else:
                st.error("❌ 找不到地址，保持原位置")
        except Exception as e:
            st.error(f"❌ 地址轉換失敗，保持原位置：{e}")

# =========================
# 更新地圖函數
# =========================
def update_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon

    # 計算距離 & 最近 5 個設施
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )

    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

    # 生成 tooltip
    filtered_df["tooltip"] = filtered_df.apply(
        lambda r: f"{r['Type']}\n地址: {r['Address']}",
        axis=1
    )
    nearest_df["tooltip"] = nearest_df.apply(
        lambda r: f"🏆 最近設施\n類型: {r['Type']}\n地址: {r['Address']}\n距離: {r['distance_from_user']:.0f} 公尺",
        axis=1
    )

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
        "tooltip": f"📍 您的位置",
        "icon_data": {
            "url": ICON_MAPPING["使用者位置"],
            "width": 60,
            "height": 60,
            "anchorY": 60
        }
    }])

    # 建立圖層
    layers = []

    # 其他設施
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
        auto_highlight=True,
        name="使用者位置"
    ))

    # 地圖視圖
    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=15,
        pitch=0,
        bearing=0
    )

    # 更新地圖
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
update_map()

