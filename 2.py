import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import os
from streamlit_javascript import st_javascript
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- 頁面設定 ---
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("查找飲水機、廁所、垃圾桶、狗便袋箱位置，並回報你發現的新地點 & 設施現況！")

# --- 使用者定位 ---
st.subheader("📍 是否允許自動定位您的位置？")
allow_location = st.radio("請選擇：", ("是，我同意", "否，我不同意"), index=1)

user_lat, user_lon = 25.0330, 121.5654  # 預設位置台北101

if allow_location == "是，我同意":
    location = st_javascript(
        """
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
        """,
        key="get_location"
    )
    if location and isinstance(location, dict):
        user_lat = location.get("latitude", user_lat)
        user_lon = location.get("longitude", user_lon)
        st.success(f"✅ 已自動定位到您目前的位置：({user_lat:.5f}, {user_lon:.5f})")
    else:
        st.warning("⚠️ 無法取得定位，請在下方手動輸入地址。")
else:
    st.info("ℹ️ 未啟用定位，請在下方手動輸入地址。")

# --- 手動輸入地址功能 ---
address_input = st.text_input("📍 請輸入您的地址以便定位（可選）")
if address_input:
    geolocator = Nominatim(user_agent="taipei_map_app")
    try:
        location = geolocator.geocode(address_input, timeout=10)
        if location:
            user_lat, user_lon = location.latitude, location.longitude
            st.success(f"✅ 已定位到輸入地址的位置：({user_lat:.5f}, {user_lon:.5f})")
        else:
            st.error("❌ 找不到該地址，請確認輸入正確。")
    except Exception as e:
        st.error(f"❌ 地址轉換失敗：{e}")

# --- 載入設施資料 ---
data_path = "C:/Users/amy/PycharmProjects/B11108005-2/報告/data.json"
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
df = df.rename(columns={"Longtitude": "Longitude"})
df = df.dropna(subset=["Latitude", "Longitude"])

# --- 載入使用者回報資料 ---
feedback_file = "user_feedback.json"
if os.path.exists(feedback_file):
    with open(feedback_file, "r", encoding="utf-8") as f:
        feedback_data = json.load(f)
    df_feedback = pd.DataFrame(feedback_data)
    if not df_feedback.empty:
        if "Longtitude" in df_feedback.columns:
            df_feedback = df_feedback.rename(columns={"Longtitude": "Longitude"})
        df = pd.concat([df, df_feedback], ignore_index=True)

# --- 載入留言資料 ---
comment_file = "user_comments.json"
if os.path.exists(comment_file):
    with open(comment_file, "r", encoding="utf-8") as f:
        comments_data = json.load(f)
else:
    comments_data = []

# --- 設施圖標對應 ---
ICON_MAPPING = {
    "飲水機": "https://img.icons8.com/?size=100&id=chekdcoYm3uJ&format=png&color=000000",
    "廁所": "https://img.icons8.com/?size=100&id=QitPK4f8cxXW&format=png&color=000000",
    "垃圾桶": "https://img.icons8.com/?size=100&id=102715&format=png&color=000000",
    "狗便袋箱": "https://img.icons8.com/?size=100&id=124062&format=png&color=000000",
    "使用者位置": "https://img.icons8.com/?size=100&id=114900&format=png&color=000000"
}

# --- 側邊欄 ---
with st.sidebar:
    facility_types = sorted(df["Type"].unique().tolist())
    selected_types = st.multiselect("✅ 選擇要顯示的設施類型", facility_types, default=facility_types)

    with st.expander("📝 回報新地點（點我展開）"):
        with st.form("feedback_form"):
            feedback_type = st.selectbox("設施類型", facility_types)
            feedback_address = st.text_input("地址")
            submitted = st.form_submit_button("提交")
            if submitted:
                if feedback_address.strip() == "":
                    st.warning("請填寫地址")
                else:
                    geolocator = Nominatim(user_agent="taipei_map_app")
                    try:
                        location = geolocator.geocode(feedback_address, timeout=10)
                        if location:
                            new_entry = {
                                "Type": feedback_type,
                                "Address": feedback_address,
                                "Latitude": location.latitude,
                                "Longitude": location.longitude
                            }
                            if os.path.exists(feedback_file):
                                with open(feedback_file, "r", encoding="utf-8") as f:
                                    feedback_data = json.load(f)
                            else:
                                feedback_data = []
                            feedback_data.append(new_entry)
                            with open(feedback_file, "w", encoding="utf-8") as f:
                                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                            st.success("🎉 回報成功！謝謝您的貢獻。")
                        else:
                            st.error("❌ 找不到該地址，請確認輸入正確。")
                    except Exception as e:
                        st.error(f"❌ 地址轉換失敗：{e}")

        # ...（略過前段不變的程式碼）

    with st.expander("💬 設施留言"):
        all_addresses = sorted(df["Address"].dropna().unique().tolist())

        address_type_map = \
        df.dropna(subset=["Address", "Type"]).drop_duplicates(subset=["Address"])[["Address", "Type"]].set_index(
            "Address")["Type"].to_dict()

        comment_address = st.selectbox(
            "欲留言設施地址（輸入關鍵字選擇）",
            options=["請選擇地址"] + all_addresses,
            index=0
        )

        if comment_address != "請選擇地址":
            facility_type_for_comment = address_type_map.get(comment_address, "（無法辨識類型）")
            st.info(f"📌 該地址的設施類型：**{facility_type_for_comment}**")
        else:
            facility_type_for_comment = None

        comment_text = st.text_area("留言內容")
        comment_submit = st.button("送出留言")

        if comment_submit:
            if comment_address == "請選擇地址" or not comment_text.strip():
                st.warning("地址與留言不可空白")
            else:
                new_comment = {
                    "Address": comment_address.strip(),
                    "Type": facility_type_for_comment,
                    "Comment": comment_text.strip()
                }
                comments_data.append(new_comment)
                try:
                    with open(comment_file, "w", encoding="utf-8") as f:
                        json.dump(comments_data, f, ensure_ascii=False, indent=2)
                    st.success("📝 感謝您的留言！")
                except Exception as e:
                    st.error(f"留言存檔失敗：{e}")

        st.markdown("### 💬 設施留言列表")
        if comments_data:
            for i, c in enumerate(comments_data[::-1], 1):
                type_info = c.get("Type", "未知類型")
                st.markdown(f"**{i}. 地址：** {c['Address']}  \n**類型：** {type_info}  \n**留言：** {c['Comment']}")
        else:
            st.write("目前尚無留言。")

