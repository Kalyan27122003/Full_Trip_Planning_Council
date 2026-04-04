# tools/calendar_tool.py
"""
Google Calendar integration via OAuth2.
Adds trip event to your calendar AND sends invite to friend's email.

First-time setup:
  1. Create Google Cloud project
  2. Enable Google Calendar API
  3. Download credentials.json → place in project root
  4. Run: python tools/calendar_tool.py
     This opens browser, authenticate → generates token.json
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
TOKEN_FILE       = Path(__file__).parent.parent / "token.json"
SCOPES           = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    """Authenticate and return Google Calendar service."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    return None, (
                        "credentials.json not found. "
                        "See tools/calendar_tool.py for setup instructions."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        return build("calendar", "v3", credentials=creds), None

    except ImportError as e:
        return None, f"Missing package: {e}. Run: uv pip install google-auth-oauthlib google-api-python-client"
    except Exception as e:
        return None, str(e)


def add_trip_to_calendar(
    trip_name: str,
    destination: str,
    start_date: str,
    end_date: str,
    description: str,
    guest_emails: list = None,       # ← NEW: list of friend emails to invite
) -> str:
    """
    Add trip to YOUR Google Calendar.
    Optionally invite friends as guests — they receive a calendar invite email.

    Args:
        trip_name:    e.g. "5-Day Trip"
        destination:  e.g. "Vizag"
        start_date:   "YYYY-MM-DD"
        end_date:     "YYYY-MM-DD"
        description:  Itinerary text (max 1800 chars)
        guest_emails: List of friend emails to send calendar invite
                      e.g. ["friend@gmail.com", "another@gmail.com"]
    """
    service, err = _get_service()
    if err:
        return f"⚠️ Calendar setup needed: {err}"

    try:
        # Build attendees list (guests)
        attendees = []
        if guest_emails:
            for email in guest_emails:
                email = email.strip()
                if email and "@" in email:
                    attendees.append({"email": email})

        event = {
            "summary": f"✈️ Trip to {destination} — {trip_name}",
            "description": description[:1800],
            "start": {"date": start_date, "timeZone": "Asia/Kolkata"},
            "end":   {"date": end_date,   "timeZone": "Asia/Kolkata"},
            "attendees": attendees,        # ← guests get calendar invite email
            "guestsCanSeeOtherGuests": True,
            "guestsCanModify": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",  "minutes": 24 * 60 * 3},  # 3 days before
                    {"method": "popup",  "minutes": 24 * 60},       # 1 day before
                ],
            },
        }

        # sendUpdates="all" → sends invite email to all attendees
        created = service.events().insert(
            calendarId   = "primary",
            body         = event,
            sendUpdates  = "all",          # ← This sends the invite email to guests
        ).execute()

        link = created.get("htmlLink", "")

        if attendees:
            guest_list = ", ".join([a["email"] for a in attendees])
            return (
                f"✅ Trip added to Google Calendar!\n"
                f"📅 Calendar link: {link}\n"
                f"📨 Calendar invite sent to: {guest_list}"
            )
        else:
            return f"✅ Trip added to Google Calendar!\n📅 {link}"

    except Exception as e:
        return f"❌ Calendar error: {str(e)}"


# ── One-time OAuth setup ──────────────────────────────────────
if __name__ == "__main__":
    print("🔐 Starting Google Calendar OAuth setup...")
    service, err = _get_service()
    if err:
        print(f"❌ Error: {err}")
    else:
        print("✅ Google Calendar authenticated successfully!")
        print(f"   token.json saved at: {TOKEN_FILE}")
        print("   You can now use calendar features in the app.")