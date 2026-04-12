# agents/itinerary_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

SEASONAL_WARNINGS = {
    "ladakh": {
        "closed_months": [11, 12, 1, 2, 3, 4],
        "warning": "LADAKH APRIL WARNING: Pangong, Nubra, Tso Moriri roads CLOSED. Only Leh city monasteries accessible."
    },
    "spiti":  {"closed_months": [11,12,1,2,3,4], "warning": "Spiti roads closed Nov-April."},
    "manali": {"closed_months": [12,1,2], "warning": "Rohtang Pass closed Dec-April."},
}

EMERGENCY_CONTACTS_DB = {
    "andhra pradesh": ("Government General Hospital Vijayawada: 0866-2472600", "AP Tourism: 1800-425-4747"),
    "vizag": ("King George Hospital Visakhapatnam: 0891-2564891", "AP Tourism: 1800-425-4747"),
    "visakhapatnam": ("King George Hospital Visakhapatnam: 0891-2564891", "AP Tourism: 1800-425-4747"),
    "kakinada": ("Government Hospital Kakinada: 0884-2344800", "AP Tourism: 1800-425-4747"),
    "hyderabad": ("Osmania General Hospital: 040-24600300", "TS Tourism: 040-23452456"),
    "telangana": ("Osmania General Hospital: 040-24600300", "TS Tourism: 040-23452456"),
    "goa": ("Goa Medical College: 0832-2458700", "Goa Tourism: 1800-209-0110"),
    "kerala": ("Lakeshore Hospital Kochi: 0484-2701032", "Kerala Tourism: 1800-425-4747"),
    "rajasthan": ("SMS Hospital Jaipur: 0141-2518501", "Rajasthan Tourism: 0141-2385337"),
    "delhi": ("AIIMS Delhi: 011-26588500", "Delhi Tourism: 011-23364763"),
    "mumbai": ("KEM Hospital: 022-24107000", "Maharashtra Tourism: 022-22027762"),
    "manali": ("Mission Hospital Manali: 01902-252379", "HP Tourism: 0177-2652640"),
    "ladakh": ("SNM Hospital Leh: 01982-252360", "J&K Tourism: 0194-2548172"),
    "varanasi": ("Sir Sundar Lal Hospital BHU: 0542-2307404", "UP Tourism: 1800-180-0151"),
    "default": ("Nearest Government Hospital (dial 108)", "State Tourist Helpline: 1800-111-363"),
}

def get_seasonal_warning(destination: str, travel_dates: str) -> str:
    month_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                 "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    travel_month = None
    for abbr, num in month_map.items():
        if abbr in travel_dates.lower():
            travel_month = num
            break
    for key, data in SEASONAL_WARNINGS.items():
        if key in destination.lower():
            if travel_month and travel_month in data["closed_months"]:
                return data["warning"]
    return ""

def get_emergency_contacts(destination: str) -> tuple:
    dest_lower = destination.lower()
    for key, contacts in EMERGENCY_CONTACTS_DB.items():
        if key in dest_lower or dest_lower in key:
            return contacts
    return EMERGENCY_CONTACTS_DB["default"]

def _trim(text: str, limit: int = 200) -> str:
    text = (text or "N/A").strip()
    return text[:limit] + "..." if len(text) > limit else text

