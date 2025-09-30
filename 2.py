def create_map():
    user_lat, user_lon = st.session_state.user_lat, st.session_state.user_lon

    filtered_df = df[df["Type"].isin(selected_types)].copy()
    filtered_df["distance_from_user"] = filtered_df.apply(
        lambda r: geodesic((user_lat, user_lon), (r["Latitude"], r["Longitude"])).meters, axis=1
    )

    nearest_df = filtered_df.nsmallest(5, "distance_from_user").copy()
    other_df = filtered_df[~filtered_df.index.isin(nearest_df.index)].copy()

    # 一般設施 tooltip + icon
    other_df["tooltip"] = other_df.apply(lambda r: f"{r['Type']}\n地址: {r['Address']}", axis=1)
    other_df["icon_data"] = other_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 40,
        "height": 40,
        "anchorY": 40
    })

    # 最近設施 tooltip + icon
    nearest_df["tooltip"] = nearest_df.apply(
        lambda r: f"🏆 最近設施\n類型: {r['Type']}\n地址: {r['Address']}\n距離: {r['distance_from_user']:.0f} 公尺",
        axis=1
    )
    nearest_df["icon_data"] = nearest_df["Type"].map(lambda x: {
        "url": ICON_MAPPING.get(x, ""),
        "width": 60,
        "height": 60,
        "anchorY": 60,
        "tint": [255, 0, 0]  # 填色紅色
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
            "width": 60,
            "height": 60,
            "anchorY": 60
        }
    }])

    layers = []

    # 一般設施
    for f_type in selected_types:
        sub_df = other_df[other_df["Type"] == f_type]
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
    if not nearest_df.empty:
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
