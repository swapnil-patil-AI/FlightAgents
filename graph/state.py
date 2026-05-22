from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class FlightBookingState(TypedDict):
    # User inputs
    origin: str
    destination: str
    travel_date: str
    return_date: Optional[str]
    num_passengers: int
    passenger_name: str
    passenger_email: str
    trip_type: str  # "one-way" or "round-trip"

    # Agent outputs
    flight_results: list
    selected_flight: Optional[dict]
    booking_confirmation: Optional[dict]
    confirmation_email_sent: bool

    # Flow control
    messages: Annotated[list, add_messages]
    current_step: str
    error: Optional[str]
