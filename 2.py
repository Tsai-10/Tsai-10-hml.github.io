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
# =========================
# 移除「狗便袋箱」
# =========================
df = df[df["Type"] != "狗便袋箱"]

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
    # 留言回饋系統
    # =========================
    st.subheader("💬 留言回饋")
    feedback_type = st.selectbox("選擇設施類型", facility_types)
    feedback_input = st.text_area("請輸入您的建議或回報", height=100)
    feedback_button = st.button("送出回饋")

    # 讀取現有回饋
    feedback_path = "feedback.json"
    if os.path.exists(feedback_path):
        with open(feedback_path, "r", encoding="utf-8") as f:
            feedback_list = json.load(f)
    else:
        feedback_list = []

    # 送出回饋
    if feedback_button and feedback_input.strip():
        feedback_list.append({
            "type": feedback_type,
            "feedback": feedback_input.strip(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, ensure_ascii=False, indent=4)
        st.success(f"✅ 感謝您的回饋！針對 {feedback_type} 已成功送出。")
        feedback_input = ""  # 清空輸入框
        st.experimental_rerun()

    # 顯示歷史回饋（依設施類型過濾，最新在上）
    filtered_feedback = [fb for fb in reversed(feedback_list) if fb["type"] == feedback_type]

    if filtered_feedback:
        st.markdown(f"### 📄 {feedback_type} 歷史回饋")
        for fb in filtered_feedback:
            st.markdown(f"- ({fb['timestamp']}): {fb['feedback']}")
    else:
        st.markdown(f"尚無 **{feedback_type}** 類型的回饋。")

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
# 更新地圖函數
# =========================
def create_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()

    # 設置圖標與 tooltip
    filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })
    filtered_df["tooltip"] = filtered_df.apply(lambda r: f"{r['Type']}\n地址: {r['Address']}", axis=1)

    # 計算距離 & 最近 5 個設施
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    nearest_df["tooltip"] = nearest_df.apply(
        lambda r: f"🏆 最近設施\n類型: {r['Type']}\n地址: {r['Address']}\n距離: {r['distance_from_user']:.0f} 公尺",
        axis=1
    )
    nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 70,
        "height": 70,
        "anchorY": 70
    })

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

    # 建立圖層
    layers = []
    for f_type in selected_types:
        sub_df = filtered_df[(filtered_df["Type"] == f_type) & (~filtered_df.index.isin(nearest_df.index))]
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
        size_scale=20*1.25,
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

# =========================
# 顯示地圖
# =========================
map_container = st.empty()
with map_container:
    st.pydeck_chart(create_map())

# =========================
# 最近設施即時刷新（單一表格）
# =========================
table_container = st.empty()
REFRESH_INTERVAL = 5  # 秒

def update_nearest_table():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon
    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )
    nearest_df = filtered_df.nsmallest(5, "distance_from_user")[["Type", "Address", "distance_from_user"]].copy()
    nearest_df["distance_from_user"] = nearest_df["distance_from_user"].apply(lambda x: f"{x:.0f} 公尺")
    table_container.table(nearest_df.reset_index(drop=True))

# 用 while True 取代，並加 try-except 防止停止
