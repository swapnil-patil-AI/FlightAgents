import random
import string
import uuid
from datetime import datetime
from langchain_core.tools import tool


def _generate_confirmation_number() -> str:
    prefix = "FB"
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"{prefix}{suffix}"


def _generate_pnr() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))


@tool
def book_flight(
    airline: str,
    flight_number: str,
    origin: str,
    destination: str,
    departure_datetime: str,
    arrival_datetime: str,
    passenger_name: str,
    passenger_email: str,
    price_per_person: float,
    num_passengers: int = 1,
    seat_class: str = "Economy",
) -> dict:
    """Book a flight for passengers. Simulates the booking process and returns a confirmation.

    Args:
        airline: Airline name (e.g., 'Delta Airlines')
        flight_number: Flight number (e.g., 'DL 401')
        origin: Departure airport/city
        destination: Arrival airport/city
        departure_datetime: Departure date and time (e.g., '2025-06-15 08:30')
        arrival_datetime: Arrival date and time (e.g., '2025-06-15 20:45')
        passenger_name: Full name of the primary passenger
        passenger_email: Email address of the passenger
        price_per_person: Price per passenger in USD
        num_passengers: Number of passengers (default 1)
        seat_class: Class of service — Economy, Business, or First (default Economy)

    Returns:
        Dictionary containing booking confirmation details.
    """
    total_price = price_per_person * num_passengers
    confirmation_number = _generate_confirmation_number()
    pnr = _generate_pnr()
    booking_id = str(uuid.uuid4())[:8].upper()

    # Seat assignments
    seat_rows = {"Economy": range(20, 45), "Business": range(5, 20), "First": range(1, 5)}
    rows = seat_rows.get(seat_class, range(20, 45))
    seats = [
        f"{random.choice(list(rows))}{random.choice('ABCDEF')}"
        for _ in range(num_passengers)
    ]

    booking = {
        "status": "CONFIRMED",
        "booking_id": booking_id,
        "confirmation_number": confirmation_number,
        "pnr": pnr,
        "airline": airline,
        "flight_number": flight_number,
        "origin": origin,
        "destination": destination,
        "departure_datetime": departure_datetime,
        "arrival_datetime": arrival_datetime,
        "passenger_name": passenger_name,
        "passenger_email": passenger_email,
        "num_passengers": num_passengers,
        "seat_class": seat_class,
        "seats": seats,
        "price_per_person": price_per_person,
        "total_price": total_price,
        "currency": "USD",
        "booked_at": datetime.now().isoformat(),
        "baggage_allowance": "1 carry-on + 1 checked bag" if seat_class == "Economy" else "2 checked bags",
        "meal_included": seat_class in ("Business", "First"),
        "cancellation_policy": "Free cancellation within 24 hours of booking",
    }

    return booking


@tool
def verify_booking(confirmation_number: str, passenger_name: str) -> dict:
    """Verify that a flight booking exists and is confirmed.

    Args:
        confirmation_number: The booking confirmation number (e.g., 'FBXYZ123')
        passenger_name: Full name of the passenger to verify against

    Returns:
        Dictionary with verification status and booking details.
    """
    if confirmation_number.startswith("FB") and len(confirmation_number) == 8:
        return {
            "verified": True,
            "status": "CONFIRMED",
            "confirmation_number": confirmation_number,
            "passenger_name": passenger_name,
            "message": (
                f"Booking {confirmation_number} for {passenger_name} is confirmed "
                f"and active. Check-in opens 24 hours before departure."
            ),
        }

    return {
        "verified": False,
        "status": "NOT_FOUND",
        "confirmation_number": confirmation_number,
        "message": f"Booking {confirmation_number} could not be verified.",
    }
