import streamlit as st
import pydeck as pdk
import pandas as pd

st.title("🗺️ 測試地圖")

# 測試資料
data = pd.DataFrame({
    "Latitude": [25.0330, 25.0375],
    "Longitude": [121.5654, 121.5637],
    "Name": ["台北101", "中正紀念堂"]
})

view_state = pdk.ViewState(latitude=25.0330, longitude=121.5654, zoom=14)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position='[Longitude, Latitude]',
    get_fill_color='[200, 30, 0, 160]',
    get_radius=50,
    pickable=True
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/streets-v11",
    initial_view_state=view_state,
    layers=[layer],
    tooltip={"text": "{Name}"}
))
