# agents/notifier_agent.py
import os
from dotenv import load_dotenv
from tools.gmail_tool import send_itinerary_email
from tools.calendar_tool import add_trip_to_calendar
from graph.state import TripState

load_dotenv()

def _parse_dates(travel_dates: str):
    from datetime import datetime
    raw = travel_dates.strip()
    for sep in [" to ", " - ", " – "]:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep, 1)]
            break
    else:
        return None, None
    formats = ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y",
               "%d-%m-%Y", "%d %b %y", "%d %B %y"]
    for fmt in formats:
        try:
            start = datetime.strptime(parts[0], fmt).strftime("%Y-%m-%d")
            end   = datetime.strptime(parts[1], fmt).strftime("%Y-%m-%d")
            return start, end
        except ValueError:
            continue
    return None, None

def _capitalize_destination(destination: str) -> str:
    abbrevs = {
        "vizag": "Visakhapatnam (Vizag)",
        "hyd":   "Hyderabad",
        "blr":   "Bangalore",
        "chn":   "Chennai",
        "mum":   "Mumbai",
    }
    return abbrevs.get(destination.lower(), destination.title())

def _parse_emails(email: str) -> list:
    if not email:
        return []
    return [e.strip() for e in email.replace(";", ",").split(",") if "@" in e.strip()]


def notifier_agent(state: TripState) -> TripState:
    print("📧  Notifier Agent running...")

    itinerary    = state.get("itinerary", "No itinerary generated.")
    raw_email    = state.get("email", "")
    destination  = _capitalize_destination(state.get("destination_preference", "Your Destination"))
    travel_dates = state.get("travel_dates", "")
    travelers    = str(state.get("travelers", 1))
    budget       = f"Rs.{state.get('budget_inr', 0):,}"
    duration     = state.get("duration_days", 0)

    all_emails = _parse_emails(raw_email)
    results    = []

    # ── Step 1: Add to Google Calendar (NO guest invites) ─────
    # Get the calendar link first — we embed it in the email
    calendar_link = None
    start_date, end_date = _parse_dates(travel_dates)
    if start_date and end_date:
        calendar_result = add_trip_to_calendar(
            trip_name    = f"{duration}-Day Trip",
            destination  = destination,
            start_date   = start_date,
            end_date     = end_date,
            description  = itinerary[:1800],
            guest_emails = [],   # ← NO guest invites = no second calendar email
        )
        results.append(f"📅 Calendar: {calendar_result}")
        # Extract link from result
        for word in calendar_result.split():
            if word.startswith("https://www.google.com/calendar"):
                calendar_link = word
                break
    else:
        results.append("📅 Calendar: Skipped — use format '5 Apr 2026 to 8 Apr 2026'")

    # ── Step 2: Send ONE email with calendar link embedded ────
    if all_emails:
        subject = f"✈️ Your Trip Plan to {destination} | {travel_dates}"
        gmail_result = send_itinerary_email(
            to_email      = all_emails,
            subject       = subject,
            body          = itinerary,
            destination   = destination,
            travel_dates  = travel_dates,
            travelers     = travelers,
            budget        = budget,
            calendar_link = calendar_link,   # ← embed in email
        )
        recipients_str = ", ".join(all_emails)
        results.append(f"📧 Gmail → {recipients_str}: {gmail_result}")
    else:
        results.append("📧 Gmail: Skipped (no email provided)")

    return {**state, "notification_status": "\n".join(results)}