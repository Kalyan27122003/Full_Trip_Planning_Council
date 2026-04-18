# SAFETY AGENT — Travel Safety Advisories + Emergency Info
#
# Searches the web for destination-specific safety info:
#   - Overall safety rating for tourists
#   - Common scams/tourist traps
#   - Emergency numbers (from currency_helper — no web search needed for this)
#   - Nearest hospital / tourist helpline
#
# Uses low temperature (0.1) because safety info should be factual, not creative.
# Runs: 4th in the pipeline
# ─────────────────────────────────────────────────────────────────────────────
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from agents.currency_helper import get_emergency_number
from graph.state import TripState
 
 
def safety_agent(state: TripState) -> TripState:
    print("🛡️  Safety Agent running...")
    llm = get_llm(temperature=0.1, max_tokens=400)  # Low temp = factual output
 
    destination = state['destination_preference']
    country     = state.get('country', 'India')
    # Get country-specific emergency numbers from our hardcoded lookup (fast, no API needed)
    emergency   = get_emergency_number(country)
 
    web1 = web_search(f"travel safety tips {destination} 2026 tourist advice")
    web2 = web_search(f"common scams tourist precautions {destination} emergency contacts")
 
    prompt = f"""You are a global travel safety advisor. Use ONLY the web research below.
 
DESTINATION: {destination} ({country}) | Travelers: {state['travelers']}
Emergency numbers for {country}: {emergency}
 
WEB RESEARCH 1 (safety): {web1[:500]}
WEB RESEARCH 2 (scams/contacts): {web2[:400]}
 
Provide based on web research:
- Safety rating: Safe / Moderate / Exercise Caution (with reason specific to {destination})
- Top 3 safety tips specific to {destination}
- 2 common scams or issues tourists face there (only if confirmed in web search)
- Emergency numbers: {emergency}
- Nearest major hospital if found in web search
- Local tourist helpline if found
 
STRICT RULE: Only mention specific scams confirmed by web search for {destination}.
Keep under 250 words."""
 
    return {**state, "safety_report": invoke_with_retry(llm, prompt)}
 