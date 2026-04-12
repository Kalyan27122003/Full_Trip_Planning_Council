# tools/calendar_tool.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
TOKEN_FILE       = Path(__file__).parent.parent / "token.json"
SCOPES           = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
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
                    return None, "Google Calendar not configured on this server."
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds), None
    except ImportError as e:
        return None, f"Missing package: {e}"
    except Exception as e:
        return None, str(e)


def _parse_date_flexible(date_str: str) -> str:
    """
    Parse many date formats into YYYY-MM-DD.
    Handles: '20 june2026', '20 June 2026', '20-06-2026',
             '2026-06-20', '20/06/2026', '20 jun 2026'
    """
    import re
    from datetime import datetime

    date_str = date_str.strip()

    # Normalize: insert space before year if missing ("june2026" → "june 2026")
    date_str = re.sub(r'([a-zA-Z])(\d{4})', r'\1 \2', date_str)
    # Normalize: insert space between day and month if missing ("20june" → "20 june")
    date_str = re.sub(r'(\d{1,2})([a-zA-Z])', r'\1 \2', date_str)

    formats = [
        "%d %B %Y", "%d %b %Y",     # 20 June 2026, 20 Jun 2026
        "%d %B%Y", "%d %b%Y",       # after normalization
        "%Y-%m-%d",                  # 2026-06-20
        "%d-%m-%Y", "%d/%m/%Y",     # 20-06-2026, 20/06/2026
        "%B %d %Y", "%b %d %Y",     # June 20 2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_travel_dates(travel_dates: str):
    """Parse 'start to end' travel dates. Returns (start_str, end_str, duration_days)."""
    from datetime import datetime

    raw = travel_dates.strip()
    start_raw, end_raw = None, None
    for sep in [" to ", " - ", " – ", "to"]:
        if sep in raw:
            parts = raw.split(sep, 1)
            start_raw = parts[0].strip()
            end_raw   = parts[1].strip()
            break

    if not start_raw or not end_raw:
        return None, None, 1

    start = _parse_date_flexible(start_raw)
    end   = _parse_date_flexible(end_raw)

    if start and end:
        try:
            d1 = datetime.strptime(start, "%Y-%m-%d")
            d2 = datetime.strptime(end,   "%Y-%m-%d")
            duration = max(1, (d2 - d1).days)
            return start, end, duration
        except Exception:
            pass
    return start, end, 1


def add_trip_to_calendar(
    trip_name: str,
    destination: str,
    start_date: str,
    end_date: str,
    description: str,
    guest_emails: list = None,
) -> str:
    service, err = _get_service()
    if err:
        return f"⚠️ Calendar: {err}"

    try:
        attendees = []
        if guest_emails:
            for email in guest_emails:
                email = email.strip()
                if email and "@" in email:
                    attendees.append({"email": email})

        event = {
            "summary":     f"Trip to {destination} — {trip_name}",
            "description": description[:1800],
            "start": {"date": start_date, "timeZone": "Asia/Kolkata"},
            "end":   {"date": end_date,   "timeZone": "Asia/Kolkata"},
            "attendees": attendees,
            "guestsCanModify": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",  "minutes": 24 * 60 * 3},
                    {"method": "popup",  "minutes": 24 * 60},
                ],
            },
        }

        created = service.events().insert(
            calendarId  = "primary",
            body        = event,
            sendUpdates = "none",
        ).execute()

        link = created.get("htmlLink", "")
        return f"✅ Trip added to Google Calendar!\n{link}"
    except Exception as e:
        return f"❌ Calendar error: {str(e)}"


if __name__ == "__main__":
    print("Starting Google Calendar OAuth setup...")
    service, err = _get_service()
    if err:
        print(f"Error: {err}")
    else:
        print("✅ Google Calendar authenticated! token.json saved.")