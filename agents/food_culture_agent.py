# agents/food_culture_agent.py
import os
from dotenv import load_dotenv
from rag.retriever import query_rag
from tools.web_search_tool import web_search
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState

load_dotenv()

def food_culture_agent(state: TripState) -> TripState:
    print("🍜  Food & Culture Agent running...")
    llm = get_llm(temperature=0.4, max_tokens=500)
    rag = query_rag("food_culture", f"food culture {state['destination_preference']}", k=3)
    web = web_search(f"local food culture experiences {state['destination_preference']} India")

    prompt = f"""You are a food & culture expert. Be concise.

DESTINATION: {state['destination_preference']} | {state['duration_days']} days | {state['interests']}

KNOWLEDGE BASE: {rag[:500]}
WEB: {web[:300]}

Provide:
- Top 3 must-eat dishes (what + where)
- 1 fine dining + 1 street food spot
- Top 2 cultural experiences
- 1 foodie tip
Keep it short."""

    return {**state, "food_culture_report": invoke_with_retry(llm, prompt)}