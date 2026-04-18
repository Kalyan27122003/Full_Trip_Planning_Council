# agents/itinerary_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# ITINERARY AGENT — The Final and Most Complex Agent
#
# Job: Build the complete, polished day-by-day travel plan.
#
# This agent is the "final assembler" — it reads all previous agents' outputs
# and synthesises them into one coherent itinerary. It is the most complex
# agent because it needs to:
#
#   1. Know if the destination is coastal or inland (to avoid wrong activities)
#   2. Check for seasonal closures (Ladakh in winter, monsoon in Thailand, etc.)
#   3. Recalculate the budget breakdown independently (same logic as budget_agent)
#   4. Assign real calendar dates to each day (Day 1 = start_date, etc.)
#   5. Generate a full formatted itinerary with budget table, packing list,
#      emergency contacts, and pro tips
#
# Uses the highest max_tokens (1800) because the output is the longest.
# Runs: 9th and last agent in the pipeline (before human_approval pause)
# ─────────────────────────────────────────────────────────────────────────────
import re
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import (
    detect_country_and_currency, get_booking_platforms,
    get_emergency_number, get_intl_flight_inr
)
from graph.state import TripState


# ─────────────────────────────────────────────────────────────────────────────
# DESTINATION TYPE CLASSIFIERS
# Used to decide what kind of activities to suggest in the itinerary.
# Coastal → beach/water activities are OK.
# Inland → NO beach activities (common LLM hallucination to fix).
# ─────────────────────────────────────────────────────────────────────────────
COASTAL_KEYWORDS = [
    "goa", "pondicherry", "varkala", "kovalam", "alleppey", "alappuzha",
    "palolem", "havelock", "gokarna", "murudeshwar", "tarkarli", "puri",
    "vizag", "visakhapatnam", "kakinada", "rajahmundry",
    "bali", "phuket", "koh samui", "cancun", "tulum", "maldives",
    "santorini", "mykonos", "dubrovnik", "nice", "barcelona", "lisbon",
    "rio", "sydney", "gold coast", "miami", "hawaii", "zanzibar",
    "boracay", "palawan", "langkawi", "penang", "ko lanta", "krabi",
    "cape town", "agadir", "hurghada", "sharm el sheikh",
    "monaco", "amalfi", "cinque terre", "mallorca", "ibiza",
    "el nido", "siargao", "lombok", "nusa penida",
]

INLAND_KEYWORDS = [
    "delhi", "agra", "jaipur", "jodhpur", "udaipur", "varanasi", "lucknow",
    "hyderabad", "bangalore", "bengaluru", "pune", "nagpur", "bhopal", "indore",
    "manali", "shimla", "ladakh", "leh", "rishikesh", "haridwar",
    "beijing", "paris", "london", "berlin", "prague", "vienna", "budapest",
    "madrid", "florence", "rome", "amsterdam", "istanbul", "cairo",
    "marrakech", "nairobi", "johannesburg", "kathmandu", "bangkok city",
    "tokyo", "kyoto", "seoul", "singapore city",
]


