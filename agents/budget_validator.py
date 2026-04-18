# agents/budget_validator.py
# ─────────────────────────────────────────────────────────────────────────────
# BUDGET VALIDATOR — Pre-Planning Budget Feasibility Check
#
# This is the FIRST agent in the pipeline. Its job is to check whether the
# user's budget is realistically enough for the trip BEFORE we run all the
# expensive LLM calls.
#
# Why run this first?
#   - Saves time and API credits — no point running 8 agents if budget is ₹1000
#     for a 7-day trip to Japan.
#   - Gives the user clear feedback on how much MORE money they need.
#
# Two main functions:
#   1. estimate_minimum_budget() — calculates the minimum viable budget
#   2. validate_budget()         — compares user's budget vs minimum, returns pass/fail
#
# Works globally — handles both domestic India trips and international trips.
# ─────────────────────────────────────────────────────────────────────────────
from agents.currency_helper import (
    detect_country_and_currency,
    get_daily_min_inr,      # Minimum daily cost per person for a country
    get_intl_flight_inr,    # Round-trip international flight cost from India
)


# ─────────────────────────────────────────────────────────────────────────────
# INDIA-SPECIFIC DESTINATION CATEGORIES
# India has many different types of destinations with very different costs.
# e.g. Ladakh is expensive (remote, limited food/stay options),
#      Guntur is cheap (small city, lots of local options).
# We categorise Indian destinations to apply the right minimum costs.
# ─────────────────────────────────────────────────────────────────────────────
INDIA_CATEGORIES = {
    "ultra_remote": ["ladakh", "leh", "andaman", "lakshadweep", "spiti", "zanskar",
                     "arunachal", "tawang", "mechuka", "dzukou"],
    "hill_station": ["manali", "shimla", "mussoorie", "darjeeling", "ooty", "kodaikanal",
                     "coorg", "munnar", "shillong", "gangtok", "nainital", "mcleod",
                     "dalhousie", "chikmagalur", "mahabaleshwar", "lonavala"],
    "beach":        ["goa", "pondicherry", "varkala", "kovalam", "alleppey", "alappuzha",
                     "palolem", "havelock", "gokarna", "murudeshwar", "tarkarli", "puri"],
    "heritage":     ["jaipur", "jodhpur", "jaisalmer", "udaipur", "agra", "varanasi",
                     "hampi", "khajuraho", "mysore", "madurai", "orchha", "pushkar"],
    "spiritual":    ["rishikesh", "haridwar", "tirupati", "shirdi", "amritsar",
                     "vrindavan", "mathura", "bodh gaya", "ujjain", "dwarka"],
    "wildlife":     ["ranthambore", "corbett", "bandipur", "kaziranga", "kanha",
                     "tadoba", "nagarhole", "kabini", "wayanad", "periyar"],
    "northeast":    ["meghalaya", "assam", "arunachal", "manipur", "nagaland", "sikkim"],
    "city":         ["delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
                     "kolkata", "pune", "kochi", "guntur", "vijayawada", "vizag",
                     "kakinada", "visakhapatnam", "nellore", "tirupati", "warangal"],
}

# Minimum daily cost per person in INR for each India category
INDIA_DAILY_MIN_INR = {
    "ultra_remote": 3500,   # Ladakh etc. — expensive due to remoteness
    "hill_station": 2000,
    "beach":        2200,
    "heritage":     1800,
    "spiritual":    1400,   # Cheaper — lots of free temples, dharmashala stays
    "wildlife":     2800,   # Wildlife resorts are pricey
    "northeast":    2200,
    "city":         1200,   # Cheapest — lots of budget options in cities
    "unknown":      1000,
}

# Minimum round-trip transport cost per person in INR for India trips
# (from a typical Indian city — not exact, just for validation)
INDIA_TRANSPORT_MIN_INR = {
    "ultra_remote": 5000,   # Flights to Leh, ferries to Andaman
    "hill_station": 2000,
    "beach":        2000,
    "heritage":     1500,
    "spiritual":    1500,
    "wildlife":     2000,
    "northeast":    3500,
    "city":         400,    # Just a bus/train ticket
    "unknown":      300,
}


def get_india_category(destination: str) -> str:
    """
    Classify an Indian destination into one of our categories.
    Checks if the destination name appears in (or contains) any keyword in the list.
    Returns "unknown" if no match found.
    """
    dest_lower = destination.lower()
    for cat, places in INDIA_CATEGORIES.items():
        for place in places:
            if place in dest_lower or dest_lower in place:
                return cat
    return "unknown"


