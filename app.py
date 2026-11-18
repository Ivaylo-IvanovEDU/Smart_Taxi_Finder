import math
import random
import time

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ============================================================
# TaxiGo — Smart Taxi Finder (educational simulation)
# Stable-map version: no automatic page/map refresh.
# ============================================================

st.set_page_config(
    page_title="TaxiGo | Smart Taxi Finder",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

CENTER = (42.1354, 24.7453)  # Plovdiv
LAT_BOUNDS = (42.105, 42.165)
LON_BOUNDS = (24.705, 24.785)
TAXI_COUNT = 12
EARTH_RADIUS_KM = 6371.0088

# ---------------------------- Theme ----------------------------

st.markdown(
    """
    <style>
    /* Main surfaces and readable text */
    .stApp, [data-testid="stAppViewContainer"] {
        background: #101827 !important;
        color: #F8FAFC !important;
    }
    [data-testid="stHeader"] { background: #101827 !important; }
    [data-testid="stSidebar"] {
        background: #1B2940 !important;
        border-right: 1px solid #34445C;
    }
    [data-testid="stSidebar"] * {
        color: #E5EDF8 !important;
    }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3, h4, p, li, label, .stMarkdown,
    [data-testid="stCaptionContainer"], [data-testid="stText"] {
        color: #F1F5F9;
    }
    [data-testid="stCaptionContainer"] p { color: #AFC0D5 !important; }
    .taxigo-subtitle {
        color: #B8C9DF !important;
        text-align: center;
        margin-top: -12px;
    }
    .taxigo-muted { color: #B8C9DF !important; }
    .taxigo-card {
        background: #1E2D43;
        border: 1px solid #40536D;
        border-radius: 14px;
        padding: 16px;
        margin: 8px 0;
        color: #F8FAFC !important;
    }
    .taxigo-card * { color: #F8FAFC !important; }
    .taxigo-yellow { color: #FDE047 !important; font-weight: 800; }
    [data-testid="stMetric"] {
        background: #1E2D43;
        border: 1px solid #40536D;
        border-radius: 12px;
        padding: 12px;
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricValue"],
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #F8FAFC !important;
    }
    /* Buttons */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 700;
        min-height: 42px;
        background: #FACC15;
        color: #172033 !important;
        border: 0;
    }
    div.stButton > button:hover {
        background: #FDE047;
        color: #111827 !important;
        border: 0;
    }
    div.stButton > button p { color: #172033 !important; }
    /* Inputs and dataframe */
    [data-testid="stDataFrame"] { border: 1px solid #40536D; border-radius: 10px; }
    [data-testid="stAlert"] p { color: #172033 !important; }
    [data-testid="stAlert"] svg { color: #172033 !important; }
    hr { border-color: #40536D !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Calculations ----------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def random_point():
    return random.uniform(*LAT_BOUNDS), random.uniform(*LON_BOUNDS)


def create_taxis():
    fleet = []
    for taxi_id in range(1, TAXI_COUNT + 1):
        lat, lon = random_point()
        target_lat, target_lon = random_point()
        fleet.append({
            "id": taxi_id,
            "lat": lat,
            "lon": lon,
            "speed": random.randint(25, 55),
            "target_lat": target_lat,
            "target_lon": target_lon,
            "status": "Available",
        })
    return fleet


def move_taxis(seconds=10):
    """Advance every taxi in the simulation by the given simulated seconds."""
    seconds = max(0.0, min(float(seconds), 3600.0))
    for taxi in st.session_state.taxis:
        if taxi["status"] == "Arrived":
            continue

        remaining = haversine_km(
            taxi["lat"], taxi["lon"],
            taxi["target_lat"], taxi["target_lon"],
        )

        if remaining <= 0.025:
            if taxi["status"] == "Coming":
                taxi["lat"] = taxi["target_lat"]
                taxi["lon"] = taxi["target_lon"]
                taxi["status"] = "Arrived"
            else:
                taxi["target_lat"], taxi["target_lon"] = random_point()
            continue

        travelled = taxi["speed"] * seconds / 3600.0
        fraction = min(travelled / remaining, 1.0)
        taxi["lat"] += (taxi["target_lat"] - taxi["lat"]) * fraction
        taxi["lon"] += (taxi["target_lon"] - taxi["lon"]) * fraction


def eta_for(taxi, pickup):
    direct_km = haversine_km(
        taxi["lat"], taxi["lon"], pickup[0], pickup[1]
    )
    # Simplified detour factor: this is not a real road-routing service.
    road_km = direct_km * 1.25
    eta_minutes = road_km / max(taxi["speed"], 1) * 60 + 0.5
    return direct_km, road_km, eta_minutes


def find_taxi(taxi_id):
    return next(
        (t for t in st.session_state.taxis if t["id"] == taxi_id),
        None,
    )


def build_map():
    taxi_map = folium.Map(
        location=CENTER,
        zoom_start=14,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
    )

    if st.session_state.pickup is not None:
        folium.Marker(
            st.session_state.pickup,
            tooltip="Your pickup point",
            popup="YOUR PICKUP LOCATION",
            icon=folium.Icon(color="red", icon="user", prefix="fa"),
        ).add_to(taxi_map)

    for taxi in st.session_state.taxis:
        color = {
            "Available": "green",
            "Coming": "orange",
            "Arrived": "red",
        }.get(taxi["status"], "blue")

        folium.Marker(
            (taxi["lat"], taxi["lon"]),
            tooltip=f"Taxi #{taxi['id']} · {taxi['status']}",
            popup=(
                f"<b>Taxi #{taxi['id']}</b><br>"
                f"Speed: {taxi['speed']} km/h<br>"
                f"Status: {taxi['status']}"
            ),
            icon=folium.Icon(color=color, icon="taxi", prefix="fa"),
        ).add_to(taxi_map)

        if taxi["status"] == "Coming" and st.session_state.pickup:
            folium.PolyLine(
                [(taxi["lat"], taxi["lon"]), st.session_state.pickup],
                color="#F59E0B",
                weight=4,
                opacity=0.9,
                dash_array="8 8",
                tooltip=f"Simulated route · taxi #{taxi['id']}",
            ).add_to(taxi_map)

    folium.Circle(
        CENTER,
        radius=3300,
        color="#64748B",
        weight=1,
        fill=False,
        tooltip="TaxiGo demo area",
    ).add_to(taxi_map)

    return taxi_map


# ---------------------------- Session state ----------------------------

if "taxis" not in st.session_state:
    st.session_state.taxis = create_taxis()
if "pickup" not in st.session_state:
    st.session_state.pickup = None
if "selected_taxi" not in st.session_state:
    st.session_state.selected_taxi = None
if "last_map_click" not in st.session_state:
    st.session_state.last_map_click = None
if "booking_message" not in st.session_state:
    st.session_state.booking_message = ""
if "simulation_step" not in st.session_state:
    st.session_state.simulation_step = 0

# ---------------------------- Header ----------------------------

st.markdown(
    "<h1 style='text-align:center;'>🚕 TaxiGo</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="taxigo-subtitle">SMART TAXI FINDER · '
    'Educational simulation · Plovdiv</p>',
    unsafe_allow_html=True,
)
st.divider()

# ---------------------------- Sidebar controls ----------------------------

with st.sidebar:
    st.title("⚙️ Control panel")
    st.markdown(
        "This is a simulation. No real taxis, drivers or GPS devices are connected."
    )
    st.markdown("### Simulation controls")

    if st.button("▶️ Move taxis (10 simulated seconds)", use_container_width=True):
        move_taxis(10)
        st.session_state.simulation_step += 1
        st.rerun()

    if st.button("⏩ Move taxis (1 simulated minute)", use_container_width=True):
        move_taxis(60)
        st.session_state.simulation_step += 1
        st.rerun()

    if st.button("🔄 Generate new taxis", use_container_width=True):
        st.session_state.taxis = create_taxis()
        st.session_state.pickup = None
        st.session_state.selected_taxi = None
        st.session_state.last_map_click = None
        st.session_state.booking_message = ""
        st.session_state.simulation_step = 0
        st.rerun()

    if st.button("📍 Clear pickup point", use_container_width=True):
        st.session_state.pickup = None
        st.session_state.selected_taxi = None
        st.session_state.last_map_click = None
        st.session_state.booking_message = ""
        st.rerun()

    st.divider()
    st.markdown("### Map legend")
    st.markdown("🟢 **Available taxi**")
    st.markdown("🟠 **Taxi travelling to pickup**")
    st.markdown("🔴 **Taxi arrived**")
    st.markdown("📍 **Your pickup point**")
    st.divider()
    st.caption("Stable map mode: no automatic page refresh. Use the simulation buttons to move taxis.")

# ---------------------------- Main columns ----------------------------

map_col, info_col = st.columns([2.1, 1], gap="large")

with map_col:
    st.subheader("🗺️ Live taxi map")
    st.caption("Click once on the map to set your pickup point. Use the sidebar controls to advance the simulation.")

    map_output = st_folium(
        build_map(),
        width=None,
        height=590,
        key="taxigo_stable_map",
        returned_objects=["last_clicked"],
        use_container_width=True,
    )

    clicked = map_output.get("last_clicked") if map_output else None
    if clicked:
        click_key = (round(clicked["lat"], 6), round(clicked["lng"], 6))
        if click_key != st.session_state.last_map_click:
            st.session_state.last_map_click = click_key
            st.session_state.pickup = (clicked["lat"], clicked["lng"])
            st.session_state.selected_taxi = None
            st.session_state.booking_message = ""
            st.rerun()

with info_col:
    st.subheader("🚖 Nearby taxis")
    pickup = st.session_state.pickup
    ranked = []

    if pickup is None:
        st.info("Choose a pickup point by clicking anywhere on the map.")
        st.markdown(
            """
            **How it works**
            1. Click your pickup point on the map.
            2. Compare taxi distances and estimated arrival times.
            3. Select a taxi.
            4. Press **Call this taxi**.
            """
        )
    else:
        st.success(f"Pickup selected · {pickup[0]:.5f}, {pickup[1]:.5f}")
        for taxi in st.session_state.taxis:
            if taxi["status"] == "Available":
                direct, road, eta = eta_for(taxi, pickup)
                ranked.append({
                    "taxi": taxi,
                    "direct": direct,
                    "road": road,
                    "eta": eta,
                })
        ranked.sort(key=lambda item: item["eta"])

        if not ranked:
            st.warning("There are no available taxis. Generate new taxis or move the simulation.")
        else:
            fastest = ranked[0]
            st.markdown(
                f"""
                <div class="taxigo-card">
                  <div class="taxigo-muted">⚡ FASTEST ESTIMATED TAXI</div>
                  <div class="taxigo-yellow" style="font-size:30px;">
                    Taxi #{fastest['taxi']['id']}
                  </div>
                  <div style="font-size:25px;font-weight:800;color:#FFFFFF;">
                    {max(1, math.ceil(fastest['eta']))} min
                  </div>
                  <div class="taxigo-muted">Estimated arrival time</div>
                </div>
                """,
                unsafe_allow_html=True,
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