# ─────────────────────────────────────────────────────────────────────────────
# SEASONAL WARNINGS
# If the user is travelling in a month when a destination is closed/risky,
# we inject a warning into the itinerary prompt so the LLM doesn't suggest
# inaccessible places (e.g. Pangong Tso in December — road is closed).
# ─────────────────────────────────────────────────────────────────────────────
GLOBAL_SEASONAL_WARNINGS = {
    "ladakh":    {"months": [11,12,1,2,3,4], "msg": "⚠️ Pangong Tso & Nubra Valley roads CLOSED Nov–Apr. Only Leh + nearby monasteries accessible."},
    "leh":       {"months": [11,12,1,2,3,4], "msg": "⚠️ High passes closed Nov–Apr. Leh city & nearby monasteries accessible by flight only."},
    "manali":    {"months": [12,1,2],         "msg": "⚠️ Rohtang Pass closed Dec–Feb."},
    "spiti":     {"months": [11,12,1,2,3,4], "msg": "⚠️ Spiti Valley roads closed Nov–Apr."},
    "kedarnath": {"months": [11,12,1,2,3,4], "msg": "⚠️ Kedarnath temple closed Nov–Apr."},
    "everest":   {"months": [6,7,8,12,1,2],  "msg": "⚠️ Everest Base Camp: best in Mar-May & Sep-Nov. Avoid monsoon (Jun-Aug) and winter."},
    "maldives":  {"months": [6,7,8],          "msg": "⚠️ Maldives monsoon season Jun-Aug — rough seas, some resorts close."},
    "thailand":  {"months": [9,10,11],        "msg": "⚠️ Thailand monsoon peak Sep-Nov — heavy rains especially south islands."},
    "bali":      {"months": [1,2,3],          "msg": "⚠️ Bali wet season Nov–Mar — heavy rain possible. Still visitable but expect some rain."},
    "japan":     {"months": [6,7,8],          "msg": "⚠️ Japan summer (Jun-Aug) is very hot and humid. Rainy season in June."},
    "europe":    {"months": [7,8],            "msg": "⚠️ Peak tourist season in Europe — very crowded and expensive in Jul-Aug. Book in advance."},
}

# Duplicate of budget_agent's tables (needed here to recalculate budget independently)
KNOWN_DISTANCES = {
    frozenset(["hyderabad", "ladakh"]): 2300, frozenset(["hyderabad", "leh"]): 2300,
    frozenset(["hyderabad", "delhi"]): 1500, frozenset(["hyderabad", "mumbai"]): 710,
    frozenset(["hyderabad", "goa"]): 580, frozenset(["hyderabad", "bangalore"]): 570,
    frozenset(["hyderabad", "bengaluru"]): 570, frozenset(["hyderabad", "chennai"]): 630,
    frozenset(["hyderabad", "kolkata"]): 1200, frozenset(["hyderabad", "jaipur"]): 1400,
    frozenset(["hyderabad", "manali"]): 2100, frozenset(["hyderabad", "shimla"]): 1900,
    frozenset(["hyderabad", "kochi"]): 880, frozenset(["hyderabad", "vizag"]): 620,
    frozenset(["hyderabad", "visakhapatnam"]): 620, frozenset(["hyderabad", "kakinada"]): 450,
    frozenset(["hyderabad", "guntur"]): 270, frozenset(["hyderabad", "vijayawada"]): 270,
    frozenset(["hyderabad", "tirupati"]): 550, frozenset(["hyderabad", "rajahmundry"]): 450,
    frozenset(["ameerpet", "ladakh"]): 2300, frozenset(["ameerpet", "leh"]): 2300,
    frozenset(["ameerpet", "kakinada"]): 450, frozenset(["ameerpet", "guntur"]): 270,
    frozenset(["ameerpet", "goa"]): 580, frozenset(["ameerpet", "manali"]): 2100,
    frozenset(["delhi", "ladakh"]): 980, frozenset(["delhi", "leh"]): 980,
    frozenset(["delhi", "manali"]): 540, frozenset(["delhi", "shimla"]): 340,
    frozenset(["delhi", "jaipur"]): 270, frozenset(["delhi", "agra"]): 210,
    frozenset(["mumbai", "goa"]): 590, frozenset(["mumbai", "pune"]): 150,
    frozenset(["mumbai", "delhi"]): 1400, frozenset(["bangalore", "goa"]): 560,
    frozenset(["bengaluru", "goa"]): 560, frozenset(["bangalore", "mysore"]): 145,
    frozenset(["bengaluru", "mysore"]): 145,
    frozenset(["hyderabad", "bangkok"]): 2900, frozenset(["hyderabad", "dubai"]): 2800,
    frozenset(["hyderabad", "singapore"]): 3300, frozenset(["hyderabad", "bali"]): 4200,
    frozenset(["hyderabad", "kathmandu"]): 2000, frozenset(["hyderabad", "colombo"]): 1500,
    frozenset(["hyderabad", "london"]): 9000, frozenset(["hyderabad", "paris"]): 9200,
    frozenset(["hyderabad", "tokyo"]): 5800, frozenset(["hyderabad", "phuket"]): 3000,
    frozenset(["mumbai", "dubai"]): 2000, frozenset(["mumbai", "london"]): 9000,
    frozenset(["delhi", "dubai"]): 2200, frozenset(["delhi", "london"]): 8500,
    frozenset(["delhi", "bangkok"]): 2800, frozenset(["delhi", "kathmandu"]): 900,
    frozenset(["delhi", "tokyo"]): 5500, frozenset(["delhi", "singapore"]): 4000,
    frozenset(["delhi", "bali"]): 4500, frozenset(["delhi", "phuket"]): 3200,
    frozenset(["chennai", "singapore"]): 3200, frozenset(["mumbai", "bali"]): 4000,
    frozenset(["mumbai", "bangkok"]): 2700, frozenset(["mumbai", "singapore"]): 3000,
    frozenset(["bangalore", "singapore"]): 3000, frozenset(["bengaluru", "singapore"]): 3000,
    frozenset(["bangalore", "dubai"]): 2800, frozenset(["bengaluru", "dubai"]): 2800,
    frozenset(["kochi", "dubai"]): 2200, frozenset(["kochi", "singapore"]): 2800,
}