def itinerary_agent(state: TripState) -> TripState:
    print("Itinerary Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=2000)

    destination     = state.get("destination_preference", "India")
    origin          = state.get("origin", "your city")
    travel_dates    = state.get("travel_dates", "")
    duration        = state.get("duration_days", 1)
    travelers       = state.get("travelers", 1)
    budget          = state.get("budget_inr", 0)
    interests       = state.get("interests", "General travel")
    specific_places = state.get("specific_places", "").strip()

    seasonal_warning             = get_seasonal_warning(destination, travel_dates)
    hospital_contact, helpline   = get_emergency_contacts(destination)

    # Parse start/end date for display
    from tools.calendar_tool import parse_travel_dates
    start_date, end_date, _ = parse_travel_dates(travel_dates)

    # Web search for real prices
    price_info    = web_search(f"cheapest hotel {destination} India price per night budget 2025")
    transport_web = web_search(f"distance {origin} to {destination} km bus train fare 2025")
    places_web    = web_search(f"best places to visit {destination} {specific_places if specific_places else 'top tourist spots'} India")

    rag_context = query_rag("destinations", f"itinerary {destination} activities", k=2)

    # Places instruction
    if specific_places:
        places_instruction = f"""USER WANTS TO VISIT THESE SPECIFIC PLACES: {specific_places}
Include ALL of these in the itinerary. Add other nearby attractions to fill the days."""
    else:
        places_instruction = f"""USER DID NOT SPECIFY PLACES.
Use the web search results below to choose the BEST places to visit in {destination}.
WEB SEARCH FOR PLACES: {places_web[:400]}"""

    prompt = f"""You are a professional Indian travel planner. Create a REALISTIC, ACCURATE itinerary.

TRANSPORT DISTANCE RULES (STRICT — DO NOT DEVIATE):
- Distance < 100 km: LOCAL BUS only (APSRTC/TSRTC/state bus) — Rs.20-100 per person
- Distance 100-700 km: SLEEPER TRAIN — Rs.200-800 per person
- Distance > 700 km: FLIGHT — Rs.3,000-8,000 per person one way
Search the actual distance first, then apply the correct rule.

ACCOMMODATION RULES:
- Always suggest the CHEAPEST decent option (budget lodge, guesthouse, Zostel, OYO budget)
- Use web search prices: {price_info[:300]}
- Small towns: Rs.300-700/night | Tier-2 cities: Rs.600-1,200/night | Metros: Rs.800-2,000/night

IMPORTANT RULES:
1. NO Day 0 — start directly from Day 1 (travel day is Day 1)
2. Calculate duration from dates: {travel_dates} = {duration} days
3. {places_instruction}
4. Budget total MUST equal exactly Rs.{budget:,}
5. Use REAL entry fees (Kailasagiri Rs.50, Vizag Museum Rs.20, most temples FREE)
6. Transport cost from distance rules above — web searched: {transport_web[:300]}
7. Meal prices: dhaba Rs.80-150/meal, local restaurant Rs.150-300/meal
8. NEVER write placeholder text like [insert name] — use real names or "local dhaba"

SEASONAL WARNING: {seasonal_warning if seasonal_warning else "None"}

TRIP:
- From: {origin} | To: {destination}
- Dates: {travel_dates} ({duration} days)
- Travelers: {travelers} | Budget: Rs.{budget:,} (Rs.{budget//max(travelers,1):,}/person)
- Interests: {interests}

RESEARCH:
Destination: {_trim(state.get('destination_report'))}
Hotels: {_trim(state.get('hotel_report'))}
Food: {_trim(state.get('food_culture_report'))}
Transport: {_trim(state.get('transport_report'))}
Weather: {_trim(state.get('weather_report'))}

FORMAT — FOLLOW EXACTLY:

FULL TRIP PLAN: {destination.upper()}
From: {origin} | Dates: {travel_dates} | Travelers: {travelers} | Budget: Rs.{budget:,}

PRE-TRIP CHECKLIST:
1. [specific action]
2. [specific action]
3. [specific action]

DAY-BY-DAY PLAN:
(Start from Day 1 — NO Day 0)

Day 1 ({start_date}) - Travel from {origin} + Arrival at {destination}
[Travel using correct transport based on distance rule]
[Check-in to cheapest good hotel]
[Evening activity at destination]

Day 2 onwards - [Theme]
[8 AM to 9 PM schedule, 6+ activities, real prices]

Day {duration} ({end_date}) - Return to {origin}
[Morning checkout, travel back]

BUDGET TABLE:
| Category | Amount | Notes |
|----------|--------|-------|
| Transport {origin} to {destination} (round trip) | Rs.XXXX | [bus/train/flight based on distance] |
| Accommodation ({duration} nights) | Rs.XXXX | Rs.XXX/night (budget hotel name) |
| Food & Meals | Rs.XXXX | Rs.XXX/day local prices |
| Activities & Entry Fees | Rs.XXXX | |
| Local Transport | Rs.XXXX | |
| Shopping / Misc | Rs.XXXX | |
| Buffer | Rs.XXXX | |
| TOTAL | Rs.{budget:,} | |

PACKING LIST (5 items for {destination} in {travel_dates}):

EMERGENCY CONTACTS:
- Police: 100 | Ambulance: 108 | Emergency: 112
- {hospital_contact}
- {helpline}

3 PRO TIPS for {destination.upper()}:"""

    return {**state, "itinerary": invoke_with_retry(llm, prompt)}