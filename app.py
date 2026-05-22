import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="FlightAgents AI",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Streamlit Cloud secrets after set_page_config
try:
    for key in ["ANTHROPIC_API_KEY", "TAVILY_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass


# ── Session state ─────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "step": "input",          # input → searching → select_flight → booking → results
        "form_data": {},
        "search_state": None,     # full state after Agent 1
        "flight_results": [],
        "selected_flight_idx": 0,
        "booking_state": None,    # full state after Agents 2+3
        "booking_confirmation": None,
        "email_sent": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✈ FlightAgents AI")
    st.markdown(
        "**How it works**\n\n"
        "1. 🔍 **Agent 1** searches the web for the best flights\n"
        "2. 🖱 **You** pick your preferred option\n"
        "3. 🎫 **Agent 2** books the selected flight\n"
        "4. ✉ **Agent 3** verifies & emails your confirmation"
    )
    st.divider()
    if st.button("🔄 Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("✈ FlightAgents AI")
st.caption("Three AI agents collaborate to search, book, and confirm your flight end-to-end.")

# Progress indicator
step_map = {"input": 1, "searching": 1, "select_flight": 2, "booking": 3, "results": 4}
current_step_num = step_map.get(st.session_state.step, 1)
st.progress(current_step_num / 4)
cols = st.columns(4)
labels = ["1. Search Details", "2. Choose Flight", "3. Booking", "4. Confirmation"]
for i, (col, label) in enumerate(zip(cols, labels), 1):
    if i < current_step_num:
        col.markdown(f"~~{label}~~ ✅")
    elif i == current_step_num:
        col.markdown(f"**{label}**")
    else:
        col.markdown(f"{label}")

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Input form
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "input":
    st.subheader("Step 1 — Enter Your Flight Details")

    with st.form("flight_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Trip Details**")
            origin      = st.text_input("From (City or Airport)", placeholder="e.g. New York JFK")
            destination = st.text_input("To (City or Airport)",   placeholder="e.g. London LHR")
            travel_date = st.date_input("Departure Date", min_value=date.today() + timedelta(days=1))
            trip_type   = st.radio("Trip Type", ["One-way", "Round-trip"], horizontal=True)
            return_date = st.date_input(
                "Return Date",
                min_value=date.today() + timedelta(days=2),
                disabled=(trip_type == "One-way"),
            )

        with col2:
            st.markdown("**Passenger Details**")
            pax_name    = st.text_input("Full Name",  placeholder="John Doe")
            pax_email   = st.text_input("Email Address", placeholder="your@email.com",
                                        help="Your booking confirmation will be sent here")
            passengers  = st.number_input("Number of Passengers", min_value=1, max_value=9, value=1)

        submitted = st.form_submit_button("🔍 Search Flights", use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not origin:      errors.append("Please enter the departure city/airport.")
        if not destination: errors.append("Please enter the destination city/airport.")
        if not pax_name:    errors.append("Please enter the passenger name.")
        if not pax_email:   errors.append("Please enter the passenger email.")
        if not os.getenv("ANTHROPIC_API_KEY"): errors.append("Anthropic API Key not configured.")
        if not os.getenv("TAVILY_API_KEY"):    errors.append("Tavily API Key not configured.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.form_data = {
                "origin": origin,
                "destination": destination,
                "travel_date": str(travel_date),
                "return_date": str(return_date) if trip_type == "Round-trip" else None,
                "num_passengers": int(passengers),
                "passenger_name": pax_name,
                "passenger_email": pax_email,
                "trip_type": trip_type.lower().replace("-", "_"),
            }
            st.session_state.step = "searching"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1b — Agent 1 running (flight search)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == "searching":
    fd = st.session_state.form_data
    st.subheader("Step 1 — Searching for Flights")
    st.info(f"**{fd['origin']}** → **{fd['destination']}** | {fd['travel_date']} | {fd['num_passengers']} passenger(s)")

    with st.spinner("🔍 Agent 1 is searching the web for the best flights..."):
        try:
            from graph.workflow import get_search_graph_cached

            graph = get_search_graph_cached()
            initial_state = {
                "origin": fd["origin"],
                "destination": fd["destination"],
                "travel_date": fd["travel_date"],
                "return_date": fd.get("return_date"),
                "num_passengers": fd["num_passengers"],
                "passenger_name": fd["passenger_name"],
                "passenger_email": fd["passenger_email"],
                "trip_type": fd.get("trip_type", "one_way"),
                "flight_results": [],
                "selected_flight": None,
                "booking_confirmation": None,
                "confirmation_email_sent": False,
                "messages": [],
                "current_step": "starting",
                "error": None,
            }

            search_state = graph.invoke(initial_state)

            st.session_state.search_state   = search_state
            st.session_state.flight_results = search_state.get("flight_results", [])
            st.session_state.step           = "select_flight"
            st.rerun()

        except Exception as e:
            st.error(f"Search failed: {e}")
            st.exception(e)
            if st.button("Try Again"):
                st.session_state.step = "input"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — User selects a flight
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == "select_flight":
    fd      = st.session_state.form_data
    flights = st.session_state.flight_results

    st.subheader("Step 2 — Choose Your Flight")
    st.success(f"Agent 1 found {len(flights)} flight options for **{fd['origin']} → {fd['destination']}** on {fd['travel_date']}")

    if not flights:
        st.warning("No flight options were found. Please try a different search.")
        if st.button("← Back to Search"):
            st.session_state.step = "input"
            st.rerun()
    else:
        # Build radio options
        options = []
        for f in flights:
            direct = "Direct" if f.get("direct") else "1 Stop"
            label = (
                f"Option {f['option_number']}: {f['airline']} ({f['flight_number']}) — {direct}  |  "
                f"{f['departure_datetime']} → {f['arrival_datetime']}  |  "
                f"${f['price_per_person']:.2f}/person  (Total: ${f['total_price']:.2f})"
            )
            options.append(label)

        selected = st.radio("Select a flight:", options, index=0)
        selected_idx = options.index(selected)

        # Show details of selected flight
        f = flights[selected_idx]
        with st.expander("Flight details", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Airline",    f['airline'])
            col2.metric("Flight",     f['flight_number'])
            col3.metric("Duration",   f"{f['duration_hours']}h")
            col4.metric("Price/pax",  f"${f['price_per_person']:.2f}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Departure",  f['departure_datetime'])
            col2.metric("Arrival",    f['arrival_datetime'])
            col3.metric("Total",      f"${f['total_price']:.2f}")

        st.divider()
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("← Back to Search"):
                st.session_state.step = "input"
                st.rerun()
        with col2:
            if st.button(f"✅ Book This Flight — ${f['total_price']:.2f} Total", type="primary", use_container_width=True):
                st.session_state.selected_flight_idx = selected_idx
                st.session_state.step = "booking"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Agent 2 + Agent 3 running (booking + confirmation)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == "booking":
    fd             = st.session_state.form_data
    flights        = st.session_state.flight_results
    selected_idx   = st.session_state.selected_flight_idx
    selected_flight = flights[selected_idx]

    st.subheader("Step 3 — Booking Your Flight")
    st.info(
        f"Booking **{selected_flight['airline']} {selected_flight['flight_number']}** — "
        f"{selected_flight['origin']} → {selected_flight['destination']}  |  "
        f"${selected_flight['total_price']:.2f} total"
    )

    col1, col2 = st.columns(2)
    col1.metric("Agent 2 — Booking",       "⏳ Running...")
    col2.metric("Agent 3 — Confirmation",  "⏸ Waiting")

    with st.spinner("🎫 Agent 2 is booking your flight and Agent 3 will send your confirmation email..."):
        try:
            from graph.workflow import get_booking_graph_cached

            graph = get_booking_graph_cached()

            booking_input = dict(st.session_state.search_state)
            booking_input["selected_flight"]  = selected_flight
            booking_input["messages"]         = []  # fresh message history

            booking_state = graph.invoke(booking_input)

            st.session_state.booking_state        = booking_state
            st.session_state.booking_confirmation = booking_state.get("booking_confirmation")
            st.session_state.email_sent           = booking_state.get("confirmation_email_sent", False)
            st.session_state.step                 = "results"
            st.rerun()

        except Exception as e:
            st.error(f"Booking failed: {e}")
            st.exception(e)
            if st.button("← Go Back"):
                st.session_state.step = "select_flight"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Results
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == "results":
    fd      = st.session_state.form_data
    booking = st.session_state.booking_confirmation

    st.subheader("Step 4 — Booking Confirmed!")
    st.success("All three agents have completed their tasks.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Agent 1 — Search",       "✅ Done")
    col2.metric("Agent 2 — Booking",      "✅ Done")
    col3.metric("Agent 3 — Email",        "✅ Sent" if st.session_state.email_sent else "⚠ Check logs")

    st.divider()

    if booking:
        # Confirmation number hero
        st.markdown(f"### Confirmation Number: `{booking.get('confirmation_number', 'N/A')}`")
        st.markdown(f"**PNR:** `{booking.get('pnr', 'N/A')}`  |  **Status:** {booking.get('status', 'CONFIRMED')}")
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Flight Details**")
            st.write(f"✈ **Airline:** {booking.get('airline')}")
            st.write(f"🔢 **Flight:** {booking.get('flight_number')}")
            st.write(f"🛫 **Route:** {booking.get('origin')} → {booking.get('destination')}")
            st.write(f"🕐 **Departure:** {booking.get('departure_datetime')}")
            st.write(f"🕐 **Arrival:** {booking.get('arrival_datetime')}")
            st.write(f"💺 **Class:** {booking.get('seat_class', 'Economy')}")
            st.write(f"💺 **Seats:** {', '.join(booking.get('seats', []))}")
        with col2:
            st.markdown("**Passenger & Price**")
            st.write(f"👤 **Passenger:** {booking.get('passenger_name')}")
            st.write(f"📧 **Email:** {booking.get('passenger_email')}")
            st.write(f"👥 **Passengers:** {booking.get('num_passengers', 1)}")
            st.write(f"💰 **Per person:** ${booking.get('price_per_person', 0):.2f}")
            st.write(f"💳 **Total paid:** ${booking.get('total_price', 0):.2f} {booking.get('currency', 'USD')}")
            st.write(f"🧳 **Baggage:** {booking.get('baggage_allowance')}")
            st.write(f"🍽 **Meal:** {'Yes' if booking.get('meal_included') else 'No'}")

        st.divider()

        if st.session_state.email_sent:
            st.success(f"✉ Confirmation email sent to **{fd.get('passenger_email')}**")
        else:
            st.warning("✉ Email not sent — check Gmail credentials in Streamlit secrets.")
    else:
        st.warning("Booking details not available.")

    # Agent log
    with st.expander("🤖 View Agent Conversation Logs"):
        for state_key in ["search_state", "booking_state"]:
            state = st.session_state.get(state_key)
            if not state:
                continue
            label = "Agent 1 — Flight Search" if state_key == "search_state" else "Agents 2 & 3 — Booking + Confirmation"
            st.markdown(f"**{label}**")
            for msg in state.get("messages", []):
                content = msg.content if hasattr(msg, "content") else str(msg)
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                if str(content).strip():
                    role = type(msg).__name__.replace("Message", "")
                    st.markdown(f"*{role}*")
                    st.text(str(content)[:600])
            st.divider()

    if st.button("✈ Book Another Flight", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