# --- 加上 icon 與 tooltip ---
filtered_df = df[df["Type"].isin(selected_types)].copy()
filtered_df["icon_data"] = filtered_df["Type"].map(lambda x: {
    "url": ICON_MAPPING.get(x, ""),
    "width": 40,
    "height": 40,
    "anchorY": 40
})
filtered_df["tooltip"] = filtered_df["Address"]

# --- 加入使用者位置圖示 ---
user_pos_df = pd.DataFrame([{
    "Type": "使用者位置",
    "Address": "您目前的位置",
    "Latitude": user_lat,
    "Longitude": user_lon,
    "icon_data": {
        "url": ICON_MAPPING["使用者位置"],
        "width": 50,
        "height": 50,
        "anchorY": 80
    },
    "tooltip": "您目前的位置"
}])

# --- 使用者選擇欲查看的設施類型 ---
st.subheader("📍 顯示最近設施（依類型）")
facility_types = sorted(filtered_df["Type"].unique())
selected_type = st.selectbox("請選擇設施類型", options=facility_types)

# --- 篩選出指定類型 ---
type_df = filtered_df[filtered_df["Type"] == selected_type].copy()

# --- 計算與使用者的距離 ---
type_df["distance_from_user"] = type_df.apply(
    lambda row: geodesic((user_lat, user_lon), (row["Latitude"], row["Longitude"])).meters,
    axis=1
)

# --- 顯示最近的前五筆設施 ---
st.markdown(f"### 🔍 離您最近的「{selected_type}」前五名")
if not type_df.empty:
    closest_type_df = type_df.sort_values("distance_from_user").head(5)
    display_df = closest_type_df[["Type", "Address", "distance_from_user"]].copy()
    display_df["distance_from_user"] = display_df["distance_from_user"].round(1)
    display_df = display_df.rename(columns={"Type": "設施類型", "Address": "地址", "distance_from_user": "距離（公尺）"})
    st.table(display_df.reset_index(drop=True))
else:
    st.write("目前無符合條件的設施。")



# --- 地圖圖層分群顯示 ---
layers = []
for f_type in selected_types:
    sub_df = filtered_df[filtered_df["Type"] == f_type].copy()
    if sub_df.empty:
        continue
    icon_layer = pdk.Layer(
        "IconLayer",
        data=sub_df,
        get_icon="icon_data",
        get_size=3,
        size_scale=12,
        get_position='[Longitude, Latitude]',
        pickable=True,
        auto_highlight=True,
        name=f_type
    )
    layers.append(icon_layer)

# --- 使用者位置圖層 ---
user_layer = pdk.Layer(
    "IconLayer",
    data=user_pos_df,
    get_icon="icon_data",
    get_size=4,
    size_scale=20,
    get_position='[Longitude, Latitude]',
    pickable=True,
    auto_highlight=True
)
layers.append(user_layer)

# --- 紅點：最近設施顯示 ---
df["distance_from_user"] = df.apply(
    lambda row: geodesic((user_lat, user_lon), (row["Latitude"], row["Longitude"])).meters,
    axis=1
)
nearest_df = df.nsmallest(5, "distance_from_user").copy()
nearest_df["tooltip"] = nearest_df.apply(
    lambda row: f'地址：{row["Address"]}\n距離：{row["distance_from_user"]:.1f} 公尺', axis=1
)

red_dot_layer = pdk.Layer(
    "ScatterplotLayer",
    data=nearest_df,
    get_position='[Longitude, Latitude]',
    get_fill_color='[255, 0, 0, 160]',
    get_radius=20,
    pickable=True,
    tooltip=True,
    auto_highlight=True
)
layers.append(red_dot_layer)

# --- 顯示地圖 ---
view_state = pdk.ViewState(
    longitude=user_lon,
    latitude=user_lat,
    zoom=15,
    pitch=0
)
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/streets-v11",
    initial_view_state=view_state,
    layers=layers,
    tooltip={"text": "{tooltip}"}
))
