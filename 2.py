import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
from st_aggrid import AgGrid, GridOptionsBuilder

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Taipei City Walk", layout="wide")
st.title("🏙️ Taipei City Walk")
st.markdown("**智慧便民設施地圖** - 找到離你最近的飲水機、廁所或垃圾桶")

# =========================
# 資料載入
# =========================
@st.cache_data
def load_data():
    # 假資料，可以替換成你的設施資料 CSV
    data = {
        "Name": ["飲水機 - 台科大", "垃圾桶 - 公園", "廁所 - 捷運站", "飲水機 - 市政府"],
        "Latitude": [25.0135, 25.0148, 25.0155, 25.0324],
        "Longitude": [121.5415, 121.5432, 121.5378, 121.5651],
    }
    df = pd.DataFrame(data)
    return df

df = load_data()

# =========================
# 使用者定位
# =========================
user_location = st.sidebar.text_input("輸入目前位置 (緯度,經度)", "25.014,121.541")
try:
    user_lat, user_lon = map(float, user_location.split(","))
    user_coords = (user_lat, user_lon)
except:
    st.error("⚠️ 請輸入有效的經緯度，例如：25.014,121.541")
    st.stop()

# =========================
# 計算距離
# =========================
def calculate_distances(df, user_coords):
    df["Distance_m"] = df.apply(
        lambda row: geodesic(user_coords, (row["Latitude"], row["Longitude"])).meters,
        axis=1,
    )
    return df.sort_values(by="Distance_m")

df = calculate_distances(df, user_coords)

# =========================
# 顯示最近設施列表
# =========================
st.subheader("📋 最近設施列表")

# st-aggrid 表格設計
gb = GridOptionsBuilder.from_dataframe(
    df[["Name", "Distance_m"]].rename(columns={"Name": "設施名稱", "Distance_m": "距離(公尺)"})
)
gb.configure_selection("single", use_checkbox=True)  # 單選
gb.configure_column("距離(公尺)", type=["numericColumn"], precision=2)
grid_options = gb.build()

grid_response = AgGrid(
    df[["Name", "Distance_m"]].rename(columns={"Name": "設施名稱", "Distance_m": "距離(公尺)"}),
    gridOptions=grid_options,
    height=250,
    fit_columns_on_grid_load=True,
    theme="balham",  # 表格主題
)

selected_rows = grid_response.get("selected_rows")

# =========================
# 地圖呈現
# =========================
st.subheader("🗺️ 地圖視覺化")

# 基礎圖層（所有設施）
base_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position=["Longitude", "Latitude"],
    get_fill_color=[100, 149, 237, 120],  # 柔和藍色
    get_radius=30,
    pickable=True,
)

# 最近設施突出顯示
highlight_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df.head(1),  # 最近的一筆資料
    get_position=["Longitude", "Latitude"],
    get_fill_color=[255, 215, 0, 200],  # 金色
    get_radius=120,
    pickable=True,
)

# 使用者位置標記
user_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([{"Latitude": user_lat, "Longitude": user_lon}]),
    get_position=["Longitude", "Latitude"],
    get_fill_color=[255, 0, 0, 200],  # 紅色
    get_radius=150,
    pickable=False,
)

# 判斷是否有選取表格列，並聚焦
if selected_rows and len(selected_rows) > 0:
    selected_name = selected_rows[0]["設施名稱"]
    selected_point = df[df["Name"] == selected_name].iloc[0]
    initial_view = pdk.ViewState(
        latitude=selected_point["Latitude"],
        longitude=selected_point["Longitude"],
        zoom=17,
        pitch=45,
    )
else:
    # 預設顯示使用者位置
    initial_view = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=15, pitch=45)

# 繪製地圖
r = pdk.Deck(
    layers=[base_layer, highlight_layer, user_layer],
    initial_view_state=initial_view,
    tooltip={"text": "{Name}\n距離: {Distance_m} 公尺"},
    map_style="mapbox://styles/mapbox/light-v11",
)
st.pydeck_chart(r)

# =========================
# 最近設施摘要
# =========================
nearest_facility = df.iloc[0]
st.markdown(
    f"""
    ### 🌟 最近設施
    - **名稱：** {nearest_facility['Name']}
    - **距離：** {nearest_facility['Distance_m']:.2f} 公尺
    """
)
