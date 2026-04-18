# TRANSPORT AGENT — How to Travel There + Local Transport
#
# Covers two things:
#   1. Intercity/international transport: How to get FROM origin TO destination
#      (flight, train, bus — based on distance)
#   2. Local transport: How to get around WITHIN the destination
#      (metro, bus, cab, tuk-tuk, etc.)
#
# Distance-based logic (also used in budget and itinerary agents):
#   < 50 km   → auto/local bus
#   50-150 km → regional train/bus
#   150-500 km → express train/bus
#   500-1200 km → overnight train or budget flight
#   > 1200 km → FLIGHT only
#
# Runs: 8th in the pipeline
# ─────────────────────────────────────────────────────────────────────────────
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import detect_country_and_currency, get_booking_platforms
from graph.state import TripState
 
 
def transport_agent(state: TripState) -> TripState:
    print("🚌  Transport Agent running...")
    llm = get_llm(temperature=0.1, max_tokens=450)
 
    origin      = state.get("origin", "your city")
    destination = state.get("destination_preference", "")
    country     = state.get("country", "India")
    platforms   = get_booking_platforms(country)
 
    # Check if this is an international trip by comparing origin and destination countries
    origin_country_info = detect_country_and_currency(origin)
    is_international = (origin_country_info["country"] != country and
                        country not in ("India", "Unknown") and
                        origin_country_info["country"] not in ("Unknown",))
 
    web1 = web_search(f"distance {origin} to {destination} km exact")
    web2 = web_search(f"how to travel {destination} from {origin} transport options fare 2026")
    web3 = web_search(f"local transport {destination} public bus metro cab daily cost 2026")
 
    # Extra instructions for international trips (flights + visa + airport transfers)
    intl_note = ""
    if is_international:
        intl_note = f"""
INTERNATIONAL TRIP: {origin} → {destination}
- Recommend flights. Search for airlines operating this route.
- Mention visa requirements briefly.
- Include airport transfer costs at destination."""
 
    prompt = f"""You are a global transport expert. Use web research for real distances and fares.
 
ROUTE: {origin} → {destination} ({country})
Travelers: {state['travelers']} | Dates: {state['travel_dates']}
Booking platforms: {platforms}
{intl_note}
 
WEB RESEARCH 1 (distance): {web1[:350]}
WEB RESEARCH 2 (transport options): {web2[:420]}
WEB RESEARCH 3 (local transport): {web3[:250]}
 
Distance-based rules:
- Under 50km: local bus/auto only
- 50-150km: regional bus or train
- 150-500km: express bus or train
- 500-1200km: overnight train or budget flight
- Over 1200km: FLIGHT only — no bus or auto suggestion
 
Provide:
1. Distance: [EXACT NUMBER] km  ← write this clearly on its own line
2. Best transport mode + realistic fare per person one-way in local currency
3. Journey duration
4. Local transport options in {destination} with daily cost
5. Booking tip — specific platform/app
 
CRITICAL: For distances over 1200km, ALWAYS say Flight. Never suggest bus/auto for long routes.
Format the distance as: "Distance: XXXX km" on its own line."""
 
    return {**state, "transport_report": invoke_with_retry(llm, prompt)}
 