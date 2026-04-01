# graph/state.py
from typing import TypedDict, Optional

class TripState(TypedDict):
    # ── User Inputs ──────────────────────────────────────────
    user_query: str
    origin: str
    destination_preference: str
    travel_dates: str
    duration_days: int
    budget_inr: int
    travelers: int
    interests: str
    email: str

    # ── Agent Outputs ────────────────────────────────────────
    destination_report: str
    budget_report: str
    hotel_report: str
    food_culture_report: str
    transport_report: str
    weather_report: str
    safety_report: str
    itinerary: str

    # ── Control Flow ─────────────────────────────────────────
    human_approved: bool
    notification_status: str
    error: Optional[str]
