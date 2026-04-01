# agents/budget_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def budget_agent(state: TripState) -> TripState:
    print("💰  Budget Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=600)
    rag = query_rag("destinations", f"budget cost {state['destination_preference']}", k=2)

    per_person = state['budget_inr'] // max(state['travelers'], 1)
    per_day    = state['budget_inr'] // max(state['duration_days'], 1)

    prompt = f"""You are a travel budget expert. Be concise.

TRIP: {state['destination_preference']} | {state['duration_days']} days | Rs.{state['budget_inr']:,} total | {state['travelers']} travelers
Per person: Rs.{per_person:,} | Per day: Rs.{per_day:,}

CONTEXT: {rag[:400]}

Give a short budget breakdown:
- Transport / Hotel / Food / Activities / Shopping / Buffer (10%)
- Daily spend target
- 2 money-saving tips
Use Rs. amounts. Keep it brief."""

    return {**state, "budget_report": invoke_with_retry(llm, prompt)}