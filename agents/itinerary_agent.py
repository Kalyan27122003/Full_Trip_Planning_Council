# agents/itinerary_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

# Fallback emergency contacts by state/city
EMERGENCY_CONTACTS_DB = {
    "andhra pradesh": ("Government General Hospital Vijayawada: 0866-2472600", "AP Tourism: 1800-425-4747"),
    "vizag": ("King George Hospital Visakhapatnam: 0891-2564891", "AP Tourism: 1800-425-4747"),
    "visakhapatnam": ("King George Hospital Visakhapatnam: 0891-2564891", "AP Tourism: 1800-425-4747"),
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
    "agra": ("SN Medical College: 0562-2600118", "UP Tourism: 1800-180-0151"),
    "andaman": ("GB Pant Hospital Port Blair: 03192-232102", "Andaman Tourism: 03192-232694"),
    "default": ("Nearest Government Hospital", "State Tourist Helpline: 1800-111-363"),
}

def get_emergency_contacts(destination: str) -> tuple:
    dest_lower = destination.lower()
    for key, contacts in EMERGENCY_CONTACTS_DB.items():
        if key in dest_lower or dest_lower in key:
            return contacts
    return EMERGENCY_CONTACTS_DB["default"]


def _trim(text: str, limit: int = 250) -> str:
    text = (text or "N/A").strip()
    return text[:limit] + "..." if len(text) > limit else text

