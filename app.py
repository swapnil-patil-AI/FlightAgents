import os
import sys
import threading
import queue
import streamlit as st
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# Load Streamlit Cloud secrets into env vars if running on Streamlit Cloud
try:
    for key in ["ANTHROPIC_API_KEY", "TAVILY_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # secrets not available locally — that's fine

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FlightAgents AI",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .main-header {
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    color: white; padding: 2rem; border-radius: 12px; text-align: center; margin-bottom: 2rem;
  }
  .agent-card {
    border: 1px solid #e0e0e0; border-radius: 10px; padding: 1.2rem;
    margin-bottom: 1rem; background: #fafafa;
  }
  .agent-card.active { border-color: #1a73e8; background: #e8f0fe; }
  .agent-card.done   { border-color: #34a853; background: #e6f4ea; }
  .agent-card.error  { border-color: #ea4335; background: #fce8e6; }
  .step-icon { font-size: 1.6rem; margin-right: 0.5rem; }
  .price-tag {
    background: #1a73e8; color: white; padding: 0.3rem 0.8rem;
    border-radius: 20px; font-weight: bold; font-size: 1.1rem;
  }
  .confirmation-box {
    background: linear-gradient(135deg, #34a853, #1a73e8);
    color: white; padding: 1.5rem; border-radius: 12px; text-align: center;
    font-size: 1.1rem; margin: 1rem 0;
  }
  .confirmation-number { font-size: 2rem; font-weight: bold; letter-spacing: 4px; }
  .flight-option {
    border: 2px solid #e0e0e0; border-radius: 10px; padding: 1rem;
    margin-bottom: 0.8rem; cursor: pointer; transition: all 0.2s;
  }
  .flight-option:hover  { border-color: #1a73e8; background: #e8f0fe; }
  .flight-option.selected { border-color: #1a73e8; background: #e8f0fe; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
  <h1>✈ FlightAgents AI</h1>
  <p style="font-size:1.1rem; opacity:0.9;">
    Three AI agents work together to search, book, and confirm your flights
  </p>
</div>
""",
    unsafe_allow_html=True,
)


# ── Session state defaults ────────────────────────────────────────────────────
def init_session():
    defaults = {
        "step": "input",
        "flight_results": [],
        "selected_flight_idx": 0,
        "booking_confirmation": None,
        "email_sent": False,
        "agent_logs": {},
        "running": False,
        "final_state": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ── Sidebar: API keys ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔑 API Configuration")

    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Required for the AI agents",
    )
    tavily_key = st.text_input(
        "Tavily API Key",
        value=os.getenv("TAVILY_API_KEY", ""),
        type="password",
        help="Required for flight search",
    )
    gmail_user = st.text_input(
        "Gmail Address",
        value=os.getenv("GMAIL_USER", ""),
        help="Gmail account to send confirmation from",
    )
    gmail_pass = st.text_input(
        "Gmail App Password",
        value=os.getenv("GMAIL_APP_PASSWORD", ""),
        type="password",
        help="16-char app password (not your regular password)",
    )

    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key
    if gmail_user:
        os.environ["GMAIL_USER"] = gmail_user
    if gmail_pass:
        os.environ["GMAIL_APP_PASSWORD"] = gmail_pass

    st.divider()
    st.markdown("### How it works")
    st.markdown(
        """
**Agent 1 — Flight Search**
Searches the web using Tavily to find the best available flights.

**Agent 2 — Booking**
Books your selected flight and generates a confirmation.

**Agent 3 — Confirmation**
Verifies the booking and emails you the confirmation.
"""
    )

    st.divider()
    if st.button("🔄 Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ── Agent status display ──────────────────────────────────────────────────────
def agent_status_panel(current_step: str):
    agents = [
        ("flight_search", "🔍", "Agent 1: Flight Search", "Searching for the best flights..."),
        ("booking", "🎫", "Agent 2: Booking", "Processing your booking..."),
        ("confirmation", "✉", "Agent 3: Confirmation", "Verifying & sending email..."),
    ]
    completed = {
        "search_complete": {"flight_search"},
        "booking_complete": {"flight_search", "booking"},
        "confirmation_complete": {"flight_search", "booking", "confirmation"},
        "booking_failed": {"flight_search"},
        "confirmation_failed": {"flight_search", "booking"},
    }.get(current_step, set())

    active = {
        "searching": "flight_search",
        "booking": "booking",
        "confirming": "confirmation",
    }.get(current_step, "")

    cols = st.columns(3)
    for col, (key, icon, title, desc) in zip(cols, agents):
        with col:
            if key in completed:
                css = "done"
                status = "✅ Complete"
            elif key == active:
                css = "active"
                status = "⏳ Running..."
            else:
                css = ""
                status = "⏸ Waiting"
            st.markdown(
                f'<div class="agent-card {css}">'
                f'<span class="step-icon">{icon}</span><strong>{title}</strong><br>'
                f'<small style="color:#666">{desc}</small><br>'
                f'<small>{status}</small>'
                f"</div>",
                unsafe_allow_html=True,
            )


# ── STEP 1: Input form ────────────────────────────────────────────────────────
if st.session_state.step == "input":
    st.subheader("Search Flights")

    with st.form("flight_form"):
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("From (City or Airport)", placeholder="e.g., New York JFK")
            travel_date = st.date_input(
                "Departure Date", min_value=date.today() + timedelta(days=1)
            )
            trip_type = st.radio("Trip Type", ["One-way", "Round-trip"], horizontal=True)
            num_passengers = st.number_input("Passengers", min_value=1, max_value=9, value=1)
        with col2:
            destination = st.text_input("To (City or Airport)", placeholder="e.g., London LHR")
            return_date = st.date_input(
                "Return Date",
                min_value=date.today() + timedelta(days=2),
                disabled=(trip_type == "One-way"),
            )
            passenger_name = st.text_input("Passenger Full Name", placeholder="John Doe")
            passenger_email = st.text_input(
                "Passenger Email",
                value="swpnl_ptl2@yahoo.com",
                placeholder="your@email.com",
            )

        submitted = st.form_submit_button("🚀 Search & Book Flights", use_container_width=True, type="primary")

    if submitted:
        if not all([origin, destination, passenger_name, passenger_email]):
            st.error("Please fill in all required fields.")
        elif not os.getenv("ANTHROPIC_API_KEY"):
            st.error("Please enter your Anthropic API Key in the sidebar.")
        elif not os.getenv("TAVILY_API_KEY"):
            st.error("Please enter your Tavily API Key in the sidebar.")
        else:
            st.session_state.form_data = {
                "origin": origin,
                "destination": destination,
                "travel_date": str(travel_date),
                "return_date": str(return_date) if trip_type == "Round-trip" else None,
                "num_passengers": num_passengers,
                "passenger_name": passenger_name,
                "passenger_email": passenger_email,
                "trip_type": trip_type.lower().replace("-", "_"),
            }
            st.session_state.step = "running"
            st.rerun()


# ── STEP 2: Running agents ─────────────────────────────────────────────────────
elif st.session_state.step == "running":
    fd = st.session_state.form_data

    st.info(
        f"**{fd['origin']} → {fd['destination']}** | "
        f"{fd['travel_date']} | "
        f"{fd['num_passengers']} passenger(s) | "
        f"Passenger: {fd['passenger_name']}"
    )

    status_placeholder = st.empty()
    log_placeholder = st.empty()
    progress_bar = st.progress(0)

    def run_agents():
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
        return graph.invoke(initial_state)

    with st.spinner("AI Agents are working on your booking..."):
        steps = [
            ("🔍 Agent 1 searching for flights...", 15),
            ("🎫 Agent 2 booking your flight...", 50),
            ("✉  Agent 3 confirming & sending email...", 85),
        ]

        for msg, pct in steps:
            status_placeholder.info(msg)
            progress_bar.progress(pct)

        try:
            final_state = run_agents()
            progress_bar.progress(100)
            status_placeholder.success("✅ All agents completed successfully!")

            st.session_state.final_state = final_state
            st.session_state.flight_results = final_state.get("flight_results", [])
            st.session_state.booking_confirmation = final_state.get("booking_confirmation")
            st.session_state.email_sent = final_state.get("confirmation_email_sent", False)
            st.session_state.step = "results"
            st.rerun()

        except Exception as e:
            status_placeholder.error(f"An error occurred: {str(e)}")
            st.exception(e)
            if st.button("Try Again"):
                st.session_state.step = "input"
                st.rerun()


# ── STEP 3: Results ───────────────────────────────────────────────────────────
elif st.session_state.step == "results":
    final_state = st.session_state.final_state
    fd = st.session_state.form_data

    # Trip summary banner
    st.markdown(
        f"""
<div style="background:#e8f0fe; padding:1rem; border-radius:10px; margin-bottom:1.5rem;">
  <strong>✈ {fd['origin']}</strong> → <strong>{fd['destination']}</strong> &nbsp;|&nbsp;
  {fd['travel_date']} &nbsp;|&nbsp; {fd['num_passengers']} passenger(s) &nbsp;|&nbsp;
  Passenger: {fd['passenger_name']}
</div>
""",
        unsafe_allow_html=True,
    )

    agent_status_panel("confirmation_complete")
    st.divider()

    # ── Flight Results ────────────────────────────────────────────────────────
    with st.expander("🔍 Agent 1 — Flight Search Results", expanded=True):
        flights = st.session_state.flight_results
        if flights:
            st.success(f"Found {len(flights)} flight options")
            for f in flights:
                direct_badge = "🟢 Direct" if f.get("direct") else "🔄 1 Stop"
                st.markdown(
                    f"""
<div class="flight-option">
  <strong>Option {f['option_number']}</strong> &nbsp;
  <strong>{f['airline']}</strong> ({f['flight_number']}) &nbsp; {direct_badge}<br>
  🛫 {f['origin']} → 🛬 {f['destination']}<br>
  🕐 Dep: <strong>{f['departure_datetime']}</strong> &nbsp; Arr: <strong>{f['arrival_datetime']}</strong><br>
  ⏱ Duration: {f['duration_hours']}h &nbsp;
  💰 <span class="price-tag">${f['price_per_person']:.2f}/person</span>
  &nbsp; Total: <strong>${f['total_price']:.2f}</strong>
</div>
""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No flight results were captured.")

        # Show agent's message
        messages = final_state.get("messages", [])
        search_msgs = [m for m in messages if hasattr(m, "content") and "[Flight Search Agent]" not in str(m.content)]
        if search_msgs and hasattr(search_msgs[0], "content"):
            with st.expander("Agent reasoning"):
                st.text(search_msgs[0].content[:2000] if search_msgs else "")

    # ── Booking Confirmation ──────────────────────────────────────────────────
    booking = st.session_state.booking_confirmation
    with st.expander("🎫 Agent 2 — Booking Confirmation", expanded=True):
        if booking:
            st.success(f"Booking confirmed! Status: **{booking.get('status', 'CONFIRMED')}**")

            c1, c2, c3 = st.columns(3)
            c1.metric("Confirmation #", booking.get("confirmation_number", "N/A"))
            c2.metric("PNR", booking.get("pnr", "N/A"))
            c3.metric("Booking ID", booking.get("booking_id", "N/A"))

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
                st.markdown("**Price & Inclusions**")
                st.write(f"👤 **Passengers:** {booking.get('num_passengers', 1)}")
                st.write(f"💰 **Per person:** ${booking.get('price_per_person', 0):.2f}")
                st.write(f"💳 **Total paid:** ${booking.get('total_price', 0):.2f} {booking.get('currency', 'USD')}")
                st.write(f"🧳 **Baggage:** {booking.get('baggage_allowance')}")
                st.write(f"🍽 **Meal:** {'Yes' if booking.get('meal_included') else 'No'}")
                st.write(f"🔄 **Cancellation:** {booking.get('cancellation_policy')}")
        else:
            st.warning("Booking confirmation details not available.")

    # ── Email Confirmation ────────────────────────────────────────────────────
    with st.expander("✉ Agent 3 — Confirmation Email", expanded=True):
        if st.session_state.email_sent:
            st.markdown(
                f"""
<div class="confirmation-box">
  <div>✅ Confirmation Email Sent Successfully!</div>
  <div style="font-size:0.9rem; opacity:0.85; margin-top:0.5rem;">
    Sent to: <strong>{fd.get('passenger_email', 'swpnl_ptl2@yahoo.com')}</strong>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            if not os.getenv("GMAIL_USER") or not os.getenv("GMAIL_APP_PASSWORD"):
                st.warning(
                    "⚠️ Email not sent — Gmail credentials not configured in the sidebar. "
                    "All other steps completed successfully."
                )
            else:
                st.warning("⚠️ Email sending was attempted but may not have succeeded.")

    # ── Big confirmation number ───────────────────────────────────────────────
    if booking:
        st.markdown(
            f"""
<div class="confirmation-box" style="margin-top:2rem;">
  <div style="font-size:1rem; opacity:0.85;">Your Booking Confirmation Number</div>
  <div class="confirmation-number">{booking.get('confirmation_number', 'N/A')}</div>
  <div style="font-size:0.9rem; opacity:0.75; margin-top:0.5rem;">
    Save this number for check-in. Online check-in opens 24 hours before departure.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── Agent conversation log ────────────────────────────────────────────────
    with st.expander("🤖 Full Agent Conversation Log"):
        messages = final_state.get("messages", []) if final_state else []
        for i, msg in enumerate(messages):
            role = type(msg).__name__.replace("Message", "")
            content = msg.content if hasattr(msg, "content") else str(msg)
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )
            if content and content.strip():
                label = {"Human": "👤 User", "AI": "🤖 Agent", "System": "⚙ System", "Tool": "🔧 Tool"}.get(role, role)
                st.markdown(f"**{label}**")
                st.text(str(content)[:800])
                st.divider()

    # ── New search button ─────────────────────────────────────────────────────
    if st.button("✈ Book Another Flight", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
