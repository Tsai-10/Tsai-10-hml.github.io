import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
import time

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶** 位置，並回報你發現的新地點 & 設施現況！")

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
# 使用者位置初始化
# =========================
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 25.0330
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 121.5654

# =========================
# 自動 GPS 定位
# =========================
st.subheader("📍 自動定位")
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
        """, key="get_geolocation")
    except Exception:
        location = None

if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location.get("lat", st.session_state.user_lat)
    st.session_state.user_lon = location.get("lon", st.session_state.user_lon)
    st.success(f"✅ 已取得 GPS 位置：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
else:
    st.warning("⚠️ 無法自動定位，請輸入地址或使用預設位置。")

# =========================
# 側邊欄：留言系統
# =========================
with st.sidebar:
    st.image("1.png", width=250)
    st.subheader("💬 留言回饋")
    feedback_type = st.selectbox("選擇設施類型", sorted(df["Type"].unique().tolist()))
    address_options = df[df["Type"] == feedback_type]["Address"].tolist()
    feedback_address = st.selectbox("選擇設施地址", address_options)
    feedback_input = st.text_area("請輸入您的建議或回報", height=100)
    feedback_button = st.button("送出回饋")

    if feedback_button:
        if not feedback_type or not feedback_address or not feedback_input.strip():
            st.warning("⚠️ 請完整選擇類型、地址並輸入回饋內容")
        else:
            feedback_path = "feedback.json"
            if os.path.exists(feedback_path):
                with open(feedback_path, "r", encoding="utf-8") as f:
                    feedback_list = json.load(f)
            else:
                feedback_list = []
            feedback_list.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "type": feedback_type,
                "address": feedback_address,
                "feedback": feedback_input.strip()
            })
            with open(feedback_path, "w", encoding="utf-8") as f:
                json.dump(feedback_list, f, ensure_ascii=False, indent=4)
            st.success("✅ 感謝您的回饋！")
            st.experimental_rerun()

# =========================
# 選擇顯示設施類型
# =========================
facility_types = sorted(df["Type"].unique().tolist())
selected_types = st.multiselect("✅ 選擇顯示設施類型", facility_types, default=facility_types)

# =========================
# 建立地圖（只建立一次，不閃爍）
# =========================
def build_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()

    # 使用者位置
    user_pos_df = pd.DataFrame([{
        "Type": "使用者位置",
        "Address": "您目前的位置",
        "Latitude": user_lat,
        "Longitude": user_lon,
        "tooltip": "📍 您的位置",
        "icon_data": {
            "url": ICON_MAPPING["使用者位置"],
            "width": 75,
            "height": 75,
            "anchorY": 75
        }
    }])

    layers = []
    for f_type in selected_types:
        sub_df = filtered_df[filtered_df["Type"] == f_type]
        sub_df["icon_data"] = sub_df["Type"].map(lambda t: {
            "url": ICON_MAPPING[t],
            "width": 40,
            "height": 40,
            "anchorY": 40
        })
        sub_df["tooltip"] = sub_df.apply(lambda r: f"{r['Type']}\n地址: {r['Address']}", axis=1)
        layers.append(pdk.Layer(
            "IconLayer",
            data=sub_df,
            get_icon="icon_data",
            get_size=4,
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
deck = build_map()
with map_container:
    st.pydeck_chart(deck)

# =========================
# 自動刷新最近設施表格與圖標大小（不刷新地圖）
# =========================
table_container = st.empty()
REFRESH_INTERVAL = 5

def refresh_nearest():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    nearest_df["distance_from_user"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")

    # 更新地圖圖標大小：最近設施放大
    for layer in deck.layers[:-1]:  # 最後一層是使用者位置
        df_layer = layer.data
        df_layer["icon_data"] = df_layer.apply(
            lambda r: {"url": ICON_MAPPING.get(r["Type"], ""),
                       "width": 70 if r.name in nearest_df.index else 40,
                       "height": 70 if r.name in nearest_df.index else 40,
                       "anchorY": 70 if r.name in nearest_df.index else 40}, axis=1
        )

    # 表格顯示
    table_container.markdown("### 🏆 最近設施")
    table_container.dataframe(nearest_df[["Type", "Address", "distance_from_user"]].reset_index(drop=True), use_container_width=True)

# 每次互動刷新
refresh_nearest()