CATEGORY_MIN_DISTANCE = {
    "ultra_remote": 1500, "hill_station": 400, "beach": 300, "heritage": 300,
    "spiritual": 300, "wildlife": 250, "northeast": 1200, "city": 200, "unknown": 150,
}

# Category classification for distance fallback
DEST_CATEGORIES = {
    "ultra_remote": ["ladakh", "leh", "andaman", "spiti", "arunachal", "tawang"],
    "hill_station": ["manali", "shimla", "mussoorie", "darjeeling", "ooty", "coorg",
                     "munnar", "gangtok", "nainital", "interlaken", "zermatt"],
    "beach":        ["goa", "pondicherry", "varkala", "puri", "bali", "phuket",
                     "maldives", "boracay", "cancun", "santorini", "zanzibar"],
    "heritage":     ["jaipur", "agra", "varanasi", "hampi", "kyoto", "rome",
                     "athens", "cairo", "istanbul", "prague", "marrakech", "petra"],
    "spiritual":    ["rishikesh", "haridwar", "tirupati", "bodh gaya", "kathmandu",
                     "lumbini", "varanasi", "amritsar"],
    "wildlife":     ["ranthambore", "corbett", "kaziranga", "kanha", "kruger",
                     "masai mara", "serengeti", "wayanad"],
    "northeast":    ["meghalaya", "sikkim", "arunachal", "manipur"],
    "city":         ["delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
                     "kolkata", "pune", "tokyo", "paris", "london", "new york", "singapore",
                     "dubai", "bangkok", "seoul", "berlin", "amsterdam", "barcelona",
                     "sydney", "melbourne", "toronto", "guntur", "vijayawada", "kakinada",
                     "visakhapatnam", "vizag", "tirupati"],
}


def get_dest_category(destination: str) -> str:
    dest_lower = destination.lower()
    for cat, places in DEST_CATEGORIES.items():
        for place in places:
            if place in dest_lower or dest_lower in place:
                return cat
    return "unknown"


def get_distance_km(origin: str, destination: str, transport_report: str, country: str) -> int:
    """Same distance-finding logic as budget_agent — see budget_agent.py for explanation."""
    cleaned = transport_report.replace(",", "")
    m = re.search(r'(\d{3,5})\s*km', cleaned)
    if m:
        d = int(m.group(1))
        if d > 50:
            return d
    o, d2 = origin.lower(), destination.lower()
    for key_set, dist in KNOWN_DISTANCES.items():
        keys = list(key_set)
        if ((keys[0] in o or o in keys[0]) and (keys[1] in d2 or d2 in keys[1])) or \
           ((keys[1] in o or o in keys[1]) and (keys[0] in d2 or d2 in keys[0])):
            return dist
    if country not in ("India", "Unknown"):
        return 5000
    cat = get_dest_category(destination)
    return CATEGORY_MIN_DISTANCE.get(cat, 200)


