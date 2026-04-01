# tools/calendar_tool.py
"""
Google Calendar integration via OAuth2.
First-time setup:
  1. Create a Google Cloud project
  2. Enable the Google Calendar API
  3. Download credentials.json → place in project root
  4. Run this file directly once to authenticate and generate token.json
"""
import os
import json
import datetime
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
                    return None, "credentials.json not found. See tools/calendar_tool.py for setup."
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        return build("calendar", "v3", credentials=creds), None
    except Exception as e:
        return None, str(e)

def add_trip_to_calendar(
    trip_name: str,
    destination: str,
    start_date: str,
    end_date: str,
    description: str,
) -> str:
    """
    Add a trip event to Google Calendar.
    start_date / end_date format: 'YYYY-MM-DD'
    """
    service, err = _get_service()
    if err:
        return f"⚠️ Calendar setup needed: {err}"

    try:
        event = {
            "summary": f"✈️ Trip to {destination} — {trip_name}",
            "description": description[:2000],   # Calendar limit
            "start": {"date": start_date, "timeZone": "Asia/Kolkata"},
            "end":   {"date": end_date,   "timeZone": "Asia/Kolkata"},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",  "minutes": 24 * 60 * 3},   # 3 days before
                    {"method": "popup",  "minutes": 24 * 60},        # 1 day before
                ],
            },
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        link = created.get("htmlLink", "")
        return f"✅ Trip added to Google Calendar!\n🔗 {link}"
    except Exception as e:
        return f"❌ Calendar error: {str(e)}"