def estimate_minimum_budget(destination: str, duration_days: int, travelers: int) -> dict:
    """
    Calculate the minimum realistic budget for a trip.

    Logic:
      1. Detect the country from the destination name.
      2. For India: look up category-specific daily + transport costs.
         For international: use REGIONAL_DAILY_MIN_INR + INTL_FLIGHT_FROM_INDIA_INR.
      3. Calculate: transport_total + daily_total + 10% buffer = minimum.

    Returns a dict with:
      - minimum: the minimum INR amount needed
      - category: what type of destination it is
      - breakdown: itemised cost breakdown (for display in UI)
    """
    currency_info = detect_country_and_currency(destination)
    country = currency_info["country"]

    if country in ("India", "Unknown"):
        # Use India-specific category costs
        cat = get_india_category(destination)
        daily_min_inr    = INDIA_DAILY_MIN_INR.get(cat, 1000)
        transport_pp_inr = INDIA_TRANSPORT_MIN_INR.get(cat, 400)
        transport_total  = transport_pp_inr * 2 * travelers  # ×2 for round trip
        category_label   = f"India — {cat}"
    else:
        # International trip — use country-level daily cost + international flight
        daily_min_inr   = get_daily_min_inr(country)
        flight_inr      = get_intl_flight_inr(country)
        transport_total = flight_inr * travelers  # Round-trip flight per person
        category_label  = country

    daily_total = daily_min_inr * duration_days * travelers  # Total daily expenses
    subtotal    = transport_total + daily_total
    buffer      = int(subtotal * 0.10)   # 10% emergency buffer
    minimum     = subtotal + buffer

    return {
        "minimum":       minimum,
        "category":      category_label,
        "country":       country,
        "currency_info": currency_info,
        "breakdown": {
            f"Transport (round trip × {travelers} person(s))": f"₹{transport_total:,}",
            f"Daily expenses × {duration_days} days × {travelers} person(s)":
                f"₹{daily_total:,}  (≈ ₹{daily_min_inr:,}/person/day)",
            "10% emergency buffer": f"₹{buffer:,}",
        },
        "note": "Rough minimum estimates. Actual costs vary by season and travel style.",
    }


def validate_budget(destination: str, budget_inr: int,
                    duration_days: int, travelers: int) -> dict:
    """
    Main validation function — used by both the LangGraph node and the Streamlit UI.

    Compares the user's budget_inr against the estimated minimum.

    Returns:
      {"valid": True, "currency_info": {...}}                        → budget is OK
      {"valid": False, "message": "detailed error + tips", ...}      → budget is too low

    The error message includes:
      - How much they need vs how much they have
      - Itemised cost breakdown
      - Tips: increase budget OR reduce duration
    """
    data    = estimate_minimum_budget(destination, duration_days, travelers)
    minimum = data["minimum"]

    if budget_inr >= minimum:
        # Budget is sufficient — just return success + currency info
        return {"valid": True, "currency_info": data["currency_info"]}

    # Budget is too low — build a detailed, helpful error message
    shortfall = minimum - budget_inr
    breakdown_str = "\n".join([f"  • {k}: {v}" for k, v in data["breakdown"].items()])
    # Calculate how many days the user CAN afford within their budget
    alt_days = max(1, budget_inr // max(minimum // max(duration_days, 1), 1))

    return {
        "valid": False,
        "message": f"""⚠️ Budget May Be Low for {destination}

Your budget      : ₹{budget_inr:,}
Estimated minimum: ₹{minimum:,}  ({travelers} traveler(s), {duration_days} days)
Destination type : {data['category']}

Rough cost breakdown:
{breakdown_str}

Note: {data['note']}

💡 Options:
  1. Increase budget to at least ₹{minimum:,}
  2. Reduce duration to ~{alt_days} day(s) within ₹{budget_inr:,}
  3. Travel in off-season for lower prices""",
        "minimum":       minimum,
        "breakdown":     data["breakdown"],
        "currency_info": data["currency_info"],
    }


def calculate_minimum_budget(destination: str, duration_days: int, travelers: int) -> dict:
    """
    Public alias for estimate_minimum_budget().
    Called directly from app.py to show the budget preview card in the Streamlit UI
    (separate from the LangGraph pipeline — just for live UI feedback).
    """
    return estimate_minimum_budget(destination, duration_days, travelers)