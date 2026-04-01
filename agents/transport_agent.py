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
    rag = query_rag("transport", f"{state['origin']} to {state['destination_preference']}", k=3)
    web = web_search(f"flight bus train {state['origin']} to {state['destination_preference']} price")

    prompt = f"""You are a transport expert. Be concise.

ROUTE: {state['origin']} -> {state['destination_preference']} | {state['travel_dates']} | {state['travelers']} travelers

KNOWLEDGE BASE: {rag[:500]}
WEB: {web[:300]}

Provide:
- Best travel option (flight/train/bus) with price in Rs. and duration
- Local transport at destination (daily cost)
- 1 booking tip
Keep it short."""

    return {**state, "transport_report": invoke_with_retry(llm, prompt)}