SEASONAL_WARNINGS = {
    "ladakh": {
        "closed_months": [11, 12, 1, 2, 3, 4],
        "warning": "⚠️ LADAKH APRIL WARNING: Pangong, Nubra, Tso Moriri roads CLOSED in April. Only Leh city + nearby monasteries accessible. Major passes open mid-May."
    },
    "spiti": {
        "closed_months": [11, 12, 1, 2, 3, 4],
        "warning": "⚠️ Spiti roads closed Nov-April. Accessible June-October only."
    },
    "manali": {
        "closed_months": [12, 1, 2],
        "warning": "⚠️ Rohtang Pass closed Dec-April. Atal Tunnel open year-round."
    },
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

def estimate_distance_and_transport(origin: str, destination: str) -> dict:
    """
    Web search to estimate real distance and transport cost.
    Returns transport mode, estimated cost, and duration.
    """
    result = web_search(f"distance {origin} to {destination} km how to reach bus train")
    return result[:400]

def itinerary_agent(state: TripState) -> TripState:
    print("📅  Itinerary Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=2000)

    destination  = state.get("destination_preference", "India")
    origin       = state.get("origin", "your city")
    travel_dates = state.get("travel_dates", "")
    travelers    = state.get("travelers", 1)
    duration     = state.get("duration_days", 1)
    budget       = state.get("budget_inr", 0)
    interests    = state.get("interests", "General travel")

    rag_context      = query_rag("destinations", f"itinerary {destination} activities", k=2)
    seasonal_warning = get_seasonal_warning(destination, travel_dates)

    # Web search for both distance/transport AND destination info
    distance_info = estimate_distance_and_transport(origin, destination)
    dest_web_info = web_search(f"{destination} India travel places visit hotel stay food 2025")

    prompt = f"""You are a senior professional Indian travel planner with deep knowledge of local transport.

═══ MOST IMPORTANT RULE — TRANSPORT COST ═══
You MUST determine the REAL distance between {origin} and {destination} using the web research below.
Then choose the CORRECT and CHEAPEST realistic transport mode:

DISTANCE RULES:
- 0-30 km:   Local bus/auto/shared jeep — Rs.20-100 total. NO train, NO flight.
- 30-100 km: Bus (APSRTC/TSRTC/state bus) — Rs.50-200 per person. Train possible.
- 100-300 km: Bus or train — Rs.100-500 per person. No flight.
- 300-600 km: Train (sleeper/3AC) — Rs.300-800 per person. Flight if budget allows.
- 600+ km:   Flight or overnight train — Rs.2,000-8,000 per person for flight.

DISTANCE RESEARCH for {origin} → {destination}:
{distance_info}

ACCOMMODATION RULES (match budget to actual local prices):
- Small towns/villages: Rs.300-800/night (basic lodge/dharamshala/local guesthouse)
- Tier-3 cities: Rs.500-1,200/night (budget hotel)
- Tier-2 cities: Rs.800-2,000/night (decent hotel)
- Tier-1 cities/hill stations: Rs.1,500-4,000/night (mid-range hotel)
- Tourist hotspots: Rs.2,000-6,000/night (varies widely)
- If budget is tight: suggest homestay/dharamshala/lodge

FOOD COST RULES (realistic Indian 2025 prices):
- Local dhaba/street food: Rs.80-150 per meal per person
- Budget restaurant: Rs.150-300 per meal per person  
- Mid-range restaurant: Rs.300-600 per meal per person
- Do NOT suggest 5-star restaurants for budget trips

═══ SEASONAL ADVISORY ═══
{seasonal_warning if seasonal_warning else "No major seasonal concerns."}

═══ TRIP DETAILS ═══
Origin      : {origin}
Destination : {destination}
Dates       : {travel_dates}
Duration    : {duration} days
Travelers   : {travelers}
Budget      : Rs.{budget:,} TOTAL (Rs.{budget//max(travelers,1):,} per person)
Interests   : {interests}

═══ DESTINATION RESEARCH ═══
{dest_web_info[:400]}

═══ AGENT RESEARCH ═══
Destination : {_trim(state.get('destination_report'))}
Hotels      : {_trim(state.get('hotel_report'))}
Food        : {_trim(state.get('food_culture_report'))}
Transport   : {_trim(state.get('transport_report'))}
Weather     : {_trim(state.get('weather_report'))}
Safety      : {_trim(state.get('safety_report'))}
RAG         : {_trim(rag_context, 100)}

═══ BUDGET ALLOCATION RULES ═══
First figure out the REAL transport cost based on actual distance (from research above).
Then allocate the REMAINING budget realistically across accommodation, food, activities.
The TOTAL must equal exactly Rs.{budget:,}.

Example for short trip (Gollaprolu→Kakinada 24km):
- Transport: Rs.100-200 (local bus, both ways for 2 people)
- Hotel 1 night: Rs.600-1,200 (budget lodge in small city)
- Food: Rs.800-1,200 (local dhabas)
- Activities: Rs.200-500
- Buffer: remaining amount

═══ WRITE THE COMPLETE ITINERARY ═══

FULL TRIP PLAN: {destination.upper()}
From: {origin} | Dates: {travel_dates} | Travelers: {travelers} | Budget: Rs.{budget:,}

{f"⚠️ ADVISORY: {seasonal_warning}" if seasonal_warning else ""}

PRE-TRIP CHECKLIST:
1. [Specific actionable item]
2. [Specific actionable item]  
3. [Specific actionable item]

DAY-BY-DAY PLAN:

Day 0 ({travel_dates.split(' to ')[0] if ' to ' in travel_dates else ''}) - Travel from {origin} to {destination}
[Show CORRECT transport mode based on actual distance, with real cost]
[Evening arrival plan]

[Each full day: minimum 6 bullet points with times 8AM-9PM]
Day N (Date) - [Theme]
• 8:00 AM - Breakfast at [local place] (Rs.XX per person)
• 9:00 AM - [Activity] (entry: Rs.XX or free)
• 11:00 AM - [Activity] (entry: Rs.XX or free)
• 1:00 PM - Lunch at [local dhaba/restaurant] (Rs.XX per person)
• 2:30 PM - [Activity]
• 4:30 PM - [Activity]
• 7:00 PM - Dinner at [local place] (Rs.XX per person)

Day {duration+1} - Return to {origin}
[Transport back, realistic cost]

BUDGET TABLE:
| Category | Amount | Notes |
|----------|--------|-------|
| Transport {origin}↔{destination} | Rs.XXXX | [CORRECT mode — bus/train/auto based on distance] |
| Accommodation ({duration} nights) | Rs.XXXX | Rs.XXXX/night [realistic for {destination}] |
| Food & Meals | Rs.XXXX | Rs.XXX/day approx (local prices) |
| Activities & Entry Fees | Rs.XXXX | |
| Local Transport at {destination} | Rs.XXXX | |
| Shopping / Misc | Rs.XXXX | |
| Buffer | Rs.XXXX | |
| **TOTAL** | **Rs.{budget:,}** | |

PACKING LIST (5 items specific to {destination} and this season):

EMERGENCY CONTACTS:
• Police: 100 | Ambulance: 108 | Emergency: 112
• {{hospital_contact}}
• {{helpline_contact}}

3 PRO TIPS FOR {destination.upper()}:
1. [Specific genuine tip]
2. [Specific genuine tip]
3. [Specific genuine tip]"""

    return {**state, "itinerary": invoke_with_retry(llm, prompt)}