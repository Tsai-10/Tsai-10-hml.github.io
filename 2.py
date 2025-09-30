import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
import os

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找 **飲水機、廁所、垃圾桶、狗便袋箱、寵物友善環境** 位置，並回報你發現的新地點 & 設施現況！")

# =========================
# 載入資料的統一清理函數
# =========================
def clean_and_validate(df):
    """清理欄位名稱並驗證 Latitude / Longitude 是否存在"""
    df.columns = [col.strip().replace("\t", "").replace("\n", "") for col in df.columns]
    rename_map = {c: c.strip().capitalize() for c in df.columns}

    # 修正拼字
    fixed_columns = {}
    for col in df.columns:
        if col.lower() in ["longtitude", "longitude"]:
            fixed_columns[col] = "Longitude"
        elif col.lower() == "latitude":
            fixed_columns[col] = "Latitude"
        else:
            fixed_columns[col] = col
    df = df.rename(columns=fixed_columns)

    # 驗證必要欄位
    required_cols = ["Latitude", "Longitude"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ 資料缺少 {col} 欄位")
            st.stop()

    # 移除經緯度缺失的資料
    df = df.dropna(subset=["Latitude", "Longitude"])
    return df

# =========================
# 載入主要 JSON 資料 (公共設施)
# =========================
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
df_main = pd.DataFrame(data)
df_main = clean_and_validate(df_main)
df_main["Source"] = "公共設施"



# =========================
# 設施圖標
# =========================
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=1E90FF",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=228B22",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=696969",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=A52A2A",
    "寵物友善環境": "https://img.icons8.com/?size=100&id=25181&format=png&color=FFD700",
    "使用者位置": "https://img.icons8.com/fluency/96/marker.png"
}

# =========================
# 側邊欄
# =========================
with st.sidebar:
    st.image("1.png", width=250)
    facility_types = sorted(combined_df["Type"].unique().tolist())
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

if location and isinstance(location, dict) and "lat" in location:
    st.session_state.user_lat = location.get("lat", st.session_state.user_lat)
    st.session_state.user_lon = location.get("lon", st.session_state.user_lon)
    st.success(f"✅ 已取得 GPS 位置：({st.session_state.user_lat:.5f}, {st.session_state.user_lon:.5f})")
else:
    st.warning("⚠️ 等待定位中，請允許瀏覽器存取您的位置")

# =========================
# 手動地址輸入
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
            st.error(f"❌ 地址轉換失敗：{e}")

# =========================
# 更新地圖
# =========================
def update_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon

    # 篩選使用者選擇的設施
    filtered_df = combined_df[combined_df["Type"].isin(selected_types)].copy()

    # 計算距離
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )

    # 最近五個設施
    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    filtered_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

    # 設備 icon
    for df_target, size_normal, size_highlight in [(filtered_df, 40, 40), (nearest_df, 60, 60)]:
        df_target["icon_data"] = df_target["Type"].map(lambda x: {
            "url": ICON_MAPPING.get(x, ""),
            "width": size_normal,
            "height": size_normal,
            "anchorY": size_normal
        })
        df_target["tooltip"] = df_target.apply(
            lambda r: f"{r['Type']}\n地址: {r['Address']}\n距離: {r['distance_from_user']:.0f} 公尺" if 'distance_from_user' in r else f"{r['Type']}\n地址: {r['Address']}",
            axis=1
        )

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

    # 顯示地圖
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
update_map()
