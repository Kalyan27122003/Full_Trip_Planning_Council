# agents/notifier_agent.py
# This agent is the final step in the travel planning pipeline.
# It handles two tasks:
#   1. Adding the trip to Google Calendar (without sending guest invites)
#   2. Sending one styled HTML email with the itinerary + calendar link embedded

import os
from dotenv import load_dotenv

# Import the Gmail sending function from our custom tool
from tools.gmail_tool import send_itinerary_email

# Import the Google Calendar function and date parser from our custom tool
from tools.calendar_tool import add_trip_to_calendar

# Import the shared state type that flows through the LangGraph pipeline
from graph.state import TripState

# Load environment variables from .env (e.g., Gmail credentials, API keys)
load_dotenv()


def _parse_dates(travel_dates: str):
    """
    Extracts start and end dates from a travel date range string.

    Delegates to parse_travel_dates() in calendar_tool.py.
    Returns (start_date, end_date) as 'YYYY-MM-DD' strings, or (None, None) on failure.
    We discard the duration (third return value) since it's not needed here.
    """
    from tools.calendar_tool import parse_travel_dates
    start, end, _ = parse_travel_dates(travel_dates)  # _ = duration (ignored here)
    return start, end


def _capitalize_destination(destination: str) -> str:
    """
    Converts short city abbreviations or lowercase names into proper display names.

    Examples:
        "vizag" → "Visakhapatnam (Vizag)"
        "hyd"   → "Hyderabad"
        "paris" → "Paris"  (via .title() fallback)

    This ensures the destination looks clean in emails and calendar events.
    """
    # Mapping of common short forms / nicknames to full city names
    abbrevs = {
        "vizag": "Visakhapatnam (Vizag)",
        "hyd":   "Hyderabad",
        "blr":   "Bangalore",
        "chn":   "Chennai",
        "mum":   "Mumbai",
    }
    # Return the mapped name if found; otherwise title-case the input (e.g., "goa" → "Goa")
    return abbrevs.get(destination.lower(), destination.title())


def _parse_emails(email: str) -> list:
    """
    Parses a raw email string into a clean list of valid email addresses.

    Handles:
      - Single address:    "user@example.com"
      - Comma-separated:  "a@x.com, b@y.com"
      - Semicolon-separated: "a@x.com; b@y.com"

    Returns an empty list if the input is empty or contains no valid addresses.
    Basic validation: checks that each entry contains "@".
    """
    if not email:
        return []
    # Replace semicolons with commas, split, strip whitespace, and filter valid emails
    return [e.strip() for e in email.replace(";", ",").split(",") if "@" in e.strip()]


def notifier_agent(state: TripState) -> TripState:
    """
    LangGraph agent node that sends notifications after a trip plan is generated.

    Reads from TripState:
      - itinerary:              The full AI-generated trip plan (markdown text)
      - email:                  Recipient email address(es)
      - destination_preference: Raw destination input (e.g., "vizag")
      - travel_dates:           Date range string (e.g., "5 Apr to 8 Apr 2026")
      - travelers:              Number of travelers
      - budget_inr:             Total budget in Indian Rupees
      - duration_days:          Trip duration in days

    Writes back to TripState:
      - notification_status: A summary string of what was sent/skipped

    Flow:
      Step 1 → Add event to Google Calendar (no guest invites)
      Step 2 → Send one HTML email with the calendar link embedded
    """
    print("📧  Notifier Agent running...")

    # ── Extract required fields from the shared pipeline state ──────────
    itinerary    = state.get("itinerary", "No itinerary generated.")
    raw_email    = state.get("email", "")
    destination  = _capitalize_destination(state.get("destination_preference", "Your Destination"))
    travel_dates = state.get("travel_dates", "")
    travelers    = str(state.get("travelers", 1))
    budget       = f"Rs.{state.get('budget_inr', 0):,}"  # Format as "Rs.50,000"
    duration     = state.get("duration_days", 0)

    # Parse the raw email string into a clean list of recipients
    all_emails = _parse_emails(raw_email)

    # Accumulate status messages for each action (calendar, email)
    results = []

    # ── STEP 1: Add Trip to Google Calendar ─────────────────────────────
    # We add the calendar event FIRST so we can extract its link
    # and embed it in the email sent in Step 2.
    # Important: guest_emails=[] ensures Google doesn't send a separate
    # calendar invite email to recipients — we handle notification ourselves.
    calendar_link = None  # Will be populated if calendar event is created successfully

    start_date, end_date = _parse_dates(travel_dates)

    if start_date and end_date:
        # Create the calendar event with the itinerary as the event description
        calendar_result = add_trip_to_calendar(
            trip_name    = f"{duration}-Day Trip",
            destination  = destination,
            start_date   = start_date,
            end_date     = end_date,
            description  = itinerary[:1800],  # Truncated to stay within API limits
            guest_emails = [],                # No guest invites — email is handled separately
        )
        results.append(f"📅 Calendar: {calendar_result}")

        # Extract the Google Calendar event URL from the result string
        # The URL starts with "https://www.google.com/calendar"
        for word in calendar_result.split():
            if word.startswith("https://www.google.com/calendar"):
                calendar_link = word
                break  # Stop as soon as we find the first matching URL
    else:
        # Dates couldn't be parsed — skip calendar and guide the user on correct format
        results.append("📅 Calendar: Skipped — use format '5 Apr 2026 to 8 Apr 2026'")

    # ── STEP 2: Send ONE HTML Email with Calendar Link Embedded ─────────
    # We send a single email to all recipients (first in To:, rest in BCC:).
    # The calendar link from Step 1 is embedded as a button inside the email.
    if all_emails:
        subject = f"✈️ Your Trip Plan to {destination} | {travel_dates}"

        gmail_result = send_itinerary_email(
            to_email      = all_emails,
            subject       = subject,
            body          = itinerary,        # Full markdown itinerary
            destination   = destination,
            travel_dates  = travel_dates,
            travelers     = travelers,
            budget        = budget,
            calendar_link = calendar_link,    # Embedded as a button in the HTML email
        )

        # Log which addresses received the email
        recipients_str = ", ".join(all_emails)
        results.append(f"📧 Gmail → {recipients_str}: {gmail_result}")
    else:
        # No email address was provided — skip silently
        results.append("📧 Gmail: Skipped (no email provided)")

    # ── Return Updated State ─────────────────────────────────────────────
    # Merge notification results back into the state so downstream nodes
    # (or the final output) can see what happened.
    return {**state, "notification_status": "\n".join(results)}