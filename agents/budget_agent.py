# agents/budget_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# BUDGET AGENT — Intelligent Budget Breakdown Across All Categories
#
# Takes the user's total budget (in INR) and splits it into:
#   Transport / Accommodation / Food / Activities / Local Transport /
#   Shopping / Emergency Buffer
#
# The split uses percentage-based allocation + distance logic:
#   - Transport cost depends on actual km distance (from transport_report or KNOWN_DISTANCES)
#   - For international trips: uses flight cost lookup from currency_helper
#   - Everything else is split proportionally from what's left after transport
#
# Also converts amounts to local currency (e.g. JPY, EUR) for international trips.
#
# Runs: 5th in the pipeline
# ─────────────────────────────────────────────────────────────────────────────
import re
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import (
    detect_country_and_currency, get_booking_platforms, get_intl_flight_inr
)
from graph.state import TripState


# ─────────────────────────────────────────────────────────────────────────────
# KNOWN DISTANCES TABLE
# Hardcoded km distances between common Indian city pairs and international routes.
# Used when the transport_agent's report doesn't contain a clear distance.
# Using frozenset so order doesn't matter: (A,B) == (B,A)
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_DISTANCES = {
    frozenset(["hyderabad", "ladakh"]): 2300, frozenset(["hyderabad", "leh"]): 2300,
    frozenset(["hyderabad", "delhi"]): 1500, frozenset(["hyderabad", "mumbai"]): 710,
    frozenset(["hyderabad", "goa"]): 580,    frozenset(["hyderabad", "bangalore"]): 570,
    frozenset(["hyderabad", "bengaluru"]): 570, frozenset(["hyderabad", "chennai"]): 630,
    frozenset(["hyderabad", "kolkata"]): 1200, frozenset(["hyderabad", "jaipur"]): 1400,
    frozenset(["hyderabad", "manali"]): 2100, frozenset(["hyderabad", "shimla"]): 1900,
    frozenset(["hyderabad", "kochi"]): 880,  frozenset(["hyderabad", "vizag"]): 620,
    frozenset(["hyderabad", "visakhapatnam"]): 620, frozenset(["hyderabad", "kakinada"]): 450,
    frozenset(["hyderabad", "guntur"]): 270, frozenset(["hyderabad", "vijayawada"]): 270,
    frozenset(["hyderabad", "tirupati"]): 550, frozenset(["hyderabad", "rajahmundry"]): 450,
    frozenset(["ameerpet", "ladakh"]): 2300, frozenset(["ameerpet", "leh"]): 2300,
    frozenset(["ameerpet", "kakinada"]): 450, frozenset(["ameerpet", "guntur"]): 270,
    frozenset(["ameerpet", "goa"]): 580,    frozenset(["ameerpet", "manali"]): 2100,
    frozenset(["delhi", "ladakh"]): 980,    frozenset(["delhi", "leh"]): 980,
    frozenset(["delhi", "manali"]): 540,    frozenset(["delhi", "shimla"]): 340,
    frozenset(["delhi", "jaipur"]): 270,    frozenset(["delhi", "agra"]): 210,
    frozenset(["mumbai", "goa"]): 590,      frozenset(["mumbai", "pune"]): 150,
    frozenset(["mumbai", "delhi"]): 1400,   frozenset(["bangalore", "goa"]): 560,
    frozenset(["bengaluru", "goa"]): 560,   frozenset(["bangalore", "mysore"]): 145,
    frozenset(["bengaluru", "mysore"]): 145,
    # International routes (km by air)
    frozenset(["india", "thailand"]): 2900, frozenset(["india", "bangkok"]): 2900,
    frozenset(["india", "singapore"]): 3300, frozenset(["india", "dubai"]): 2800,
    frozenset(["india", "london"]): 9000,  frozenset(["india", "paris"]): 9200,
    frozenset(["india", "tokyo"]): 5800,   frozenset(["india", "bali"]): 4200,
    frozenset(["india", "kathmandu"]): 1200, frozenset(["india", "colombo"]): 1500,
    frozenset(["hyderabad", "bangkok"]): 2900, frozenset(["hyderabad", "dubai"]): 2800,
    frozenset(["hyderabad", "singapore"]): 3300, frozenset(["hyderabad", "bali"]): 4200,
    frozenset(["hyderabad", "kathmandu"]): 2000,
    frozenset(["mumbai", "dubai"]): 2000,  frozenset(["mumbai", "london"]): 9000,
    frozenset(["delhi", "dubai"]): 2200,   frozenset(["delhi", "london"]): 8500,
    frozenset(["delhi", "bangkok"]): 2800, frozenset(["delhi", "kathmandu"]): 900,
    frozenset(["delhi", "tokyo"]): 5500,
}

