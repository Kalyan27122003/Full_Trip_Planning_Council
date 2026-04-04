# agents/transport_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def transport_agent(state: TripState) -> TripState:
    print("🚌  Transport Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=500)

    origin      = state.get("origin", "your city")
    destination = state.get("destination_preference", "India")

    # Always web search for real distance and transport options
    web = web_search(f"distance {origin} to {destination} km bus train fare how to reach")
    rag = query_rag("transport", f"{origin} to {destination} transport options", k=2)

    prompt = f"""You are an Indian transport expert. Find the REAL transport options.

ROUTE: {origin} → {destination}
Travelers: {state['travelers']} | Travel dates: {state['travel_dates']}
Total budget: Rs.{state['budget_inr']:,}

WEB RESEARCH (use this for actual distance and options):
{web[:500]}

KNOWLEDGE BASE:
{rag[:300]}

CRITICAL DISTANCE-BASED RULES:
- Under 30km: ONLY local bus/auto/shared jeep (Rs.20-100). Do NOT mention flight or train.
- 30-100km: State bus (Rs.50-200/person) or passenger train if available
- 100-300km: Express bus or train (Rs.100-500/person)  
- 300-600km: Train sleeper/3AC (Rs.300-800) or AC bus
- Over 600km: Flight (Rs.2,000-8,000) or overnight train

Based on the actual distance between {origin} and {destination}:
1. State the approximate distance in km
2. Best transport option with realistic fare per person
3. Duration of journey
4. Local transport at {destination} (auto/bus/cab, daily cost)
5. Booking advice

Be very specific about distance and costs. If they are in the same district, say so."""

    return {**state, "transport_report": invoke_with_retry(llm, prompt)}