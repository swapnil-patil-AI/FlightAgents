import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from tools.booking_tools import book_flight, verify_booking
from graph.state import FlightBookingState

SYSTEM_PROMPT = """You are a flight booking specialist. Your job is to process flight bookings \
for passengers using the available booking tools.

When booking a flight:
1. Use the book_flight tool with all required details from the selected flight and passenger info.
2. After booking, immediately use verify_booking to confirm the reservation.
3. Return a clear summary of:
   - Confirmation number and PNR
   - Booking status
   - Flight details (airline, number, route, times)
   - Seat assignments
   - Total price paid
   - Baggage and meal information

Always verify the booking after making it. If verification fails, report the issue clearly.
"""


def get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )


def booking_node(state: FlightBookingState) -> dict:
    """LangGraph node: books the selected flight and updates state with confirmation."""
    llm = get_llm()
    tools = [book_flight, verify_booking]

    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

    flight = state.get("selected_flight")
    if not flight:
        # Auto-select the cheapest flight if none selected
        results = state.get("flight_results", [])
        if not results:
            return {
                "current_step": "booking_failed",
                "error": "No flight results available to book.",
            }
        flight = min(results, key=lambda f: f.get("price_per_person", float("inf")))

    booking_request = (
        f"Please book the following flight:\n\n"
        f"Airline: {flight.get('airline')}\n"
        f"Flight Number: {flight.get('flight_number')}\n"
        f"From: {flight.get('origin')}\n"
        f"To: {flight.get('destination')}\n"
        f"Departure: {flight.get('departure_datetime')}\n"
        f"Arrival: {flight.get('arrival_datetime')}\n"
        f"Price per person: ${flight.get('price_per_person', 0):.2f}\n"
        f"Number of passengers: {state['num_passengers']}\n\n"
        f"Passenger Details:\n"
        f"Name: {state['passenger_name']}\n"
        f"Email: {state['passenger_email']}\n\n"
        f"After booking, verify the confirmation immediately."
    )

    result = agent.invoke({"messages": [HumanMessage(content=booking_request)]})
    last_message = result["messages"][-1]

    # Extract booking confirmation from tool calls in the message history
    booking_data = _extract_booking_from_messages(result["messages"])

    return {
        "selected_flight": flight,
        "booking_confirmation": booking_data,
        "current_step": "booking_complete",
        "messages": [
            SystemMessage(content="[Booking Agent]"),
            last_message,
        ],
    }


def _extract_booking_from_messages(messages: list) -> dict | None:
    """Pull the booking dict returned by the book_flight tool from message history."""
    for msg in reversed(messages):
        # ToolMessage content may be a string repr of a dict or a dict directly
        if hasattr(msg, "content") and hasattr(msg, "name") and msg.name == "book_flight":
            import ast
            try:
                if isinstance(msg.content, dict):
                    return msg.content
                if isinstance(msg.content, str):
                    return ast.literal_eval(msg.content)
            except (ValueError, SyntaxError):
                pass
    return None