# Minimum expected distance (km) from a typical city for each destination category
# Used as last-resort fallback if no distance found in transport_report or KNOWN_DISTANCES
CATEGORY_MIN_DISTANCE = {
    "ultra_remote": 1500, "hill_station": 400, "beach": 300, "heritage": 300,
    "spiritual": 300, "wildlife": 250, "northeast": 1200, "city": 200, "unknown": 150,
}


def get_distance_km(origin: str, destination: str, transport_report: str, country: str) -> int:
    """
    Get the distance in km between origin and destination.

    Priority order:
    1. Parse the transport_agent's report for "XXXX km" pattern (most accurate)
    2. Look up KNOWN_DISTANCES table (hardcoded common routes)
    3. For international trips: return 5000 (signals flight needed in cost calc)
    4. Fallback: use category-based minimum distances

    Why extract from transport_report first?
      The transport_agent already searched the web for the exact distance.
      We parse its output using regex to avoid a redundant web search.
    """
    # Try to extract distance from transport_report using regex
    cleaned = transport_report.replace(",", "")
    m = re.search(r'(\d{3,5})\s*km', cleaned)
    if m:
        d = int(m.group(1))
        if d > 50:
            return d

    # Try KNOWN_DISTANCES lookup
    o, d2 = origin.lower(), destination.lower()
    for key_set, dist in KNOWN_DISTANCES.items():
        keys = list(key_set)
        if ((keys[0] in o or o in keys[0]) and (keys[1] in d2 or d2 in keys[1])) or \
           ((keys[1] in o or o in keys[1]) and (keys[0] in d2 or d2 in keys[0])):
            return dist

    # International destination → signal that a flight is needed
    if country not in ("India", "Unknown"):
        return 5000

    return 200  # Generic fallback for unknown domestic destinations


def get_transport_cost(distance_km: int, travelers: int, budget_inr: int,
                       country: str) -> dict:
    """
    Calculate transport cost based on distance.

    Returns:
      cpp            = cost per person one-way (in INR)
      mode           = transport mode string (e.g. "Domestic flight")
      round_trip_total = total round trip cost for all travelers (capped at 45% of budget)

    The 45% cap prevents transport from consuming the entire budget.
    """
    if distance_km < 50:
        cpp = 60;   mode = "Local bus / auto-rickshaw"
    elif distance_km < 150:
        cpp = 180;  mode = "Regional bus / train"
    elif distance_km < 400:
        cpp = 400;  mode = "Express bus / train"
    elif distance_km < 700:
        cpp = 650;  mode = "Overnight train / AC bus"
    elif distance_km < 1200:
        cpp = 1400; mode = "Train (3AC) / budget flight"
    else:
        if country not in ("India", "Unknown"):
            # International flight — look up actual cost from currency_helper
            cpp = get_intl_flight_inr(country) // 2   # ÷2 because round trip = 2 one-ways
            mode = f"International flight to {country}"
        else:
            cpp = 4500; mode = "Domestic flight"

    return {
        "cpp": cpp,
        "mode": mode,
        "round_trip_total": min(cpp * 2 * travelers, int(budget_inr * 0.45)),  # Cap at 45%
    }


