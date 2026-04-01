# agents/itinerary_agent.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from rag.retriever import query_rag
from graph.state import TripState

load_dotenv()

def _trim(text: str, limit: int = 250) -> str:
    """Trim text to limit to keep prompt within Groq TPM limits."""
    text = (text or "N/A").strip()
    return text[:limit] + "..." if len(text) > limit else text

def itinerary_agent(state: TripState) -> TripState:
    """Synthesizes all agent outputs into a final day-by-day itinerary."""
    print("📅  Itinerary Agent running...")

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.4,
        max_tokens=1500,
    )

    destination = state.get("destination_preference", "India")
    rag_context = query_rag("destinations", f"itinerary {destination} activities", k=2)

    # Each agent report is trimmed to ~250 chars to avoid 413 (6000 TPM limit)
    prompt = f"""You are a master travel itinerary planner for India.
Use the research summaries below to build a day-by-day itinerary.

TRIP DETAILS:
- Origin: {state['origin']} -> Destination: {destination}
- Dates: {state['travel_dates']} | Duration: {state['duration_days']} days
- Travelers: {state['travelers']} | Budget: Rs.{state['budget_inr']:,}
- Interests: {state['interests']}

RESEARCH SUMMARIES:
Destination: {_trim(state.get('destination_report'))}
Budget: {_trim(state.get('budget_report'))}
Hotel: {_trim(state.get('hotel_report'))}
Food: {_trim(state.get('food_culture_report'))}
Transport: {_trim(state.get('transport_report'))}
Weather: {_trim(state.get('weather_report'))}
Safety: {_trim(state.get('safety_report'))}
Extra: {_trim(rag_context, 150)}

NOW BUILD THE FINAL ITINERARY:

FULL TRIP PLAN: {destination.upper()}
Dates: {state['travel_dates']} | Travelers: {state['travelers']} | Budget: Rs.{state['budget_inr']:,}

PRE-TRIP CHECKLIST (3 key things to do before leaving)

DAY-BY-DAY PLAN:
Day 0 - Departure from {state['origin']}
Day 1 to Day {state['duration_days']} - (Morning / Afternoon / Evening + meals + transport + cost)
Day {state['duration_days'] + 1} - Return to {state['origin']}

BUDGET TABLE (Transport / Hotel / Food / Activities / Shopping / Buffer / TOTAL in Rs.)

PACKING LIST (5 essentials based on weather)

EMERGENCY CONTACTS for {destination} (Police / Hospital / Tourist helpline)

3 PRO TIPS for {destination}

Be specific, practical, and actionable!"""

    response = llm.invoke(prompt)
    return {**state, "itinerary": response.content}