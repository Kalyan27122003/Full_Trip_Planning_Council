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
    llm   = get_llm(temperature=0.3, max_tokens=600)
    query = f"{state['destination_preference']} travel India {state['interests']}"
    rag   = query_rag("destinations", query, k=3)
    web   = web_search(f"best destinations India {state['destination_preference']} {state['interests']}")

    prompt = f"""You are an India travel destination expert. Be concise.

USER: {state['origin']} -> {state['destination_preference']} | {state['duration_days']} days | Rs.{state['budget_inr']:,} | {state['travelers']} travelers | {state['interests']}

KNOWLEDGE BASE: {rag[:600]}
WEB DATA: {web[:400]}

List TOP 3 destinations with: reason, best time, budget fit, unique highlight. Keep it short."""

    return {**state, "destination_report": invoke_with_retry(llm, prompt)}