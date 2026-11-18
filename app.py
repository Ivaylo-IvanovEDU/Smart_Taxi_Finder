                f"""
                <div class="taxigo-card">
                  <div style="color:#aab8ca;">⚡ FASTEST ESTIMATED TAXI</div>
                  <div class="taxigo-yellow" style="font-size:32px;">Taxi #{fastest['taxi']['id']}</div>
                  <div style="font-size:25px;font-weight:700;">
                    {max(1, math.ceil(fastest['eta']))} min
                  </div>
                  <div style="color:#aab8ca;">Estimated arrival time</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for item in ranked_taxis:
                taxi = item["taxi"]
                taxi_id = taxi["id"]
                eta_minutes = max(1, math.ceil(item["eta"]))

                with st.container(border=True):
                    st.markdown(f"**🚕 Taxi #{taxi_id}**")
                    st.write(f"Distance: **{item['distance']:.2f} km**")
                    st.write(f"Estimated road distance: **{item['road_distance']:.2f} km**")
                    st.write(f"ETA: **{eta_minutes} min**")
                    st.write(f"Speed: **{taxi['speed']} km/h**")
                    if st.button(
                        f"Select taxi #{taxi_id}",
                        key=f"select_taxi_{taxi_id}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_taxi = taxi_id
                        st.session_state.booking_message = ""
                        st.rerun()

# ---------------------------- Booking panel ----------------------------

st.divider()
st.subheader("📲 Your booking")

selected_id = st.session_state.selected_taxi
selected_taxi = get_taxi(selected_id) if selected_id is not None else None

if selected_taxi is None:
    st.info("Select one of the available taxis to see the booking option.")
elif st.session_state.pickup is None:
    st.warning("Choose a pickup point on the map first.")
else:
    booking_col1, booking_col2 = st.columns([2, 1])
    with booking_col1:
        st.markdown(f"### Selected vehicle: 🚕 Taxi #{selected_id}")
        if selected_taxi["status"] == "Available":
            _, _, eta = estimate_eta(selected_taxi, st.session_state.pickup)
            st.write(
                f"Estimated arrival: **{max(1, math.ceil(eta))} min** · "
                f"Speed: **{selected_taxi['speed']} km/h**"
            )
        elif selected_taxi["status"] == "Coming":
            remaining = haversine_km(
                selected_taxi["lat"], selected_taxi["lon"],
                st.session_state.pickup[0], st.session_state.pickup[1],
            )
            st.write(f"Taxi is on its way. Approximate remaining distance: **{remaining:.2f} km**")
        else:
            st.write("The taxi has arrived at the pickup point.")

    with booking_col2:
        if selected_taxi["status"] == "Available":
            if st.button("🚕 CALL THIS TAXI", type="primary", use_container_width=True):
                selected_taxi["status"] = "Coming"
                selected_taxi["target_lat"] = st.session_state.pickup[0]
                selected_taxi["target_lon"] = st.session_state.pickup[1]
                st.session_state.booking_message = f"Taxi #{selected_id} has been dispatched!"
                st.rerun()
        elif selected_taxi["status"] == "Coming":
            st.warning("Taxi dispatched")
        else:
            st.success("Taxi arrived")

if st.session_state.booking_message:
    st.success(st.session_state.booking_message)

# ---------------------------- Fleet statistics ----------------------------

st.divider()
st.subheader("📊 Live fleet statistics")

all_taxis = st.session_state.taxis
available_count = sum(t["status"] == "Available" for t in all_taxis)
coming_count = sum(t["status"] == "Coming" for t in all_taxis)
arrived_count = sum(t["status"] == "Arrived" for t in all_taxis)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total taxis", len(all_taxis))
m2.metric("Available", available_count)
m3.metric("On the way", coming_count)
m4.metric("Arrived", arrived_count)

table_rows = []
for taxi in all_taxis:
    row = {
        "Taxi": f"#{taxi['id']}",
        "Speed (km/h)": taxi["speed"],
        "Latitude": round(taxi["lat"], 5),
        "Longitude": round(taxi["lon"], 5),
        "Status": taxi["status"],
    }
    if pickup is not None and taxi["status"] == "Available":
        distance, _, eta = estimate_eta(taxi, pickup)
        row["Distance to pickup (km)"] = round(distance, 2)
        row["ETA (min)"] = round(eta, 1)
    table_rows.append(row)

st.subheader("🚕 Taxi fleet overview")
st.dataframe(
    pd.DataFrame(table_rows),
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
    <p style="text-align:center;color:#718096;padding:18px 0;">
      TaxiGo · Educational simulation built with Python, Streamlit and Folium.
      All vehicle positions, speeds, routes and ETAs are simulated.
    </p>
    """,
    unsafe_allow_html=True,
)

