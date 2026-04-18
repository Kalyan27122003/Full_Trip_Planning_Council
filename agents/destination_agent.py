# agents/destination_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# DESTINATION AGENT — Research the Travel Destination
#
# Job: Run live web searches about the destination and use the LLM to write
#      a structured travel guide: top attractions, how to reach, best time,
#      visa requirements, and who it suits.
#
# It also detects the country + currency from the destination name and
# injects that into the shared state (so all later agents know the currency).
#
# Runs: 2nd in the pipeline (after budget_validator passes)
# ─────────────────────────────────────────────────────────────────────────────
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import detect_country_and_currency
from graph.state import TripState


def destination_agent(state: TripState) -> TripState:
    print("🗺️  Destination Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=600)

    origin      = state.get("origin", "your city")
    destination = state.get("destination_preference", "")
    interests   = state.get("interests", "General travel")

    # Detect which country this destination belongs to, and what currency they use
    # This info is injected into state so all subsequent agents use it
    currency_info = detect_country_and_currency(destination)
    country = currency_info["country"]

    # Live web searches — two different queries to get broader coverage
    web1 = web_search(f"{destination} travel guide top attractions things to do 2026")
    web2 = web_search(f"{destination} best time to visit how to reach travel tips 2026")

    # The LLM prompt — structured to produce a consistent, useful output
    prompt = f"""You are a world travel expert. Use ONLY the web research below — never invent information.

TRIP: {origin} → {destination} ({country})
Dates: {state['travel_dates']} | {state['duration_days']} days | {state['travelers']} traveler(s)
Interests: {interests}

WEB RESEARCH 1: {web1[:600]}
WEB RESEARCH 2: {web2[:450]}

Based strictly on web research, provide:
1. **What & Where** — what {destination} is, which country/region/state
2. **Top Attractions** — 4-6 real places confirmed by web search
3. **Best time to visit** — is {state['travel_dates']} a good time? Any weather or seasonal warnings?
4. **How to reach** — nearest airport / train station / transport hub from major cities
5. **Visa & entry** — visa requirements for Indian passport holders (if international)
6. **Suits best** — type of traveler this destination is ideal for

RULES:
- Only mention attractions confirmed in web search
- If limited web data found, say so honestly and suggest nearby alternatives
- Keep under 320 words"""

    # Return updated state: add destination_report + inject currency info for all future agents
    updated = {
        **state,
        "country":            currency_info["country"],
        "currency_code":      currency_info["currency_code"],
        "currency_symbol":    currency_info["currency_symbol"],
        "inr_rate":           currency_info["inr_rate"],
        "destination_report": invoke_with_retry(llm, prompt),
    }
    return updated