def budget_agent(state: TripState) -> TripState:
    """
    Main budget allocation agent.

    Budget split logic (after transport is deducted):
      - Accommodation: 50% of remainder
      - Food: 50% of remainder (same as accommodation)
      - Activities: 10% of remainder (max ₹3000)
      - Local transport: 7% of remainder (max ₹300/day)
      - Shopping/misc: 8% of remainder (max ₹2500)
      - Buffer: 9% of remainder
      - Any rounding difference goes into buffer

    Also does a web search for actual prices at the destination — used as
    context in the LLM prompt to make cost tips more accurate.
    """
    print("💰  Budget Agent running...")
    llm = get_llm(temperature=0.1, max_tokens=400)

    destination = state['destination_preference']
    origin      = state.get('origin', 'your city')
    budget_inr  = state['budget_inr']
    travelers   = max(state['travelers'], 1)
    duration    = max(state['duration_days'], 1)
    nights      = max(duration - 1, 1)
    symbol      = state.get('currency_symbol', '₹')
    rate        = state.get('inr_rate', 1.0)
    country     = state.get('country', 'India')
    platforms   = get_booking_platforms(country)

    distance_km = get_distance_km(origin, destination, state.get('transport_report', ''), country)
    t = get_transport_cost(distance_km, travelers, budget_inr, country)

    # Clamp transport between 15% and 45% of total budget
    transport_amt = t["round_trip_total"]
    transport_amt = max(transport_amt, int(budget_inr * 0.15))
    transport_amt = min(transport_amt, int(budget_inr * 0.45))

    # Distribute remaining budget across other categories
    remaining  = budget_inr - transport_amt
    activities = min(3000, int(remaining * 0.10))
    local_tr   = min(300 * duration, int(remaining * 0.07))
    shopping   = min(2500, int(remaining * 0.08))
    buffer     = int(remaining * 0.09)
    hotel_food = remaining - activities - local_tr - shopping - buffer
    hotel_total= int(hotel_food * 0.50)
    food_total = hotel_food - hotel_total
    hotel_night= max(400, hotel_total // nights)
    food_day   = max(200, food_total // duration)

    # Fix any rounding error by adding it to the buffer
    actual = transport_amt + hotel_total + food_total + activities + local_tr + shopping + buffer
    buffer += (budget_inr - actual)

    # Helper: format INR amount in local currency with INR in brackets (for international trips)
    def fmt(inr_val):
        if rate == 1.0: return f"₹{int(inr_val):,}"
        local = inr_val / rate
        if local >= 1000: return f"{symbol}{int(local):,}  (₹{int(inr_val):,})"
        return f"{symbol}{local:.1f}  (₹{int(inr_val):,})"

    web = web_search(f"average travel cost {destination} per day budget 2026")

    prompt = f"""You are a global travel budget expert. Write a clear budget breakdown.

TRIP: {destination} ({country}) | {duration} days ({nights} nights) | ₹{budget_inr:,} budget | {travelers} traveler(s)
Transport mode: {t['mode']} (~{distance_km}km)
Booking platforms: {platforms}

USE THESE EXACT AMOUNTS:
- Transport ({t['mode']}, round trip): {fmt(transport_amt)} (≈ {fmt(t['cpp'])}/person one-way)
- Accommodation ({nights} nights): {fmt(hotel_total)} → {fmt(hotel_night)}/night
- Food & meals ({duration} days): {fmt(food_total)} → {fmt(food_day)}/day
- Activities & entry fees: {fmt(activities)}
- Local transport in {destination}: {fmt(local_tr)}
- Shopping / miscellaneous: {fmt(shopping)}
- Buffer (emergency 10%): {fmt(buffer)}
- TOTAL: ₹{budget_inr:,}

WEB CONTEXT (for tips only): {web[:350]}

Present this breakdown clearly, then give 2 practical money-saving tips for {destination}.
Keep under 230 words. Show amounts in local currency {symbol} with INR equivalent in brackets."""

    return {**state, "budget_report": invoke_with_retry(llm, prompt)}