# tools/calendar_tool.py
# This module handles Google Calendar integration for adding travel trips as events.

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the .env file (e.g., API keys, secrets)
load_dotenv()

# Path to the OAuth credentials file downloaded from Google Cloud Console
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"

# Path to the token file that stores the user's access & refresh tokens after login
TOKEN_FILE = Path(__file__).parent.parent / "token.json"

# Scopes define what permissions we're requesting from Google (full calendar access)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    """
    Authenticates with Google Calendar API and returns a usable service object.
    
    - If token.json exists, it reuses the saved credentials.
    - If the token is expired, it automatically refreshes it.
    - If no token exists, it opens a browser login flow to get one.
    - Returns: (service_object, None) on success, or (None, error_message) on failure.
    """
    try:
        # Import Google auth libraries (only inside function to catch ImportError gracefully)
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        # Check if a saved token already exists from a previous login
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # If no valid credentials found, we need to get or refresh them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Token expired but refresh token exists — silently refresh it
                creds.refresh(Request())
            else:
                # No token at all — start the OAuth browser login flow
                if not CREDENTIALS_FILE.exists():
                    return None, "Google Calendar not configured on this server."
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)  # Opens browser for user to log in

            # Save the new/refreshed token to disk for future use
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        # Build and return the Google Calendar API service client
        return build("calendar", "v3", credentials=creds), None

    except ImportError as e:
        # Required Google libraries are not installed
        return None, f"Missing package: {e}"
    except Exception as e:
        # Any other unexpected error
        return None, str(e)


def _parse_date_flexible(date_str: str) -> str:
    """
    Converts various date string formats into a standard 'YYYY-MM-DD' format.

    Handles formats like:
      - '20 june 2026'
      - '20june2026'  (no spaces)
      - '20-06-2026'
      - '2026-06-20'
      - '20/06/2026'
      - '20 jun 2026'

    Returns the date as 'YYYY-MM-DD', or None if parsing fails.
    """
    import re
    from datetime import datetime

    date_str = date_str.strip()

    # Fix: Add space between a letter and a 4-digit year (e.g., "june2026" → "june 2026")
    date_str = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', date_str)

    # Fix: Add space between a number and a letter (e.g., "20june" → "20 june")
    date_str = re.sub(r'(\d{1,2})([a-zA-Z])', r'\1 \2', date_str)

    # List of date formats to try, in order of preference
    formats = [
        "%d %B %Y", "%d %b %Y",    # e.g., "20 June 2026", "20 Jun 2026"
        "%d %B%Y", "%d %b%Y",      # post-normalization variants
        "%Y-%m-%d",                 # e.g., "2026-06-20" (ISO format)
        "%d-%m-%Y", "%d/%m/%Y",    # e.g., "20-06-2026", "20/06/2026"
        "%B %d %Y", "%b %d %Y",    # e.g., "June 20 2026"
    ]

    # Try each format until one succeeds
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue  # If format doesn't match, try the next one

    # Return None if no format worked
    return None


def parse_travel_dates(travel_dates: str):
    """
    Parses a travel date range string like '19 april to 22 april'.

    Returns a tuple: (start_date, end_date, duration_days)
    - start_date / end_date: strings in 'YYYY-MM-DD' format
    - duration_days: total calendar days including both start and end
                     e.g., April 19 to April 22 = 4 days (19, 20, 21, 22)

    Formula used: duration = (end - start).days + 1
    """
    from datetime import datetime

    raw = travel_dates.strip()
    start_raw, end_raw = None, None

    # Try common separators to split the date range into start and end
    for sep in [" to ", " - ", " – ", "to"]:
        if sep in raw:
            parts = raw.split(sep, 1)  # Split only on first occurrence
            start_raw = parts[0].strip()
            end_raw   = parts[1].strip()
            break

    # If we couldn't split the range, return defaults
    if not start_raw or not end_raw:
        return None, None, 1

    # Parse both dates using our flexible parser
    start = _parse_date_flexible(start_raw)
    end   = _parse_date_flexible(end_raw)

    if start and end:
        try:
            d1 = datetime.strptime(start, "%Y-%m-%d")
            d2 = datetime.strptime(end,   "%Y-%m-%d")

            # +1 ensures both the departure and return days are counted
            duration = max(1, (d2 - d1).days + 1)
            return start, end, duration
        except Exception:
            pass  # Fall through to default if something goes wrong

    # Return parsed dates with a default duration of 1 day if calculation fails
    return start, end, 1


def add_trip_to_calendar(
    trip_name: str,
    destination: str,
    start_date: str,   # Format: 'YYYY-MM-DD'
    end_date: str,     # Format: 'YYYY-MM-DD'
    description: str,
    guest_emails: list = None,  # Optional list of email addresses to invite
) -> str:
    """
    Creates a travel event on the user's Google Calendar.

    - Adds email and popup reminders (3 days and 1 day before).
    - Optionally invites guests via their email addresses.
    - Returns a success message with the event link, or an error message.
    """

    # Authenticate and get the Calendar API service
    service, err = _get_service()
    if err:
        return f"⚠️ Calendar: {err}"

    try:
        # Build the list of attendees (guests) from valid email addresses
        attendees = []
        if guest_emails:
            for email in guest_emails:
                email = email.strip()
                if email and "@" in email:  # Basic email validation
                    attendees.append({"email": email})

        # Construct the Google Calendar event object
        event = {
            "summary":     f"Trip to {destination} — {trip_name}",  # Event title
            "description": description[:1800],  # Truncate to stay within API limits
            "start": {"date": start_date, "timeZone": "Asia/Kolkata"},  # All-day event start
            "end":   {"date": end_date,   "timeZone": "Asia/Kolkata"},  # All-day event end
            "attendees": attendees,
            "guestsCanModify": False,  # Guests can view but not edit the event
            "reminders": {
                "useDefault": False,  # Override default reminders with custom ones
                "overrides": [
                    {"method": "email",  "minutes": 24 * 60 * 3},  # Email 3 days before
                    {"method": "popup",  "minutes": 24 * 60},       # Popup 1 day before
                ],
            },
        }

        # Insert the event into the user's primary Google Calendar
        created = service.events().insert(
            calendarId  = "primary",   # Use the user's main calendar
            body        = event,
            sendUpdates = "none",      # Don't send email notifications to guests
        ).execute()

        # Get the link to the created event
        link = created.get("htmlLink", "")
        return f"✅ Trip added to Google Calendar!\n{link}"

    except Exception as e:
        return f"❌ Calendar error: {str(e)}"


# ──────────────────────────────────────────────
# Run this file directly to test OAuth setup:
# python tools/calendar_tool.py
# It will open a browser to log in and save token.json
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Google Calendar OAuth setup...")
    service, err = _get_service()
    if err:
        print(f"Error: {err}")
    else:
        print("✅ Google Calendar authenticated! token.json saved.")