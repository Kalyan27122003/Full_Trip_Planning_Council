# FOOD & CULTURE AGENT — Local Food, Restaurants, Cultural Experiences
#
# Searches for:
#   - Must-eat local dishes at the destination
#   - Real restaurant/street food market recommendations
#   - Cultural events or experiences happening in the travel MONTH
#     (It detects the travel month from dates to avoid recommending
#      festivals that happen in a different month — a common LLM mistake)
#
# Runs: 7th in the pipeline
# ─────────────────────────────────────────────────────────────────────────────
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState
 
 
def food_culture_agent(state: TripState) -> TripState:
    print("🍜  Food & Culture Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=400)
 
    destination  = state['destination_preference']
    travel_dates = state.get('travel_dates', '')
    country      = state.get('country', 'India')
 
    # Extract the travel month from dates string (e.g. "15 Dec 2025 to 20 Dec 2025" → "December")
    # This prevents the LLM from recommending festivals from wrong months
    month_map = {
        "jan": "January", "feb": "February", "mar": "March", "apr": "April",
        "may": "May", "jun": "June", "jul": "July", "aug": "August",
        "sep": "September", "oct": "October", "nov": "November", "dec": "December"
    }
    travel_month = "unknown"
    for abbr, name in month_map.items():
        if abbr in travel_dates.lower():
            travel_month = name
            break
 
    web1 = web_search(f"famous local food dishes must eat restaurants {destination} 2026")
    web2 = web_search(f"cultural experiences festivals things to do {destination} {travel_month} 2026")
 
    prompt = f"""You are a global food & culture expert. Use ONLY the web research below.
 
DESTINATION: {destination} ({country}) | {state['duration_days']} days | Travel month: {travel_month}
Interests: {state['interests']}
 
WEB RESEARCH (food/restaurants): {web1[:500]}
WEB RESEARCH (culture — {travel_month} events): {web2[:350]}
 
Provide:
1. **Must-eat dishes** — 2-3 local specialties genuinely associated with {destination}
2. **Restaurant recommendation** — real name from web search, or "local restaurants near [area name]"
3. **Street food / market** — specific area or market from web search
4. **Cultural experiences** (2) active in {travel_month} at {destination}
   - DO NOT mention festivals/events happening in a different month
5. **Foodie tip** — one practical insider tip
 
STRICT RULES:
- Never mention festivals/events outside of {travel_month}
- Only name restaurants/places confirmed in web search
- If nothing specific found: "Ask locals or check Google Maps for top-rated restaurants near [central area of {destination}]"
- Keep under 200 words"""
 
    return {**state, "food_culture_report": invoke_with_retry(llm, prompt)}
 