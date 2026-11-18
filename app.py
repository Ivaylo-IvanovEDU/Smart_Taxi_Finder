
import streamlit as st
import folium
from streamlit_folium import st_folium
import random
import math
import time
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================================
# CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="TaxiGo - Smart Taxi Finder",
    page_icon="🚕",
    layout="wide"
)

# Example city: Plovdiv
CENTER_LAT = 42.1354
CENTER_LON = 24.7453

LAT_MIN = 42.105
LAT_MAX = 42.165
LON_MIN = 24.705
LON_MAX = 24.785

TAXI_SPEED_MIN = 25
TAXI_SPEED_MAX = 55

# ==========================================
# CUSTOM CSS
# ==========================================

st.markdown("""
<style>
.stApp {
    background-color: #101827;
    color: white;
}

h1, h2, h3 {
    color: #ffffff;
}

.metric-card {
    background: #1d293b;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    border: 1px solid #34445c;
}

.metric-number {
    font-size: 28px;
    font-weight: bold;
    color: #facc15;
}

.metric-label {
    font-size: 13px;
    color: #cbd5e1;
}

.stButton button {
    background-color: #eab308;
    color: #111827;
    font-weight: bold;
    border-radius: 10px;
    width: 100%;
    border: none;
}

.stButton button:hover {
    background-color: #facc15;
    color: black;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# DISTANCE CALCULATION
# ==========================================

def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ==========================================
# TAXI GENERATION
# ==========================================

def create_taxis():

    taxis = []

    for i in range(12):

        taxis.append({
            "id": i + 1,
            "lat": random.uniform(LAT_MIN, LAT_MAX),
            "lon": random.uniform(LON_MIN, LON_MAX),
            "speed": random.randint(
                TAXI_SPEED_MIN,
                TAXI_SPEED_MAX
            ),
            "target_lat": random.uniform(LAT_MIN, LAT_MAX),
            "target_lon": random.uniform(LON_MIN, LON_MAX),
            "status": "Available",
            "last_update": time.time()
        })

    return taxis


if "taxis" not in st.session_state:
    st.session_state.taxis = create_taxis()

if "pickup" not in st.session_state:
    st.session_state.pickup = None

if "selected_taxi" not in st.session_state:
    st.session_state.selected_taxi = None

if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()


# ==========================================
# SIMULATE TAXI MOVEMENT
# ==========================================

def move_taxis():

    now = time.time()
    elapsed = min(now - st.session_state.last_update, 3)
    st.session_state.last_update = now

    for taxi in st.session_state.taxis:

        if taxi["status"] == "Arrived":
            continue

        distance = calculate_distance(
            taxi["lat"],
            taxi["lon"],
            taxi["target_lat"],
            taxi["target_lon"]
        )

        # Taxi has reached its target
        if distance < 0.025:

            if taxi["status"] == "Coming":

                taxi["status"] = "Arrived"
                continue

            taxi["target_lat"] = random.uniform(LAT_MIN, LAT_MAX)
            taxi["target_lon"] = random.uniform(LON_MIN, LON_MAX)

            continue

        # Convert speed to distance traveled
        distance_traveled = (
            taxi["speed"] * elapsed / 3600
        )

        ratio = min(distance_traveled / distance, 1)

        taxi["lat"] += (
            taxi["target_lat"] - taxi["lat"]
        ) * ratio

        taxi["lon"] += (
            taxi["target_lon"] - taxi["lon"]
        ) * ratio


# ==========================================
# ETA PREDICTION
# ==========================================

def predict_eta(taxi, pickup):

    distance = calculate_distance(
        taxi["lat"],
        taxi["lon"],
        pickup[0],
        pickup[1]
    )

    # Simulated road detour factor
    road_factor = 1.25

    estimated_distance = distance * road_factor

    eta_minutes = (
        estimated_distance / taxi["speed"]
    ) * 60

    return distance, eta_minutes


# ==========================================
# HEADER
# ==========================================

st.markdown(
    "<h1 style='text-align:center;'>🚕 TaxiGo</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='text-align:center;color:#94a3b8;'>"
    "SMART TAXI FINDER | Find the fastest taxi near you"
    "</p>",
    unsafe_allow_html=True
)

st.divider()


# ==========================================
# AUTO REFRESH
# ==========================================

st_autorefresh(
    interval=1000,
    key="taxi_refresh"
)

move_taxis()


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("⚙️ Control Panel")

    st.markdown("### Simulation Settings")

    st.info("All taxis and GPS positions are simulated.")

    if st.button("🔄 Generate New Taxis"):

        st.session_state.taxis = create_taxis()
        st.session_state.selected_taxi = None
        st.session_state.pickup = None
        st.rerun()

    if st.button("📍 Reset Pickup Location"):

        st.session_state.pickup = None
        st.session_state.selected_taxi = None
        st.rerun()

    st.divider()

    st.markdown("### Legend")

    st.markdown("🟢 Available taxi")
    st.markdown("🟡 Taxi coming to you")
    st.markdown("🔴 Arrived taxi")
    st.markdown("📍 Your pickup location")


# ==========================================
# MAIN LAYOUT
# ==========================================

left, right = st.columns([2.2, 1])

with left:

    st.subheader("🗺️ Live Taxi Map")

    st.caption(
        "Click anywhere on the map to select your pickup location."
    )

    taxi_map = folium.Map(
        location=[CENTER_LAT, CENTER_LON],
        zoom_start=14,
        tiles="CartoDB positron"
    )

    # Pickup location
    if st.session_state.pickup:

        folium.Marker(
            location=st.session_state.pickup,
            tooltip="Your pickup location",
            popup="YOUR LOCATION",
            icon=folium.Icon(
                color="red",
                icon="user",
                prefix="fa"
            )
        ).add_to(taxi_map)

    # Draw taxis
    for taxi in st.session_state.taxis:

        if taxi["status"] == "Available":
            color = "green"
        elif taxi["status"] == "Coming":
            color = "orange"
        else:
            color = "red"

        folium.Marker(
            location=[taxi["lat"], taxi["lon"]],
            tooltip=f"Taxi #{taxi['id']}",
            popup=(
                f"Taxi #{taxi['id']}<br>"
                f"Speed: {taxi['speed']} km/h<br>"
                f"Status: {taxi['status']}"
            ),
            icon=folium.Icon(
                color=color,
                icon="taxi",
                prefix="fa"
            )
        ).add_to(taxi_map)

        # Show simulated route to pickup
        if (
            taxi["status"] == "Coming"
            and st.session_state.pickup
        ):

            folium.PolyLine(
                locations=[
                    [taxi["lat"], taxi["lon"]],
                    st.session_state.pickup
                ],
                color="orange",
                weight=3,
                dash_array="8"
            ).add_to(taxi_map)

    map_data = st_folium(
        taxi_map,
        width=None,
        height=580,
        key="taxi_map"
    )

    # Read map click
    if map_data and map_data.get("last_clicked"):

        clicked = map_data["last_clicked"]

        new_pickup = (
            clicked["lat"],
            clicked["lng"]
        )

        old_pickup = st.session_state.pickup

        if (
            old_pickup is None
            or calculate_distance(
                old_pickup[0],
                old_pickup[1],
                new_pickup[0],
                new_pickup[1]
            ) > 0.015
        ):

            st.session_state.pickup = new_pickup
            st.session_state.selected_taxi = None
            st.rerun()


# ==========================================
# TAXI INFORMATION
# ==========================================

with right:

    st.subheader("🚖 Available Taxis")

    available_taxis = []

    if st.session_state.pickup:

        for taxi in st.session_state.taxis:

            if taxi["status"] != "Available":
                continue

            distance, eta = predict_eta(
                taxi,
                st.session_state.pickup
            )

            available_taxis.append({
                "ID": taxi["id"],
                "Distance": distance,
                "ETA": eta,
                "Speed": taxi["speed"]
            })

        available_taxis.sort(
            key=lambda x: x["ETA"]
        )

        st.success(
            "Pickup location selected!"
        )

        if available_taxis:

            fastest = available_taxis[0]

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">
                        ⚡ FASTEST TAXI
                    </div>
                    <div class="metric-number">
                        #{fastest['ID']}
                    </div>
                    <div class="metric-label">
                        Estimated arrival
                    </div>
                    <div class="metric-number">
                        {max(1, math.ceil(fastest['ETA']))} min
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write("")

            for taxi_data in available_taxis:

                taxi_id = taxi_data["ID"]

                st.markdown(
                    f"""
                    **🚕 Taxi #{taxi_id}**

                    - 📍 Distance: {taxi_data['Distance']:.2f} km
                    - ⏱️ ETA: {max(1, math.ceil(taxi_data['ETA']))} min
                    - 🚀 Speed: {taxi_data['Speed']} km/h
                    """
                )

                if st.button(
                    f"SELECT TAXI #{taxi_id}",
                    key=f"select_{taxi_id}"
                ):

                    st.session_state.selected_taxi = taxi_id
                    st.rerun()

                st.divider()

        else:

            st.warning(
                "No available taxis at the moment."
            )

    else:

        st.warning(
            "First, click on the map to choose your pickup location."
        )

        st.markdown(
            """
            ### How to start?

            1. Find your location on the map.
            2. Click on your pickup point.
            3. Compare available taxis.
            4. Select the fastest one.
            """
        )


# ==========================================
# CALL TAXI
# ==========================================

st.divider()

st.subheader("📲 Your Taxi Booking")

selected_id = st.session_state.selected_taxi

if selected_id:

    selected_taxi = next(
        (
            taxi for taxi in st.session_state.taxis
            if taxi["id"] == selected_id
        ),
        None
    )

    if selected_taxi:

        st.markdown(
            f"### Selected taxi: 🚕 #{selected_id}"
        )

        if selected_taxi["status"] == "Available":

            if st.button(
                "🚕 CALL THIS TAXI",
                type="primary"
            ):

                selected_taxi["status"] = "Coming"

                selected_taxi["target_lat"] = (
                    st.session_state.pickup[0]
                )

                selected_taxi["target_lon"] = (
                    st.session_state.pickup[1]
                )

                st.success(
                    f"Taxi #{selected_id} has been called!"
                )

                st.rerun()

        elif selected_taxi["status"] == "Coming":

            st.warning(
                f"Taxi #{selected_id} is on its way!"
            )

        elif selected_taxi["status"] == "Arrived":

            st.success(
                f"Taxi #{selected_id} has arrived!"
            )

else:

    st.info(
        "Select a taxi from the list to make a booking."
    )


# ==========================================
# STATISTICS
# ==========================================

st.divider()

st.subheader("📊 Live Simulation Statistics")

total = len(st.session_state.taxis)

available = sum(
    1 for t in st.session_state.taxis
    if t["status"] == "Available"
)

coming = sum(
    1 for t in st.session_state.taxis
    if t["status"] == "Coming"
)

arrived = sum(
    1 for t in st.session_state.taxis
    if t["status"] == "Arrived"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Total Taxis", total)

with c2:
    st.metric("Available", available)

with c3:
    st.metric("Coming", coming)

with c4:
    st.metric("Arrived", arrived)


# ==========================================
# TAXI TABLE
# ==========================================

st.subheader("🚕 Taxi Fleet Overview")

taxi_table = pd.DataFrame([
    {
        "Taxi ID": f"#{t['id']}",
        "Speed (km/h)": t["speed"],
        "Latitude": round(t["lat"], 5),
        "Longitude": round(t["lon"], 5),
        "Status": t["status"]
    }
    for t in st.session_state.taxis
])

st.dataframe(
    taxi_table,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# FOOTER
# ==========================================

st.markdown(
    """
    <div style="text-align:center;color:#64748b;padding:20px;">
        🚕 TaxiGo Smart Taxi Finder |
        Educational Simulation Project |
        Built with Python & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
