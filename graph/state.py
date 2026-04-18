# graph/state.py
# ─────────────────────────────────────────────────────────────────────────────
# STATE — Shared Data Container for All Agents
#
# In LangGraph, every agent reads from and writes to a single shared "state"
# object. Think of it like a shared whiteboard that every agent can read and
# update. This file defines what that whiteboard looks like (its schema).
#
# Why TypedDict?
#   - Gives us type hints so we know exactly what keys exist and their types.
#   - LangGraph requires the state to be a TypedDict (or Pydantic model).
# ─────────────────────────────────────────────────────────────────────────────
from typing import TypedDict, Optional


class TripState(TypedDict):
    # ── User Inputs ──────────────────────────────────────────────────────────
    # These come directly from the Streamlit form filled by the user.

    user_query: str               # Full sentence like "Plan a 5-day trip to Goa"
    origin: str                   # Where the user is travelling FROM (e.g. "Hyderabad")
    destination_preference: str   # Where the user wants to GO (e.g. "Goa", "Paris")
    travel_dates: str             # Raw string like "15 Dec 2025 to 20 Dec 2025"
    duration_days: int            # Auto-calculated from travel_dates (e.g. 6 days)
    budget_inr: int               # User's total budget, always stored in INR internally
    travelers: int                # Number of people travelling
    interests: str                # Comma-separated interests like "Beach, Food, Culture"
    specific_places: str          # Optional: specific places user wants to visit
    email: str                    # Email(s) to send the final itinerary to

    # ── Auto-detected Destination Info ───────────────────────────────────────
    # These are filled by the destination_agent after detecting the country
    # from the destination name using currency_helper.py

    country: str          # e.g. "Japan", "India", "France"
    currency_code: str    # e.g. "JPY", "INR", "EUR"
    currency_symbol: str  # e.g. "¥", "₹", "€"
    inr_rate: float       # Exchange rate: 1 local currency unit = X INR
                          # e.g. for Japan: 1 JPY = 0.56 INR → inr_rate = 0.56

    # ── Agent Outputs ─────────────────────────────────────────────────────────
    # Each agent writes its result into one of these fields.
    # Later agents (like itinerary_agent) READ these to build the final plan.

    destination_report: str    # From destination_agent — top attractions, how to reach
    budget_report: str         # From budget_agent — ₹ breakdown across categories
    hotel_report: str          # From hotel_agent — recommended hotels with prices
    food_culture_report: str   # From food_culture_agent — local food + cultural tips
    transport_report: str      # From transport_agent — how to travel, distance, cost
    weather_report: str        # From weather_agent — forecast + packing tips
    safety_report: str         # From safety_agent — safety rating, scams, emergency numbers
    itinerary: str             # From itinerary_agent — the final day-by-day plan

    # ── Control Flow ──────────────────────────────────────────────────────────
    # These fields control the flow of the pipeline.

    human_approved: bool       # True once the user clicks "Approve" in the UI
    notification_status: str   # Result message after sending Gmail + Calendar
    error: Optional[str]       # Set by budget_validator if budget is too low → stops pipeline