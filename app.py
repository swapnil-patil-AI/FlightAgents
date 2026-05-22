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
        "step": "input",
        "flight_results": [],
        "selected_flight_idx": 0,
        "booking_confirmation": None,
        "email_sent": False,
        "final_state": None,
        "form_data": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔑 API Keys")

    anthropic_key = st.text_input("Anthropic API Key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")
    tavily_key    = st.text_input("Tavily API Key",    value=os.getenv("TAVILY_API_KEY", ""),    type="password")
    gmail_user    = st.text_input("Gmail Address",     value=os.getenv("GMAIL_USER", ""))
    gmail_pass    = st.text_input("Gmail App Password",value=os.getenv("GMAIL_APP_PASSWORD", ""),type="password")

    if anthropic_key: os.environ["ANTHROPIC_API_KEY"]   = anthropic_key
    if tavily_key:    os.environ["TAVILY_API_KEY"]       = tavily_key
    if gmail_user:    os.environ["GMAIL_USER"]           = gmail_user
    if gmail_pass:    os.environ["GMAIL_APP_PASSWORD"]   = gmail_pass

    st.divider()
    st.markdown("**How it works**")
    st.markdown("1. 🔍 Agent 1 searches for flights\n2. 🎫 Agent 2 books your ticket\n3. ✉ Agent 3 confirms & emails you")
    st.divider()
    if st.button("🔄 Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("✈ FlightAgents AI")
st.caption("Three AI agents collaborate to search, book, and confirm your flight end-to-end.")
st.divider()


# ── STEP 1: Input ─────────────────────────────────────────────────────────────
if st.session_state.step == "input":
    st.subheader("Search & Book a Flight")

    with st.form("flight_form"):
        col1, col2 = st.columns(2)

        with col1:
            origin      = st.text_input("From (City or Airport)", placeholder="e.g. New York JFK")
            travel_date = st.date_input("Departure Date", min_value=date.today() + timedelta(days=1))
            trip_type   = st.radio("Trip Type", ["One-way", "Round-trip"], horizontal=True)
            passengers  = st.number_input("Passengers", min_value=1, max_value=9, value=1)

        with col2:
            destination  = st.text_input("To (City or Airport)", placeholder="e.g. London LHR")
            return_date  = st.date_input(
                "Return Date",
                min_value=date.today() + timedelta(days=2),
                disabled=(trip_type == "One-way"),
            )
            pax_name  = st.text_input("Passenger Full Name", placeholder="John Doe")
            pax_email = st.text_input("Passenger Email", value="swpnl_ptl2@yahoo.com")

        submitted = st.form_submit_button("🚀 Search & Book", use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not origin:      errors.append("Origin is required.")
        if not destination: errors.append("Destination is required.")
        if not pax_name:    errors.append("Passenger name is required.")
        if not pax_email:   errors.append("Passenger email is required.")
        if not os.getenv("ANTHROPIC_API_KEY"): errors.append("Anthropic API Key is required.")
        if not os.getenv("TAVILY_API_KEY"):    errors.append("Tavily API Key is required.")

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
            st.session_state.step = "running"
            st.rerun()


# ── STEP 2: Running agents ─────────────────────────────────────────────────────
elif st.session_state.step == "running":
    fd = st.session_state.form_data

    st.subheader("Agents at Work")
    st.info(f"**{fd['origin']}** → **{fd['destination']}** | {fd['travel_date']} | {fd['num_passengers']} passenger(s)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Agent 1", "🔍 Flight Search", "Searching...")
    col2.metric("Agent 2", "🎫 Booking",       "Waiting")
    col3.metric("Agent 3", "✉ Confirmation",   "Waiting")

    with st.spinner("Running all three agents... this may take 1-2 minutes."):
        try:
            from graph.workflow import get_graph

            graph = get_graph()
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

            final_state = graph.invoke(initial_state)

            st.session_state.final_state         = final_state
            st.session_state.flight_results      = final_state.get("flight_results", [])
            st.session_state.booking_confirmation = final_state.get("booking_confirmation")
            st.session_state.email_sent          = final_state.get("confirmation_email_sent", False)
            st.session_state.step                = "results"
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.exception(e)
            if st.button("Try Again"):
                st.session_state.step = "input"
                st.rerun()


# ── STEP 3: Results ───────────────────────────────────────────────────────────
elif st.session_state.step == "results":
    fd           = st.session_state.form_data
    final_state  = st.session_state.final_state
    booking      = st.session_state.booking_confirmation

    st.subheader("Booking Complete!")
    st.success(f"All three agents finished — **{fd['origin']}** → **{fd['destination']}** on {fd['travel_date']}")

    # Agent status
    col1, col2, col3 = st.columns(3)
    col1.metric("Agent 1 — Flight Search", "✅ Done")
    col2.metric("Agent 2 — Booking",       "✅ Done")
    col3.metric("Agent 3 — Confirmation",  "✅ Done" if st.session_state.email_sent else "⚠ Check logs")

    st.divider()

    # Flight results
    with st.expander("🔍 Flight Search Results", expanded=True):
        flights = st.session_state.flight_results
        if flights:
            for f in flights:
                direct = "Direct" if f.get("direct") else "1 Stop"
                st.markdown(
                    f"**Option {f['option_number']}: {f['airline']}** ({f['flight_number']}) — {direct}  \n"
                    f"🛫 {f['departure_datetime']} → 🛬 {f['arrival_datetime']}  \n"
                    f"💰 **${f['price_per_person']:.2f}/person** | Total: **${f['total_price']:.2f}**"
                )
                st.divider()
        else:
            st.warning("No structured flight results captured — see agent log below.")

    # Booking confirmation
    with st.expander("🎫 Booking Confirmation", expanded=True):
        if booking:
            st.success(f"Status: **{booking.get('status', 'CONFIRMED')}**")

            c1, c2, c3 = st.columns(3)
            c1.metric("Confirmation #", booking.get("confirmation_number", "N/A"))
            c2.metric("PNR",            booking.get("pnr", "N/A"))
            c3.metric("Total Paid",     f"${booking.get('total_price', 0):.2f} {booking.get('currency','USD')}")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Airline:** {booking.get('airline')}")
                st.write(f"**Flight:** {booking.get('flight_number')}")
                st.write(f"**Route:** {booking.get('origin')} → {booking.get('destination')}")
                st.write(f"**Departure:** {booking.get('departure_datetime')}")
                st.write(f"**Arrival:** {booking.get('arrival_datetime')}")
            with col2:
                st.write(f"**Class:** {booking.get('seat_class', 'Economy')}")
                st.write(f"**Seats:** {', '.join(booking.get('seats', []))}")
                st.write(f"**Baggage:** {booking.get('baggage_allowance')}")
                st.write(f"**Meal:** {'Yes' if booking.get('meal_included') else 'No'}")
                st.write(f"**Cancellation:** {booking.get('cancellation_policy')}")
        else:
            st.warning("Booking details not available.")

    # Email confirmation
    with st.expander("✉ Email Confirmation", expanded=True):
        if st.session_state.email_sent:
            st.success(f"Confirmation email sent to **{fd.get('passenger_email')}**")
        else:
            if not os.getenv("GMAIL_USER") or not os.getenv("GMAIL_APP_PASSWORD"):
                st.warning("Email not sent — Gmail credentials not configured in the sidebar.")
            else:
                st.warning("Email sending was attempted but may not have succeeded.")

    # Agent conversation log
    with st.expander("🤖 Agent Conversation Log"):
        messages = final_state.get("messages", []) if final_state else []
        for msg in messages:
            role    = type(msg).__name__.replace("Message", "")
            content = msg.content if hasattr(msg, "content") else str(msg)
            if isinstance(content, list):
                content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            if content and str(content).strip():
                st.markdown(f"**{role}**")
                st.text(str(content)[:600])
                st.divider()

    if st.button("✈ Book Another Flight", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