def estimate_transport(distance_km: int, travelers: int, country: str, budget_inr: int) -> dict:
    """Same transport cost logic as budget_agent — see budget_agent.py for explanation."""
    if distance_km < 50:
        cpp = 60;   mode = "Local bus / metro"
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
            cpp = get_intl_flight_inr(country) // 2
            mode = f"International flight to {country}"
        else:
            cpp = 4500; mode = "Domestic flight"
    total = min(cpp * 2 * travelers, int(budget_inr * 0.45))
    return {"cpp": cpp, "mode": mode, "round_trip_total": total}


def is_coastal(destination: str) -> bool:
    """Check if destination is a coastal/beach location — affects activity suggestions."""
    dest_lower = destination.lower()
    return any(kw in dest_lower for kw in COASTAL_KEYWORDS)


def get_seasonal_warning(destination: str, travel_dates: str) -> str:
    """
    Check if travel dates fall in a known problematic season for this destination.
    Returns warning string if there's an issue, empty string if all clear.
    """
    month_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                 "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    travel_month = None
    for abbr, num in month_map.items():
        if abbr in travel_dates.lower():
            travel_month = num
            break
    dest_lower = destination.lower()
    for key, data in GLOBAL_SEASONAL_WARNINGS.items():
        if key in dest_lower:
            if travel_month and travel_month in data["months"]:
                return data["msg"]
    return ""


def _trim(text: str, limit: int = 160) -> str:
    """Trim a string to avoid making the final prompt too long (token limit protection)."""
    text = (text or "N/A").strip()
    return text[:limit] + "..." if len(text) > limit else text


