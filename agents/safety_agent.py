# agents/safety_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def safety_agent(state: TripState) -> TripState:
    print("🛡️  Safety Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=400)
    rag = query_rag("safety_tips", f"safety {state['destination_preference']}", k=3)
    web = web_search(f"travel safety tips {state['destination_preference']} India")

    prompt = f"""You are a travel safety advisor. Be concise.

DESTINATION: {state['destination_preference']} | Travelers: {state['travelers']}

KNOWLEDGE BASE: {rag[:500]}
WEB: {web[:200]}

Provide:
- Safety rating (Safe / Moderate / Caution)
- Top 3 safety tips specific to this destination
- 2 common scams to avoid
- Emergency numbers (Police / Ambulance / Tourist helpline)
Keep it short."""

    return {**state, "safety_report": invoke_with_retry(llm, prompt)}