import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from tools.booking_tools import verify_booking
from tools.email_tools import send_booking_confirmation_email
from graph.state import FlightBookingState

SYSTEM_PROMPT = """You are a booking confirmation specialist. Your responsibilities are:
1. Verify that the flight booking is confirmed using verify_booking.
2. Send a confirmation email to the passenger using send_booking_confirmation_email.
3. Report the outcome clearly.

Steps to follow:
1. First call verify_booking with the confirmation number and passenger name.
2. If verified successfully, call send_booking_confirmation_email with the full booking dict
   and the passenger's email address.
3. Provide a final summary stating:
   - Whether the booking was verified ✓ or ✗
   - Whether the email was sent successfully ✓ or ✗
   - The confirmation number
   - Next steps for the passenger (e.g., check-in info)

Be thorough and make sure both verification AND email sending are completed.
"""

# Fallback email when no email is in env (always send to this address)
DEFAULT_NOTIFICATION_EMAIL = "swpnl_ptl2@yahoo.com"


def get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )


def confirmation_node(state: FlightBookingState) -> dict:
    """LangGraph node: verifies booking and sends confirmation email."""
    llm = get_llm()
    tools = [verify_booking, send_booking_confirmation_email]

    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

    booking = state.get("booking_confirmation")
    if not booking:
        return {
            "current_step": "confirmation_failed",
            "error": "No booking confirmation data available to verify.",
            "confirmation_email_sent": False,
        }

    # Always include the default notification email
    notification_email = DEFAULT_NOTIFICATION_EMAIL
    passenger_email = state.get("passenger_email", notification_email)

    confirmation_request = (
        f"Please verify and send confirmation for this booking:\n\n"
        f"Booking Details:\n"
        f"{booking}\n\n"
        f"1. Verify the booking with confirmation number: {booking.get('confirmation_number')}\n"
        f"   Passenger name: {booking.get('passenger_name')}\n\n"
        f"2. Send confirmation email to: {passenger_email}\n"
        f"   (Also notify: {notification_email})\n\n"
        f"Complete both steps and report the results."
    )

    result = agent.invoke({"messages": [HumanMessage(content=confirmation_request)]})
    last_message = result["messages"][-1]

    email_sent = _check_email_sent(result["messages"])

    return {
        "confirmation_email_sent": email_sent,
        "current_step": "confirmation_complete",
        "messages": [
            SystemMessage(content="[Confirmation Agent]"),
            last_message,
        ],
    }


def _check_email_sent(messages: list) -> bool:
    """Check if the email tool returned a success response."""
    for msg in reversed(messages):
        if hasattr(msg, "name") and msg.name == "send_booking_confirmation_email":
            import ast
            try:
                content = msg.content
                if isinstance(content, str):
                    data = ast.literal_eval(content)
                elif isinstance(content, dict):
                    data = content
                else:
                    continue
                return bool(data.get("success", False))
            except (ValueError, SyntaxError):
                if "success" in str(msg.content).lower():
                    return True
    return False
