# agents/destination_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def destination_agent(state: TripState) -> TripState:
    print("🗺️  Destination Agent running...")
    llm = get_llm(temperature=0.3, max_tokens=700)

    origin      = state.get("origin", "India")
    destination = state.get("destination_preference", "India")
    interests   = state.get("interests", "General travel")

    # Always web search — especially important for small/unknown places
    web = web_search(f"{destination} India travel guide places to visit things to do")
    rag = query_rag("destinations", f"{destination} travel India {interests}", k=3)

    prompt = f"""You are an India travel expert. Research and describe {destination} accurately.

TRIP:
- From: {origin} → To: {destination}
- Dates: {state['travel_dates']} | Duration: {state['duration_days']} days
- Budget: Rs.{state['budget_inr']:,} | Travelers: {state['travelers']}
- Interests: {interests}

WEB RESEARCH (use this — it has the most current info):
{web[:600]}

KNOWLEDGE BASE:
{rag[:400]}

INSTRUCTIONS:
- {destination} could be a village, small town, temple town, hill station, forest, beach, or any local spot in India
- Use the web research to find what actually exists there
- If web search confirms it exists: describe it accurately with real attractions
- If web search finds nothing: honestly say "Limited travel information found for {destination}. 
  It may be a very local spot. Here is what we suggest based on the region..."
  then suggest nearby well-known alternatives in the same district/state
- Never invent attractions, restaurants, or facilities that don't exist
- Mention if travel dates are suitable or if there are seasonal issues

Provide:
1. What {destination} is and where it is located (state, district)
2. Top attractions / things to do (only confirmed real ones)
3. Is this a good time to visit? ({state['travel_dates']})
4. Nearest major city/transport hub
5. Who this destination is best suited for"""

    return {**state, "destination_report": invoke_with_retry(llm, prompt)}