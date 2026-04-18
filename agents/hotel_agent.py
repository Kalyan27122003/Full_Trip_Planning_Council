# HOTEL AGENT — Find Budget-Appropriate Accommodation
#
# Searches for real hotels within the accommodation budget slice.
# Budget slice: 28% of total budget is allocated for accommodation.
# Prices are shown in local currency (e.g. JPY for Japan, EUR for Europe).
#
# Key rule: ONLY recommend hotels found in web search.
#           Never invent hotel names or prices.
#
# Runs: 6th in the pipeline (after budget_agent calculates the allocations)
# ─────────────────────────────────────────────────────────────────────────────
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import detect_country_and_currency, get_booking_platforms
from graph.state import TripState
 
 
def hotel_agent(state: TripState) -> TripState:
    print("🏨  Hotel Agent running...")
    llm = get_llm(temperature=0.1, max_tokens=400)
 
    destination    = state['destination_preference']
    duration       = max(state['duration_days'], 1)
    travelers      = max(state['travelers'], 1)
    budget_inr     = state['budget_inr']
    symbol         = state.get('currency_symbol', '₹')
    rate           = state.get('inr_rate', 1.0)
    country        = state.get('country', 'India')
 
    # Calculate how many nights we need (duration - 1 because last day is travel back)
    nights = max(duration - 1, 1)
    # Allocate 28% of total budget to accommodation
    accommodation_inr = int(budget_inr * 0.28)
    max_per_night_inr = accommodation_inr // nights
 
    # Convert max nightly budget to local currency for the web search query
    if rate != 1.0 and rate > 0:
        max_per_night_local = max_per_night_inr / rate
        search_budget = f"{symbol}{max_per_night_local:.0f}"
    else:
        search_budget = f"₹{max_per_night_inr:,}"
 
    platforms = get_booking_platforms(country)
 
    web1 = web_search(f"budget hotels {destination} under {search_budget} per night 2026")
    web2 = web_search(f"best area to stay {destination} for tourists affordable")
 
    prompt = f"""You are a global hotel booking expert. Strict budget: {search_budget}/night MAX.
 
TRIP: {destination} ({country}) | {nights} night(s) | MAX {search_budget}/night | {travelers} traveler(s)
Total accommodation budget: ₹{accommodation_inr:,} (approx {search_budget} × {nights} nights)
Recommended booking platforms: {platforms}
 
WEB RESEARCH (hotels): {web1[:500]}
WEB RESEARCH (areas): {web2[:300]}
 
STRICT RULES:
- ONLY recommend hotels/hostels/guesthouses priced under {search_budget}/night
- If a property costs more than {search_budget}/night, skip it entirely
- If nothing found in web search, say: "Search on {platforms.split(',')[0].strip()} — filter under {search_budget}/night in {destination}"
- Never invent hotel names or prices
- Use local currency ({symbol}) for prices
 
Provide:
1. Best pick — real property name, price/night in {symbol}, why it fits
2. Budget alternative — cheaper option if found
3. Best area/neighbourhood to stay in {destination} for tourists
4. Booking tip — best platform and timing
 
Keep under 200 words."""
 
    return {**state, "hotel_report": invoke_with_retry(llm, prompt)}
 