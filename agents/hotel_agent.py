# agents/hotel_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def hotel_agent(state: TripState) -> TripState:
    print("🏨  Hotel Agent running...")
    llm = get_llm(temperature=0.3, max_tokens=500)
    rag = query_rag("hotels", f"hotels {state['destination_preference']}", k=3)
    web = web_search(f"best hotels {state['destination_preference']} India booking")

    budget_per_night = int(state['budget_inr'] * 0.30 / max(state['duration_days'], 1))

    prompt = f"""You are a hotel booking expert. Be concise.

TRIP: {state['destination_preference']} | {state['duration_days']} nights | Rs.{budget_per_night:,}/night budget | {state['travelers']} travelers

KNOWLEDGE BASE: {rag[:500]}
WEB: {web[:300]}

Recommend:
1. Top pick (name, price/night, why it fits)
2. Budget alternative
3. Best area to stay
4. 1 booking tip
Keep it short."""

    return {**state, "hotel_report": invoke_with_retry(llm, prompt)}