# graph/orchestrator.py
"""
LangGraph Multi-Agent Orchestration

Flow:
  START → budget_validator → (invalid→END) → destination_agent
  → weather_agent → safety_agent → budget_agent → hotel_agent
  → food_culture_agent → transport_agent → itinerary_agent
  → human_approval (INTERRUPT) → END

Note: Notifier (Gmail/Calendar) is called ONCE manually from app.py after approval.
It is NOT in the graph to avoid duplicate sends.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TripState
from agents.budget_validator    import validate_budget
from agents.destination_agent   import destination_agent
from agents.budget_agent        import budget_agent
from agents.hotel_agent         import hotel_agent
from agents.food_culture_agent  import food_culture_agent
from agents.transport_agent     import transport_agent
from agents.weather_agent       import weather_agent
from agents.safety_agent        import safety_agent
from agents.itinerary_agent     import itinerary_agent


def budget_validation_node(state: TripState) -> TripState:
    print("✅  Budget Validator running...")
    result = validate_budget(
        destination   = state["destination_preference"],
        budget_inr    = state["budget_inr"],
        duration_days = state["duration_days"],
        travelers     = state["travelers"],
    )
    if not result["valid"]:
        return {**state, "error": result["message"], "itinerary": result["message"]}
    return {**state, "error": None}


def route_after_validation(state: TripState) -> str:
    return END if state.get("error") else "destination_agent"


def human_approval_node(state: TripState) -> TripState:
    """No-op — graph pauses here via interrupt_before."""
    return state


def build_graph():
    builder = StateGraph(TripState)

    builder.add_node("budget_validator",   budget_validation_node)
    builder.add_node("destination_agent",  destination_agent)
    builder.add_node("weather_agent",      weather_agent)
    builder.add_node("safety_agent",       safety_agent)
    builder.add_node("budget_agent",       budget_agent)
    builder.add_node("hotel_agent",        hotel_agent)
    builder.add_node("food_culture_agent", food_culture_agent)
    builder.add_node("transport_agent",    transport_agent)
    builder.add_node("itinerary_agent",    itinerary_agent)
    builder.add_node("human_approval",     human_approval_node)

    builder.set_entry_point("budget_validator")
    builder.add_conditional_edges(
        "budget_validator", route_after_validation,
        {"destination_agent": "destination_agent", END: END},
    )
    builder.add_edge("destination_agent",  "weather_agent")
    builder.add_edge("weather_agent",      "safety_agent")
    builder.add_edge("safety_agent",       "budget_agent")
    builder.add_edge("budget_agent",       "hotel_agent")
    builder.add_edge("hotel_agent",        "food_culture_agent")
    builder.add_edge("food_culture_agent", "transport_agent")
    builder.add_edge("transport_agent",    "itinerary_agent")
    builder.add_edge("itinerary_agent",    "human_approval")
    builder.add_edge("human_approval",     END)

    memory = MemorySaver()
    graph  = builder.compile(
        checkpointer=memory,
        interrupt_before=["human_approval"],
    )
    return graph, memory


_graph, _memory = build_graph()

def get_graph():  return _graph
def get_memory(): return _memory