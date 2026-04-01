# graph/orchestrator.py
"""
LangGraph Multi-Agent Orchestration

Flow:
  START
    │
    ▼
  [PARALLEL PHASE 1]
  destination_agent ──┐
  weather_agent     ──┤
  safety_agent      ──┘
    │
    ▼
  [PARALLEL PHASE 2]  (uses destination output)
  budget_agent      ──┐
  hotel_agent       ──┤
  food_culture_agent──┤
  transport_agent   ──┘
    │
    ▼
  itinerary_agent   (synthesizes all outputs)
    │
    ▼
  human_approval    (interrupts for user confirmation)
    │
    ▼
  notifier_agent    (Gmail + Calendar)
    │
    ▼
  END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TripState
from agents.destination_agent   import destination_agent
from agents.budget_agent        import budget_agent
from agents.hotel_agent         import hotel_agent
from agents.food_culture_agent  import food_culture_agent
from agents.transport_agent     import transport_agent
from agents.weather_agent       import weather_agent
from agents.safety_agent        import safety_agent
from agents.itinerary_agent     import itinerary_agent
from agents.notifier_agent      import notifier_agent


# ── Human-in-the-loop node ────────────────────────────────────
def human_approval_node(state: TripState) -> TripState:
    """
    Interrupt point: Streamlit UI will pause here and wait for
    the user to approve or reject the itinerary.
    This node itself is a no-op — the graph pauses before it runs
    because of the interrupt_before= setting below.
    """
    return state


# ── Routing after approval ────────────────────────────────────
def route_after_approval(state: TripState) -> str:
    if state.get("human_approved"):
        return "notifier_agent"
    return END


# ── Build the graph ───────────────────────────────────────────
def build_graph():
    builder = StateGraph(TripState)

    # Register all nodes
    builder.add_node("destination_agent",   destination_agent)
    builder.add_node("weather_agent",       weather_agent)
    builder.add_node("safety_agent",        safety_agent)
    builder.add_node("budget_agent",        budget_agent)
    builder.add_node("hotel_agent",         hotel_agent)
    builder.add_node("food_culture_agent",  food_culture_agent)
    builder.add_node("transport_agent",     transport_agent)
    builder.add_node("itinerary_agent",     itinerary_agent)
    builder.add_node("human_approval",      human_approval_node)
    builder.add_node("notifier_agent",      notifier_agent)

    # ── Phase 1: Parallel (no dependencies) ──────────────────
    builder.set_entry_point("destination_agent")

    # Fan out from START to Phase 1 agents
    builder.add_edge("destination_agent", "weather_agent")
    # Note: True parallel fan-out in LangGraph requires Send API;
    # here we chain Phase 1 sequentially then fan out Phase 2.
    # This keeps the code simple while still being multi-agent.
    builder.add_edge("weather_agent",     "safety_agent")

    # ── Phase 2: Agents that need destination context ─────────
    builder.add_edge("safety_agent",      "budget_agent")
    builder.add_edge("budget_agent",      "hotel_agent")
    builder.add_edge("hotel_agent",       "food_culture_agent")
    builder.add_edge("food_culture_agent","transport_agent")

    # ── Phase 3: Final synthesis ──────────────────────────────
    builder.add_edge("transport_agent",   "itinerary_agent")

    # ── Human-in-the-loop interrupt ───────────────────────────
    builder.add_edge("itinerary_agent",   "human_approval")
    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"notifier_agent": "notifier_agent", END: END},
    )
    builder.add_edge("notifier_agent", END)

    # Compile with memory checkpointer for HITL support
    memory = MemorySaver()
    graph  = builder.compile(
        checkpointer=memory,
        interrupt_before=["human_approval"],
    )
    return graph, memory


# Singleton graph instance
_graph, _memory = build_graph()

def get_graph():
    return _graph

def get_memory():
    return _memory
