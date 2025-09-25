import streamlit as st
import folium
from streamlit_folium import st_folium

# ====== 1. 載入自訂 CSS ======
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ====== 2. 頁面標題 ======
st.title("🌟 Taipei City Walk - 台北市公共設施互動地圖")

st.markdown("""
這是一個整合 **飲水機、廁所、垃圾桶、狗便袋箱** 的互動式地圖。
使用者可以搜尋附近的設施，並提供回饋與推薦功能。  
""")

# ====== 3. 初始化地圖 ======
center = [25.0330, 121.5654]  # 台北101
m = folium.Map(location=center, zoom_start=15, tiles="CartoDB Positron")

# ====== 4. 加入標記 ======
folium.Marker(
    location=[25.0330, 121.5654],
    popup="台北101 - 專題中心",
    tooltip="點擊查看更多"
).add_to(m)

folium.Marker(
    location=[25.0375, 121.5637],
    popup="象山登山口 - 垃圾桶",
    tooltip="象山登山口"
).add_to(m)

# ====== 5. 在 Streamlit 顯示地圖 ======
st_folium(m, width=800, height=500)
