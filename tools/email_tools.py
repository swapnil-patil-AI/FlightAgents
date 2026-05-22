import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_core.tools import tool


def _build_html_email(booking: dict) -> str:
    seats_str = ", ".join(booking.get("seats", []))
    meal = "Yes" if booking.get("meal_included") else "No"
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: auto; background: white; border-radius: 8px;
                  overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .header {{ background: #1a73e8; color: white; padding: 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 26px; }}
    .header p {{ margin: 5px 0 0; opacity: 0.85; }}
    .badge {{ display: inline-block; background: #34a853; color: white; padding: 6px 18px;
              border-radius: 20px; font-weight: bold; margin-top: 12px; font-size: 14px; }}
    .body {{ padding: 30px; }}
    .section {{ margin-bottom: 24px; }}
    .section h2 {{ color: #1a73e8; font-size: 16px; margin: 0 0 12px;
                   border-bottom: 2px solid #e8f0fe; padding-bottom: 6px; }}
    .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
    .label {{ color: #666; }}
    .value {{ font-weight: bold; color: #333; }}
    .highlight-box {{ background: #e8f0fe; border-left: 4px solid #1a73e8;
                      padding: 16px; border-radius: 4px; margin: 16px 0; }}
    .confirmation-number {{ font-size: 28px; font-weight: bold; color: #1a73e8;
                             letter-spacing: 3px; text-align: center; margin: 8px 0; }}
    .footer {{ background: #f8f9fa; padding: 20px; text-align: center;
               font-size: 12px; color: #888; }}
    .route {{ text-align: center; padding: 16px; font-size: 18px; }}
    .route .city {{ font-weight: bold; font-size: 22px; color: #1a73e8; }}
    .arrow {{ color: #999; margin: 0 12px; font-size: 20px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✈ Flight Booking Confirmed!</h1>
      <p>Your journey is booked. Have a great trip!</p>
      <span class="badge">✓ CONFIRMED</span>
    </div>
    <div class="body">

      <div class="highlight-box">
        <div style="text-align:center; color:#666; font-size:13px;">CONFIRMATION NUMBER</div>
        <div class="confirmation-number">{booking.get('confirmation_number', 'N/A')}</div>
        <div style="text-align:center; color:#666; font-size:12px;">PNR: {booking.get('pnr', 'N/A')}</div>
      </div>

      <div class="section">
        <h2>Flight Details</h2>
        <div class="route">
          <span class="city">{booking.get('origin', '')}</span>
          <span class="arrow">→</span>
          <span class="city">{booking.get('destination', '')}</span>
        </div>
        <div class="row">
          <span class="label">Airline</span>
          <span class="value">{booking.get('airline', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Flight Number</span>
          <span class="value">{booking.get('flight_number', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Departure</span>
          <span class="value">{booking.get('departure_datetime', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Arrival</span>
          <span class="value">{booking.get('arrival_datetime', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Class</span>
          <span class="value">{booking.get('seat_class', 'Economy')}</span>
        </div>
        <div class="row">
          <span class="label">Seat(s)</span>
          <span class="value">{seats_str}</span>
        </div>
      </div>

      <div class="section">
        <h2>Passenger Information</h2>
        <div class="row">
          <span class="label">Passenger</span>
          <span class="value">{booking.get('passenger_name', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Email</span>
          <span class="value">{booking.get('passenger_email', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Passengers</span>
          <span class="value">{booking.get('num_passengers', 1)}</span>
        </div>
      </div>

      <div class="section">
        <h2>Price Summary</h2>
        <div class="row">
          <span class="label">Price per person</span>
          <span class="value">${booking.get('price_per_person', 0):.2f}</span>
        </div>
        <div class="row">
          <span class="label">Passengers</span>
          <span class="value">× {booking.get('num_passengers', 1)}</span>
        </div>
        <div class="row" style="font-size:16px; border-top:1px solid #eee; padding-top:8px; margin-top:8px;">
          <span class="label"><strong>Total Paid</strong></span>
          <span class="value" style="color:#1a73e8;">${booking.get('total_price', 0):.2f} {booking.get('currency', 'USD')}</span>
        </div>
      </div>

      <div class="section">
        <h2>What's Included</h2>
        <div class="row">
          <span class="label">Baggage</span>
          <span class="value">{booking.get('baggage_allowance', 'N/A')}</span>
        </div>
        <div class="row">
          <span class="label">Meal</span>
          <span class="value">{meal}</span>
        </div>
        <div class="row">
          <span class="label">Cancellation</span>
          <span class="value">{booking.get('cancellation_policy', 'N/A')}</span>
        </div>
      </div>

    </div>
    <div class="footer">
      <p>This booking was made via FlightAgents AI System</p>
      <p>For support, keep your confirmation number handy: <strong>{booking.get('confirmation_number', '')}</strong></p>
      <p style="margin-top:8px; color:#aaa;">© 2025 FlightAgents. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
"""


@tool
def send_booking_confirmation_email(
    booking: dict,
    recipient_email: str,
) -> dict:
    """Send a flight booking confirmation email to the passenger.

    Args:
        booking: The booking confirmation dictionary from book_flight tool.
        recipient_email: Email address to send the confirmation to.

    Returns:
        Dictionary with send status and details.
    """
    smtp_user = os.getenv("GMAIL_USER")
    smtp_password = os.getenv("GMAIL_APP_PASSWORD")

    if not smtp_user or not smtp_password:
        return {
            "success": False,
            "error": "Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD env vars.",
            "recipient": recipient_email,
        }

    subject = (
        f"Booking Confirmed ✓ — {booking.get('origin', '')} → {booking.get('destination', '')} "
        f"| {booking.get('confirmation_number', '')}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"FlightAgents <{smtp_user}>"
    msg["To"] = recipient_email

    plain_text = (
        f"Flight Booking Confirmation\n"
        f"{'='*40}\n"
        f"Confirmation Number: {booking.get('confirmation_number', 'N/A')}\n"
        f"PNR: {booking.get('pnr', 'N/A')}\n"
        f"Status: {booking.get('status', 'N/A')}\n\n"
        f"Flight: {booking.get('airline', '')} {booking.get('flight_number', '')}\n"
        f"Route: {booking.get('origin', '')} → {booking.get('destination', '')}\n"
        f"Departure: {booking.get('departure_datetime', 'N/A')}\n"
        f"Arrival: {booking.get('arrival_datetime', 'N/A')}\n"
        f"Class: {booking.get('seat_class', 'Economy')}\n"
        f"Seats: {', '.join(booking.get('seats', []))}\n\n"
        f"Passenger: {booking.get('passenger_name', 'N/A')}\n"
        f"Total Price: ${booking.get('total_price', 0):.2f} {booking.get('currency', 'USD')}\n\n"
        f"Thank you for booking with FlightAgents!"
    )

    html_content = _build_html_email(booking)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())

        return {
            "success": True,
            "recipient": recipient_email,
            "subject": subject,
            "confirmation_number": booking.get("confirmation_number"),
            "message": f"Confirmation email successfully sent to {recipient_email}",
        }
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD.",
            "recipient": recipient_email,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}",
            "recipient": recipient_email,
        }
