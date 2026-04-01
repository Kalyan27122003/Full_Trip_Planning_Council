# agents/notifier_agent.py
import os
from dotenv import load_dotenv
from tools.gmail_tool import send_itinerary_email
from tools.calendar_tool import add_trip_to_calendar
from graph.state import TripState

load_dotenv()

def _parse_dates(travel_dates: str):
    import re
    from datetime import datetime
    raw = travel_dates.strip()
    for sep in [" to ", " - ", " – "]:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep, 1)]
            break
    else:
        return None, None
    formats = ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    start, end = None, None
    for fmt in formats:
        try:
            start = datetime.strptime(parts[0], fmt).strftime("%Y-%m-%d")
            end   = datetime.strptime(parts[1], fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            continue
    return start, end


def notifier_agent(state: TripState) -> TripState:
    """Sends itinerary via Gmail and adds trip to Google Calendar."""
    print("📧  Notifier Agent running...")

    itinerary    = state.get("itinerary", "No itinerary generated.")
    email        = state.get("email", "")
    destination  = state.get("destination_preference", "Your Destination")
    travel_dates = state.get("travel_dates", "")
    travelers    = str(state.get("travelers", 2))
    budget       = f"Rs.{state.get('budget_inr', 0):,}"
    duration     = state.get("duration_days", 0)
    results      = []

    # ── 1. Send Gmail ─────────────────────────────────────────
    if email:
        subject = f"✈️ Your Trip Plan to {destination} | {travel_dates}"
        gmail_result = send_itinerary_email(
            to_email     = email,
            subject      = subject,
            body         = itinerary,
            destination  = destination,
            travel_dates = travel_dates,
            travelers    = travelers,
            budget       = budget,
        )
        results.append(f"📧 Gmail: {gmail_result}")
    else:
        results.append("📧 Gmail: Skipped (no email provided)")

    # ── 2. Add to Google Calendar ─────────────────────────────
    start_date, end_date = _parse_dates(travel_dates)
    if start_date and end_date:
        calendar_result = add_trip_to_calendar(
            trip_name   = f"{duration}-Day Trip",
            destination = destination,
            start_date  = start_date,
            end_date    = end_date,
            description = itinerary[:1800],
        )
        results.append(f"📅 Calendar: {calendar_result}")
    else:
        results.append(
            "📅 Calendar: Skipped — use format '1 Apr 2026 to 10 Apr 2026'"
        )

    return {**state, "notification_status": "\n".join(results)}