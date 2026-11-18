import math
import random

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# ============================================================
# TaxiGo — Smart Taxi Finder
# Educational demo: browser GPS + simulated taxis
# ============================================================

st.set_page_config(
    page_title="TaxiGo | Smart Taxi Finder",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_CENTER = (42.1354, 24.7453)  # Plovdiv fallback
EARTH_KM = 6371.0088
TAXI_COUNT = 12

# ---------------------------- Modern UI ----------------------------

st.markdown(
    """
    <style>
    :root {
        --bg: #F4F7FB;
        --surface: #FFFFFF;
        --ink: #172338;
        --muted: #68778D;
        --line: #E3EAF2;
        --navy: #14243A;
        --yellow: #FFC928;
        --green: #16A36A;
    }
    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--ink) !important;
    }
    [data-testid="stHeader"] { background: rgba(244,247,251,.92) !important; }
    [data-testid="stSidebar"] {
        background: #14243A !important;
        border-right: 1px solid #263B56;
    }
    [data-testid="stSidebar"] * { color: #F4F7FB !important; }
    .main .block-container { max-width: 1500px; padding-top: 1.8rem; }
    h1, h2, h3, h4, p, li, label, .stMarkdown {
        color: var(--ink);
    }
    [data-testid="stCaptionContainer"] p {
        color: var(--muted) !important;
    }
    .hero {
        background: linear-gradient(120deg, #14243A 0%, #203B5B 70%, #28506D 100%);
        padding: 28px 32px;
        border-radius: 22px;
        color: white !important;
        margin-bottom: 22px;
        box-shadow: 0 12px 30px rgba(20,36,58,.13);
    }
    .hero h1 { color: white !important; font-size: 2.35rem; margin: 0; }
    .hero p { color: #D6E2F0 !important; margin: 8px 0 0 0; }
    .eyebrow {
        color: #FFD85C !important; text-transform: uppercase;
        letter-spacing: .13em; font-size: .75rem; font-weight: 800;
    }
    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 5px 18px rgba(23,35,56,.045);
        margin-bottom: 14px;
    }
    .panel-title { color: var(--ink) !important; font-weight: 800; font-size: 1.05rem; }
    .muted { color: var(--muted) !important; }
    .best {
        background: linear-gradient(135deg, #14243A, #244968);
        color: white !important;
        padding: 20px;
        border-radius: 18px;
        margin: 12px 0 18px 0;
    }
    .best * { color: white !important; }
    .best .eta { color: #FFD85C !important; font-size: 2.1rem; font-weight: 900; }
    div.stButton > button {
        border-radius: 12px;
        border: 1px solid #E4B31C;
        background: #FFC928;
        color: #172338 !important;
        font-weight: 800;
        min-height: 44px;
    }
    div.stButton > button:hover {
        background: #FFDA61;
        border-color: #FFDA61;
        color: #172338 !important;
    }
    div.stButton > button p { color: #172338 !important; }
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px;
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--ink) !important;
    }
    [data-testid="stAlert"] p { color: #172338 !important; }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }
    hr { border-color: var(--line) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Geo / distance helpers ----------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


def offset_coordinate(lat, lon, north_km, east_km):
    """Approximate a nearby coordinate around a real GPS point."""
    new_lat = lat + north_km / 111.0
    cos_lat = max(0.2, math.cos(math.radians(lat)))
    new_lon = lon + east_km / (111.0 * cos_lat)
    return new_lat, new_lon


def random_near(center, radius_km=3.2):
    angle = random.uniform(0, 2 * math.pi)
    radius = radius_km * math.sqrt(random.random())
    return offset_coordinate(
        center[0], center[1],
        radius * math.cos(angle),
        radius * math.sin(angle),
    )


def create_taxis(center):
    fleet = []
    for taxi_id in range(1, TAXI_COUNT + 1):
        lat, lon = random_near(center)
        target_lat, target_lon = random_near(center)
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


def move_taxis(seconds=15):
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
                taxi["target_lat"], taxi["target_lon"] = random_near(
                    st.session_state.map_center
                )
            continue
        travelled = taxi["speed"] * seconds / 3600
        fraction = min(travelled / remaining, 1.0)
        taxi["lat"] += (taxi["target_lat"] - taxi["lat"]) * fraction
        taxi["lon"] += (taxi["target_lon"] - taxi["lon"]) * fraction


def estimate_eta(taxi, pickup):
    direct = haversine_km(
        taxi["lat"], taxi["lon"], pickup[0], pickup[1]
    )
    # Educational approximation, not live road traffic/navigation.
    road_distance = direct * 1.25
    eta = road_distance / max(taxi["speed"], 1) * 60 + 0.5
    return direct, road_distance, eta


def get_taxi(taxi_id):
    return next(
        (taxi for taxi in st.session_state.taxis if taxi["id"] == taxi_id),
        None,
    )


def build_map():
    center = st.session_state.map_center
    fmap = folium.Map(
        location=center,
        zoom_start=14,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )

    # Actual browser-provided device position
    if st.session_state.user_location is not None:
        lat, lon = st.session_state.user_location
        folium.Marker(
            (lat, lon),
            tooltip="Your current GPS position",
            popup="YOUR CURRENT LOCATION",
            icon=folium.Icon(color="blue", icon="crosshairs", prefix="fa"),
        ).add_to(fmap)
        folium.Circle(
            (lat, lon),
            radius=st.session_state.gps_accuracy or 30,
            color="#2878D0",
            fill=True,
            fill_opacity=0.10,
            tooltip="GPS accuracy area",
        ).add_to(fmap)

    # Pickup point (may be different from current GPS position)
    if st.session_state.pickup is not None:
        folium.Marker(
            st.session_state.pickup,
            tooltip="Taxi pickup point",
            popup="PICKUP POINT",
            icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
        ).add_to(fmap)

    for taxi in st.session_state.taxis:
        color = {
            "Available": "green",
            "Coming": "orange",
            "Arrived": "red",
        }.get(taxi["status"], "gray")

        folium.Marker(
            (taxi["lat"], taxi["lon"]),
            tooltip=f"Taxi #{taxi['id']} · {taxi['status']}",
            popup=(
                f"<b>Taxi #{taxi['id']}</b><br>"
                f"Speed: {taxi['speed']} km/h<br>"
                f"Status: {taxi['status']}"
            ),
            icon=folium.Icon(color=color, icon="taxi", prefix="fa"),
        ).add_to(fmap)

        if taxi["status"] == "Coming" and st.session_state.pickup:
            folium.PolyLine(
                [(taxi["lat"], taxi["lon"]), st.session_state.pickup],
                color="#F2A900",
                weight=4,
                opacity=0.9,
                dash_array="7 8",
            ).add_to(fmap)

    return fmap


# ---------------------------- Session state ----------------------------

if "user_location" not in st.session_state:
    st.session_state.user_location = None
if "gps_accuracy" not in st.session_state:
    st.session_state.gps_accuracy = None
if "map_center" not in st.session_state:
    st.session_state.map_center = DEFAULT_CENTER
if "pickup" not in st.session_state:
    st.session_state.pickup = None
if "selected_taxi" not in st.session_state:
    st.session_state.selected_taxi = None
if "last_map_click" not in st.session_state:
    st.session_state.last_map_click = None
if "booking_message" not in st.session_state:
    st.session_state.booking_message = ""
if "taxis" not in st.session_state:
    st.session_state.taxis = create_taxis(st.session_state.map_center)

# ---------------------------- Header ----------------------------

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Smart urban mobility · Student project</div>
      <h1>🚕 TaxiGo</h1>
      <p>Find the closest available taxi. Choose your pickup point. Get moving.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Sidebar / GPS ----------------------------

with st.sidebar:
    st.markdown("## 📍 Your location")
    st.write("Allow browser location access to center the map on your real position.")

    # Uses browser navigator.geolocation.getCurrentPosition().
    # The browser asks the user for permission.
    gps_data = streamlit_geolocation()

    if isinstance(gps_data, dict):
        lat = gps_data.get("latitude")
        lon = gps_data.get("longitude")
        accuracy = gps_data.get("accuracy")
        if lat is not None and lon is not None:
            new_location = (float(lat), float(lon))
            old_location = st.session_state.user_location
            changed = (
                old_location is None
                or haversine_km(
                    old_location[0], old_location[1],
                    new_location[0], new_location[1],
                ) > 0.05
            )
            st.session_state.user_location = new_location
            st.session_state.gps_accuracy = (
                float(accuracy) if accuracy is not None else None
            )
            if changed:
                st.session_state.map_center = new_location
                st.session_state.pickup = new_location
                st.session_state.taxis = create_taxis(new_location)
                st.session_state.selected_taxi = None
                st.session_state.last_map_click = None
                st.session_state.booking_message = ""
                st.rerun()

    if st.session_state.user_location is not None:
        st.success("GPS location received")
        st.caption(
            f"Lat: {st.session_state.user_location[0]:.5f} · "
            f"Lon: {st.session_state.user_location[1]:.5f}"
        )
        if st.session_state.gps_accuracy is not None:
            st.caption(f"Reported accuracy: ±{st.session_state.gps_accuracy:.0f} m")
        if st.button("Use my current position as pickup", use_container_width=True):
            st.session_state.pickup = st.session_state.user_location
            st.session_state.selected_taxi = None
            st.rerun()
    else:
        st.info("GPS not set yet. Press the location button above and allow permission, or click the map to choose a pickup point.")
        st.caption("If GPS is unavailable, the map opens around Plovdiv as a demo fallback.")

    st.divider()
    st.markdown("## 🎮 Simulation")
    if st.button("▶ Move taxis · 15 seconds", use_container_width=True):
        move_taxis(15)
        st.rerun()
    if st.button("⏩ Move taxis · 1 minute", use_container_width=True):
        move_taxis(60)
        st.rerun()
    if st.button("🔄 Reset taxi fleet", use_container_width=True):
        st.session_state.taxis = create_taxis(st.session_state.map_center)
        st.session_state.selected_taxi = None
        st.session_state.booking_message = ""
        st.rerun()
    st.divider()
    st.markdown("### Map legend")
    st.markdown("🔵 **Your real GPS position**")
    st.markdown("🔴 **Selected pickup point**")
    st.markdown("🟢 **Available taxi**")
    st.markdown("🟠 **Taxi on the way**")
    st.markdown("🔴 **Taxi arrived**")

# ---------------------------- Main map and taxi list ----------------------------

map_col, list_col = st.columns([1.8, 1], gap="large")

with map_col:
    st.markdown("### 🗺️ Live map")
    st.caption("Blue marker = your device location · Red marker = pickup · Click the map to change pickup.")

    map_result = st_folium(
        build_map(),
        width=None,
        height=620,
        key="taxigo_gps_map",
        returned_objects=["last_clicked"],
        use_container_width=True,
    )

    clicked = map_result.get("last_clicked") if map_result else None
    if clicked:
        click_key = (round(clicked["lat"], 6), round(clicked["lng"], 6))
        if click_key != st.session_state.last_map_click:
            st.session_state.last_map_click = click_key
            st.session_state.pickup = (float(clicked["lat"]), float(clicked["lng"]))
            st.session_state.selected_taxi = None
            st.session_state.booking_message = ""
            st.rerun()

with list_col:
    st.markdown("### 🚖 Nearby taxis")
    pickup = st.session_state.pickup

    if pickup is None:
        st.info("Set your real GPS position or click on the map to choose a pickup point.")
        ranked = []
    else:
        ranked = []
        for taxi in st.session_state.taxis:
            if taxi["status"] == "Available":
                direct, road, eta = estimate_eta(taxi, pickup)
                ranked.append({
                    "taxi": taxi,
                    "direct": direct,
                    "road": road,
                    "eta": eta,
                })
        ranked.sort(key=lambda item: item["eta"])

        st.markdown(
            f'<div class="panel"><span class="muted">Pickup coordinates</span><br>'
            f'<b>{pickup[0]:.5f}, {pickup[1]:.5f}</b></div>',
            unsafe_allow_html=True,
        )

        if ranked:
            fastest = ranked[0]
            st.markdown(
                f"""
                <div class="best">
                  <div style="font-size:.78rem;letter-spacing:.1em;color:#D5E3F0;">⚡ FASTEST ESTIMATED ARRIVAL</div>
                  <div style="font-size:1.6rem;font-weight:850;">Taxi #{fastest['taxi']['id']}</div>
                  <div class="eta">{max(1, math.ceil(fastest['eta']))} min</div>
                  <div style="color:#D5E3F0;">Estimated arrival · simulated</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for item in ranked:
                taxi = item["taxi"]
                taxi_id = taxi["id"]
                with st.container(border=True):
                    top_a, top_b = st.columns([2, 1])
                    top_a.markdown(f"**🚕 Taxi #{taxi_id}**")
                    top_b.markdown(f"**{max(1, math.ceil(item['eta']))} min**")
                    st.caption(
                        f"{item['direct']:.2f} km direct · "
                        f"{item['road']:.2f} km estimated road · "
                        f"{taxi['speed']} km/h"
                    )
                    if st.button(
                        f"Choose taxi #{taxi_id}",
                        key=f"choose_{taxi_id}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_taxi = taxi_id
                        st.session_state.booking_message = ""
                        st.rerun()
        else:
            st.warning("No free taxis. Reset the fleet to create new simulated taxis.")

# ---------------------------- Booking ----------------------------

st.divider()
st.markdown("### 📲 Booking details")

selected = get_taxi(st.session_state.selected_taxi) if st.session_state.selected_taxi else None

if selected is None:
    st.info("Choose a taxi from the list to see the booking action.")
elif st.session_state.pickup is None:
    st.warning("Choose a pickup location first.")
else:
    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"**Selected taxi: #{selected['id']}**")
        st.write(f"Vehicle speed: {selected['speed']} km/h")
        st.write(f"Status: {selected['status']}")
    with right:
        if selected["status"] == "Available":
            if st.button("🚕 CALL THIS TAXI", type="primary", use_container_width=True):
                selected["status"] = "Coming"
                selected["target_lat"] = st.session_state.pickup[0]
                selected["target_lon"] = st.session_state.pickup[1]
                st.session_state.booking_message = f"Taxi #{selected['id']} is on its way (simulation)."
                st.rerun()
        elif selected["status"] == "Coming":
            st.warning("Taxi is travelling to your pickup point.")
        else:
            st.success("Taxi has arrived at the pickup point.")

if st.session_state.booking_message:
    st.success(st.session_state.booking_message)

# ---------------------------- Fleet metrics ----------------------------

st.divider()
st.markdown("### 📊 Fleet overview")

fleet = st.session_state.taxis
available_count = sum(t["status"] == "Available" for t in fleet)
coming_count = sum(t["status"] == "Coming" for t in fleet)
arrived_count = sum(t["status"] == "Arrived" for t in fleet)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total taxis", len(fleet))
m2.metric("Available", available_count)
m3.metric("On the way", coming_count)
m4.metric("Arrived", arrived_count)

rows = []
for taxi in fleet:
    row = {
        "Taxi": f"#{taxi['id']}",
        "Speed": f"{taxi['speed']} km/h",
        "Status": taxi["status"],
        "Latitude": round(taxi["lat"], 5),
        "Longitude": round(taxi["lon"], 5),
    }
    if pickup is not None and taxi["status"] == "Available":
        direct, _, eta = estimate_eta(taxi, pickup)
        row["Distance"] = f"{direct:.2f} km"
        row["ETA"] = f"{max(1, math.ceil(eta))} min"
    rows.append(row)

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown(
    """
    <p style="text-align:center;color:#68778D;padding:20px 0 4px 0;">
      TaxiGo · Student project · GPS position is provided by the browser with your permission.
      Taxi locations, movement and arrival estimates are simulated.
    </p>
    """,
    unsafe_allow_html=True,
)