def compute_budget(budget_inr: int, distance_km: int, travelers: int,
                   duration: int, country: str) -> dict:
    """
    Recalculate the full budget breakdown for use in the itinerary template.
    Same logic as budget_agent — done here again to have exact numbers
    available for inserting into the itinerary prompt template.
    Returns a dict of all budget line items.
    """
    nights = max(duration - 1, 1)
    t = estimate_transport(distance_km, travelers, country, budget_inr)
    transport_cost = t["round_trip_total"]
    transport_cost = max(transport_cost, int(budget_inr * 0.15))
    transport_cost = min(transport_cost, int(budget_inr * 0.45))

    remaining  = budget_inr - transport_cost
    activities = min(3000, int(remaining * 0.10))
    local_tr   = min(300 * duration, int(remaining * 0.07))
    shopping   = min(2500, int(remaining * 0.08))
    buffer     = int(remaining * 0.09)
    hotel_food = remaining - activities - local_tr - shopping - buffer
    hotel_total= int(hotel_food * 0.50)
    food_total = hotel_food - hotel_total
    hotel_night= max(400, hotel_total // nights)
    food_day   = max(200, food_total // duration)
    actual = transport_cost+hotel_total+food_total+activities+local_tr+shopping+buffer
    buffer += (budget_inr - actual)   # Fix rounding error
    return {
        "transport_cost": transport_cost, "transport_mode": t["mode"],
        "transport_per_pp": t["cpp"], "distance_km": distance_km,
        "hotel_total": hotel_total, "hotel_per_night": hotel_night,
        "food_total": food_total, "food_per_day": food_day,
        "activities": activities, "local_transport": local_tr,
        "shopping": shopping, "buffer": buffer, "nights": nights,
    }


def itinerary_agent(state: TripState) -> TripState:
    """
    Main itinerary generation function.

    Process:
    1. Extract all needed values from state (destination, budget, travelers, etc.)
    2. Determine: coastal vs inland, seasonal warnings, emergency numbers
    3. Parse travel dates → generate list of actual calendar dates for each day
    4. Recalculate budget breakdown (to have exact numbers for the prompt)
    5. Run 2 web searches (places + food)
    6. Build a very detailed, structured prompt with strict formatting rules
    7. Call LLM with high max_tokens (1800) to get the full itinerary

    The prompt template includes a pre-filled budget table with exact ₹ numbers
    so the LLM can't invent different amounts — it just fills in the descriptions.
    """
    print("📅  Itinerary Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=1800)  # Higher limit — long output

    destination     = state.get("destination_preference", "")
    origin          = state.get("origin", "your city")
    travel_dates    = state.get("travel_dates", "")
    duration        = state.get("duration_days", 1)
    travelers       = state.get("travelers", 1)
    budget_inr      = state.get("budget_inr", 0)
    interests       = state.get("interests", "General travel")
    specific_places = state.get("specific_places", "").strip()
    symbol          = state.get("currency_symbol", "₹")
    rate            = state.get("inr_rate", 1.0)
    country         = state.get("country", "India")

    coastal        = is_coastal(destination)
    seasonal_warn  = get_seasonal_warning(destination, travel_dates)
    emergency_num  = get_emergency_number(country)
    platforms      = get_booking_platforms(country)

    # Parse travel dates → get actual calendar dates for each day
    from tools.calendar_tool import parse_travel_dates
    start_date, end_date, _ = parse_travel_dates(travel_dates)
    from datetime import datetime, timedelta
    try:
        d_start   = datetime.strptime(start_date, "%Y-%m-%d")
        # Generate a date string for every day of the trip
        all_dates = [(d_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(duration)]
    except Exception:
        all_dates = [start_date] + [""] * max(duration-2, 0) + [end_date]

    distance_km = get_distance_km(origin, destination, state.get("transport_report",""), country)
    b = compute_budget(budget_inr, distance_km, travelers, duration, country)

    # Helper: format INR as local currency + INR in brackets for international trips
    def fmt(inr_val):
        if rate == 1.0:
            return f"₹{int(inr_val):,}"
        local = inr_val / rate
        if local >= 1000:
            return f"{symbol}{int(local):,} (₹{int(inr_val):,})"
        return f"{symbol}{local:.1f} (₹{int(inr_val):,})"

    # Web searches for real place names and food — used in the prompt
    web_places = web_search(f"top tourist attractions {destination} visit 2026")
    web_food   = web_search(f"famous food restaurants {destination} 2026")

    # Handle user-specified places vs auto-selection
    places_instr = f"MUST INCLUDE: {specific_places}. Fill other days from web search." \
        if specific_places else "Select real named places from web search results."

    # Coastal vs inland instruction (prevents beach activities for inland cities)
    beach_note = f"{destination} is a COASTAL/BEACH destination — beach and waterfront activities are valid." \
        if coastal else \
        f"CRITICAL: {destination} is INLAND — NO beach/sea activities. Use museums, temples, parks, markets, food tours instead."

    seasonal_block = f"\n⚠️ SEASONAL WARNING: {seasonal_warn}\n" if seasonal_warn else ""
    intl_note = f"\nINTERNATIONAL TRIP: Mention passport/visa requirements for Indian travelers visiting {country}." \
        if country not in ("India", "Unknown") else ""

    # Format date list for the prompt (Day 1: 2025-12-15, Day 2: 2025-12-16, ...)
    date_list = "\n".join([f"  Day {i+1}: {d}" for i, d in enumerate(all_dates)])

    # Large structured prompt with pre-filled budget numbers and strict formatting rules
    prompt = f"""You are a senior world travel planner. Create a complete, realistic itinerary.

WEB DATA:
PLACES: {web_places[:420]}
FOOD: {web_food[:250]}

TRIP: {origin} → {destination} ({country})
Dates: {travel_dates} | {duration} days | {travelers} traveler(s) | ₹{budget_inr:,}
Distance: ~{distance_km}km | Transport: {b['transport_mode']}
Interests: {interests}
Booking platforms: {platforms}
{beach_note}
{seasonal_block}{intl_note}

ALL DATES (one day per date, no skipping):
{date_list}

BUDGET — copy EXACT numbers:
Transport ({b['transport_mode']}, ~{b['distance_km']}km, round trip, {travelers} pax): {fmt(b['transport_cost'])} ({fmt(b['transport_per_pp'])}/person one-way)
Accommodation ({b['nights']} nights × {fmt(b['hotel_per_night'])}/night): {fmt(b['hotel_total'])}
Food ({duration} days × {fmt(b['food_per_day'])}/day): {fmt(b['food_total'])}
Activities & Entry Fees: {fmt(b['activities'])}
Local Transport: {fmt(b['local_transport'])}
Shopping/Misc: {fmt(b['shopping'])}
Buffer: {fmt(b['buffer'])}
TOTAL: ₹{budget_inr:,}

PLACES: {places_instr}
Every day MUST visit DIFFERENT named places — zero repetition across all {duration} days.

CONTEXT (summaries from earlier agents):
Hotels: {_trim(state.get('hotel_report'))}
Food: {_trim(state.get('food_culture_report'))}
Weather: {_trim(state.get('weather_report'), 100)}

STRICT RULES:
1. Only REAL named places from web search — never invent
2. Day 1 = travel/arrival | Day {duration} = return — fixed
3. Every middle day: unique theme + unique places (NO "relaxation day" or "rest day")
4. No place repeated across any 2 days
5. Transport Day 1 must match {b['transport_mode']} for {b['distance_km']}km
6. Departures: 5 AM–11 PM only. Flights: mention airport codes
7. Hotel price must be {fmt(b['hotel_per_night'])}/night — do not exceed this
8. Budget table must show EXACT amounts above with {symbol} amounts
9. {beach_note}
10. {seasonal_block if seasonal_block else "No seasonal closures for this trip."}

FORMAT:

**FULL TRIP PLAN: {destination.upper()}**
From: {origin} | Dates: {travel_dates} | Travelers: {travelers} | Budget: ₹{budget_inr:,}
{intl_note}

**PRE-TRIP CHECKLIST:**
1. Book {b['transport_mode']} via {platforms.split(',')[0].strip()}
2. Book accommodation at least 1 week in advance
3. [One specific prep tip for {destination} in {travel_dates}]
{seasonal_block}

**DAY-BY-DAY PLAN:**

**Day 1 ({all_dates[0]}) — Travel Day: {origin} → {destination}**
• [Depart {origin} via {b['transport_mode']} at [morning time 6-9 AM]]
• [Arrive {destination} + check-in at budget accommodation ~{fmt(b['hotel_per_night'])}/night]
• [1-2 light evening activities — real named place]
• [Dinner — real restaurant or specific local area]

[Days 2 to {max(duration-1,2)}: each has unique theme + unique real places + timings + entry fees + 2 meal mentions. NO rest days.]

**Day {duration} ({all_dates[-1]}) — Return to {origin}**
• 7:00 AM Breakfast and checkout
• [Morning visit to real named place if time permits]
• [Return via {b['transport_mode']} — depart by 9–11 AM]
• [Estimated arrival at {origin}]

**BUDGET SUMMARY:**
| Category | Amount | Notes |
|---|---|---|
| Transport {origin}↔{destination} ({travelers} pax, round trip) | {fmt(b['transport_cost'])} | {b['transport_mode']} — {fmt(b['transport_per_pp'])}/person one way |
| Accommodation ({b['nights']} nights) | {fmt(b['hotel_total'])} | {fmt(b['hotel_per_night'])}/night approx |
| Food & Meals ({duration} days) | {fmt(b['food_total'])} | {fmt(b['food_per_day'])}/day approx |
| Activities & Entry Fees | {fmt(b['activities'])} | |
| Local Transport | {fmt(b['local_transport'])} | bus/metro/taxi |
| Shopping / Misc | {fmt(b['shopping'])} | |
| Buffer (emergency) | {fmt(b['buffer'])} | |
| **TOTAL** | **₹{budget_inr:,}** | |

**PACKING LIST** (5 items for {destination} in {travel_dates}):
1. [item] 2. [item] 3. [item] 4. [item] 5. [item]

**EMERGENCY CONTACTS:**
• Emergency: {emergency_num}
• [Local hospital or nearest major hospital]
• [Local tourist helpline if known]

**3 PRO TIPS FOR {destination.upper()}:**
1. [Specific real tip from web research]
2. [Food recommendation — named dish + area]
3. [Practical local transport or timing tip]"""

    return {**state, "itinerary": invoke_with_retry(llm, prompt)}