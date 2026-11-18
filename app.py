import math
import random
import time

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ============================================================
# TaxiGo — educational taxi dispatch simulation
# ============================================================

st.set_page_config(
    page_title="TaxiGo | Smart Taxi Finder",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Demo area: Plovdiv, Bulgaria
CENTER = (42.1354, 24.7453)
LAT_BOUNDS = (42.105, 42.165)
LON_BOUNDS = (24.705, 24.785)

TAXI_COUNT = 12
REFRESH_SECONDS = 2
EARTH_RADIUS_KM = 6371.0088

# ---------------------------- Styling ----------------------------

st.markdown(
    """
    <style>
      .stApp { background: #101827; color: #f8fafc; }
      [data-testid="stSidebar"] { background: #172235; }
      h1, h2, h3 { color: #f8fafc; }
      .taxigo-subtitle { color: #aab8ca; text-align: center; margin-top: -12px; }
      .taxigo-card {
        background: #1d293b; border: 1px solid #34445c;
        border-radius: 14px; padding: 16px; margin: 8px 0;
      }
      .taxigo-yellow { color: #facc15; font-weight: 800; }
      div.stButton > button {
        border-radius: 10px; font-weight: 700; min-height: 42px;
      }
      [data-testid="stMetric"] {
        background: #1d293b; border: 1px solid #34445c;
        border-radius: 12px; padding: 12px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Helpers ----------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two GPS coordinates, in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def random_point():
    return (
        random.uniform(*LAT_BOUNDS),
        random.uniform(*LON_BOUNDS),
    )


def make_taxis():
    taxis = []
    for taxi_id in range(1, TAXI_COUNT + 1):
        lat, lon = random_point()
        target_lat, target_lon = random_point()
        taxis.append(
            {
                "id": taxi_id,
                "lat": lat,
                "lon": lon,
                "speed": random.randint(25, 55),
                "target_lat": target_lat,
                "target_lon": target_lon,
                "status": "Available",
            }
        )
    return taxis


def advance_taxis(elapsed_seconds):
    """Move taxis a small distance toward their current targets."""
    elapsed_seconds = max(0.0, min(float(elapsed_seconds), 10.0))

    for taxi in st.session_state.taxis:
        if taxi["status"] == "Arrived":
            continue

        remaining_km = haversine_km(
            taxi["lat"], taxi["lon"],
            taxi["target_lat"], taxi["target_lon"],
        )

        if remaining_km < 0.025:
            if taxi["status"] == "Coming":
                taxi["lat"] = taxi["target_lat"]
                taxi["lon"] = taxi["target_lon"]
                taxi["status"] = "Arrived"
            else:
                taxi["target_lat"], taxi["target_lon"] = random_point()
            continue

        # km/h * seconds / 3600 = km travelled this update
        travelled_km = taxi["speed"] * elapsed_seconds / 3600.0
        fraction = min(travelled_km / remaining_km, 1.0)

        taxi["lat"] += (taxi["target_lat"] - taxi["lat"]) * fraction
        taxi["lon"] += (taxi["target_lon"] - taxi["lon"]) * fraction


def estimate_eta(taxi, pickup):
    """Simplified ETA: straight-line distance + simulated road detour."""
    straight_km = haversine_km(
        taxi["lat"], taxi["lon"], pickup[0], pickup[1]
    )
    road_km = straight_km * 1.25
    # A small fixed allowance represents turns/stops in this demo.
    eta_minutes = (road_km / max(taxi["speed"], 1)) * 60 + 0.5
    return straight_km, road_km, eta_minutes


def get_taxi(taxi_id):
    return next(
        (taxi for taxi in st.session_state.taxis if taxi["id"] == taxi_id),
        None,
    )


def build_map():
    """Build the map from current simulation state."""
    taxi_map = folium.Map(
        location=CENTER,
        zoom_start=14,
        control_scale=True,
        tiles="OpenStreetMap",
        prefer_canvas=True,
    )

    # Pickup marker
    pickup = st.session_state.pickup
    if pickup is not None:
        folium.Marker(
            location=pickup,
            tooltip="Your pickup point",
            popup="YOUR PICKUP LOCATION",
            icon=folium.Icon(color="red", icon="user", prefix="fa"),
        ).add_to(taxi_map)

    # Taxi markers and their simulated routes
    for taxi in st.session_state.taxis:
        color = {
            "Available": "green",
            "Coming": "orange",
            "Arrived": "red",
        }.get(taxi["status"], "blue")

        folium.Marker(
            location=(taxi["lat"], taxi["lon"]),
            tooltip=f"Taxi #{taxi['id']} · {taxi['status']}",
            popup=(
                f"<b>Taxi #{taxi['id']}</b><br>"
                f"Speed: {taxi['speed']} km/h<br>"
                f"Status: {taxi['status']}"
            ),
            icon=folium.Icon(color=color, icon="taxi", prefix="fa"),
        ).add_to(taxi_map)

        if taxi["status"] == "Coming" and pickup is not None:
            folium.PolyLine(
                locations=[
                    (taxi["lat"], taxi["lon"]),
                    pickup,
                ],
                color="#f59e0b",
                weight=4,
                opacity=0.85,
                dash_array="8 8",
                tooltip=f"Route of taxi #{taxi['id']} (simulated)",
            ).add_to(taxi_map)

    folium.Circle(
        location=CENTER,
        radius=3300,
        color="#64748b",
        weight=1,
        fill=False,
        tooltip="TaxiGo demo area",
    ).add_to(taxi_map)

    return taxi_map


# ---------------------------- Session state ----------------------------

if "taxis" not in st.session_state:
    st.session_state.taxis = make_taxis()

if "pickup" not in st.session_state:
    st.session_state.pickup = None

if "selected_taxi" not in st.session_state:
    st.session_state.selected_taxi = None

if "last_tick" not in st.session_state:
    st.session_state.last_tick = time.time()

if "last_map_click" not in st.session_state:
    st.session_state.last_map_click = None

if "booking_message" not in st.session_state:
    st.session_state.booking_message = ""

# ---------------------------- Header ----------------------------

st.markdown(
    "<h1 style='text-align:center;'>🚕 TaxiGo</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="taxigo-subtitle">'
    "SMART TAXI FINDER · Live educational simulation · Plovdiv"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ---------------------------- Sidebar ----------------------------

with st.sidebar:
    st.title("⚙️ Control panel")
    st.caption("This is a simulation. No real taxis or GPS devices are connected.")

    if st.button("🔄 Generate new taxis", use_container_width=True):
        st.session_state.taxis = make_taxis()
        st.session_state.pickup = None
        st.session_state.selected_taxi = None
        st.session_state.last_map_click = None
        st.session_state.booking_message = ""
        st.session_state.last_tick = time.time()
        st.rerun()

    if st.button("📍 Clear pickup point", use_container_width=True):
        st.session_state.pickup = None
        st.session_state.selected_taxi = None
        st.session_state.last_map_click = None
        st.session_state.booking_message = ""
        st.rerun()

    st.divider()
    st.markdown("### Map legend")
    st.markdown("🟢 Available taxi")
    st.markdown("🟠 Taxi travelling to pickup")
    st.markdown("🔴 Taxi arrived")
    st.markdown("📍 Your pickup point")
    st.divider()
    st.caption(f"Map refresh interval: {REFRESH_SECONDS} seconds")

# ---------------------------- Main layout ----------------------------

map_col, info_col = st.columns([2.15, 1], gap="large")

with map_col:
    st.subheader("🗺️ Live taxi map")
    st.caption("Click the map once to set your pickup point. Taxi markers show simulated vehicles.")

    # The map runs in its own fragment. Its periodic refresh does not rerun
    # the entire Streamlit page, which substantially reduces iframe flicker.
    @st.fragment(run_every=f"{REFRESH_SECONDS}s")
    def live_taxi_map():
        current_time = time.time()
        elapsed = current_time - st.session_state.last_tick
        if elapsed >= REFRESH_SECONDS:
            advance_taxis(elapsed)
            st.session_state.last_tick = current_time

        taxi_map = build_map()
        map_result = st_folium(
            taxi_map,
            width=None,
            height=570,
            key="taxigo_folium_map",
            returned_objects=["last_clicked"],
            use_container_width=True,
        )

        clicked = map_result.get("last_clicked") if map_result else None
        if clicked:
            click_key = (round(clicked["lat"], 6), round(clicked["lng"], 6))
            if click_key != st.session_state.last_map_click:
                st.session_state.last_map_click = click_key
                st.session_state.pickup = (clicked["lat"], clicked["lng"])
                st.session_state.selected_taxi = None
                st.session_state.booking_message = ""
                st.rerun(scope="app")

    live_taxi_map()

with info_col:
    st.subheader("🚖 Nearby taxis")

    pickup = st.session_state.pickup
    ranked_taxis = []

    if pickup is None:
        st.info("Choose a pickup point by clicking anywhere on the map.")
        st.markdown(
            """
            **How it works**
            1. Click your pickup point on the map.
            2. Compare taxi distances and arrival estimates.
            3. Select a taxi.
            4. Press **Call taxi** to send it to your point.
            """
        )
    else:
        st.success(f"Pickup selected: {pickup[0]:.5f}, {pickup[1]:.5f}")

        for taxi in st.session_state.taxis:
            if taxi["status"] != "Available":
                continue
            distance, road_distance, eta = estimate_eta(taxi, pickup)
            ranked_taxis.append(
                {
                    "taxi": taxi,
                    "distance": distance,
                    "road_distance": road_distance,
                    "eta": eta,
                }
            )

        ranked_taxis.sort(key=lambda item: item["eta"])

        if not ranked_taxis:
            st.warning("There are no available taxis right now. Generate new taxis or wait for a taxi to become available.")
        else:
            fastest = ranked_taxis[0]
            st.markdown(
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

# The map fragment above refreshes independently every few seconds.
# On Streamlit versions older than 1.37, upgrade Streamlit using requirements.txt.
