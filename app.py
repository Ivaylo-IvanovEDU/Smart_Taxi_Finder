            )

            for item in ranked:
                taxi = item["taxi"]
                taxi_id = taxi["id"]
                with st.container(border=True):
                    st.markdown(f"**🚕 Taxi #{taxi_id}**")
                    st.write(f"Distance: **{item['direct']:.2f} km**")
                    st.write(f"Estimated road distance: **{item['road']:.2f} km**")
                    st.write(f"ETA: **{max(1, math.ceil(item['eta']))} min**")
                    st.write(f"Speed: **{taxi['speed']} km/h**")
                    if st.button(
                        f"Select taxi #{taxi_id}",
                        key=f"select_{taxi_id}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_taxi = taxi_id
                        st.session_state.booking_message = ""
                        st.rerun()

# ---------------------------- Booking ----------------------------

st.divider()
st.subheader("📲 Your booking")

selected = find_taxi(st.session_state.selected_taxi) if st.session_state.selected_taxi else None

if selected is None:
    st.info("Select an available taxi from the list to make a booking.")
elif st.session_state.pickup is None:
    st.warning("Choose a pickup point on the map first.")
else:
    b1, b2 = st.columns([2, 1])
    with b1:
        st.markdown(f"### Selected vehicle: 🚕 Taxi #{selected['id']}")
        if selected["status"] == "Available":
            _, _, selected_eta = eta_for(selected, st.session_state.pickup)
            st.write(
                f"Estimated arrival: **{max(1, math.ceil(selected_eta))} min** · "
                f"Speed: **{selected['speed']} km/h**"
            )
        elif selected["status"] == "Coming":
            remaining = haversine_km(
                selected["lat"], selected["lon"],
                st.session_state.pickup[0], st.session_state.pickup[1],
            )
            st.write(f"Taxi is on its way · Approximate remaining distance: **{remaining:.2f} km**")
        else:
            st.write("The taxi has arrived at your pickup point.")

    with b2:
        if selected["status"] == "Available":
            if st.button("🚕 CALL THIS TAXI", type="primary", use_container_width=True):
                selected["status"] = "Coming"
                selected["target_lat"] = st.session_state.pickup[0]
                selected["target_lon"] = st.session_state.pickup[1]
                st.session_state.booking_message = f"Taxi #{selected['id']} has been dispatched!"
                st.rerun()
        elif selected["status"] == "Coming":
            st.warning("Taxi dispatched")
        else:
            st.success("Taxi arrived")

if st.session_state.booking_message:
    st.success(st.session_state.booking_message)

# ---------------------------- Statistics and fleet table ----------------------------

st.divider()
st.subheader("📊 Fleet statistics")

fleet = st.session_state.taxis
available_n = sum(t["status"] == "Available" for t in fleet)
coming_n = sum(t["status"] == "Coming" for t in fleet)
arrived_n = sum(t["status"] == "Arrived" for t in fleet)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total taxis", len(fleet))
c2.metric("Available", available_n)
c3.metric("On the way", coming_n)
c4.metric("Arrived", arrived_n)

st.subheader("🚕 Taxi fleet overview")
rows = []
for taxi in fleet:
    row = {
        "Taxi": f"#{taxi['id']}",
        "Speed (km/h)": taxi["speed"],
        "Latitude": round(taxi["lat"], 5),
        "Longitude": round(taxi["lon"], 5),
        "Status": taxi["status"],
    }
    if pickup is not None and taxi["status"] == "Available":
        direct, _, eta = eta_for(taxi, pickup)
        row["Distance to pickup (km)"] = round(direct, 2)
        row["ETA (min)"] = round(eta, 1)
    rows.append(row)

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown(
    """
    <p style="text-align:center;color:#AFC0D5;padding:18px 0;">
      TaxiGo · Educational simulation built with Python, Streamlit and Folium.
      Vehicle positions, speeds, routes and ETAs are simulated.
    </p>
    """,
    unsafe_allow_html=True,
)
