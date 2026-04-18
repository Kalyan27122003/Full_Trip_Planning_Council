# graph/orchestrator.py
# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR — The Brain of the Multi-Agent Pipeline
#
# This file builds the LangGraph graph that connects all 9 agents together
# in a defined sequence. Think of it like a factory assembly line:
#   Each station (agent) does one specific job, then passes the work forward.
#
# Pipeline flow:
#   START
#     → budget_validator   (Is the budget enough? If NO → stop immediately)
#     → destination_agent  (Research the destination via web)
#     → weather_agent      (Get weather forecast for travel dates)
#     → safety_agent       (Travel advisories, scam warnings)
#     → budget_agent       (Break down budget into categories)
#     → hotel_agent        (Find hotels within budget)
#     → food_culture_agent (Local food + cultural experiences)
#     → transport_agent    (How to travel there + local transport)
#     → itinerary_agent    (Build complete day-by-day plan)
#     → human_approval     (PAUSE here — wait for user to click Approve)
#     → END
#
# Note: The notifier_agent (Gmail + Calendar) is NOT part of this graph.
#       It is called manually from app.py AFTER the user approves, to avoid
#       accidentally sending duplicate emails.
# ─────────────────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver  # Saves state in memory between steps

from graph.state import TripState

# Import all agent functions
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
    """
    First agent in the pipeline — acts as a gatekeeper.
    Checks if the user's budget is realistic for the destination + duration.
    If budget is too low → sets state["error"] → pipeline stops (goes to END).
    If budget is OK → clears error → pipeline continues to destination_agent.
    """
    print("✅  Budget Validator running...")
    result = validate_budget(
        destination   = state["destination_preference"],
        budget_inr    = state["budget_inr"],
        duration_days = state["duration_days"],
        travelers     = state["travelers"],
    )
    if not result["valid"]:
        # Budget is insufficient — set error message to stop pipeline
        return {**state, "error": result["message"], "itinerary": result["message"]}
    # Budget is fine — clear any previous error and continue
    return {**state, "error": None}


def route_after_validation(state: TripState) -> str:
    """
    Conditional routing function — called after budget_validator.
    This is a LangGraph 'conditional edge': it decides which node to go to next.

    Returns "destination_agent" if budget is OK.
    Returns END (special LangGraph constant) if budget is invalid → stops the graph.

    This is the key design pattern for early stopping in LangGraph.
    """
    return END if state.get("error") else "destination_agent"


def human_approval_node(state: TripState) -> TripState:
    """
    A 'no-op' (do nothing) node placed at the end of the pipeline.
    Its only purpose is to be an INTERRUPT point.

    LangGraph's interrupt_before=["human_approval"] means the graph PAUSES
    before executing this node, giving the user a chance to review the itinerary.
    The graph resumes only when app.py manually calls it again after user approval.
    """
    return state  # Just pass the state through unchanged


def build_graph():
    """
    Builds and compiles the LangGraph StateGraph.

    Steps:
    1. Create a StateGraph with TripState as the shared state schema.
    2. Register each agent as a 'node' with a unique name.
    3. Define 'edges' (connections) between nodes — this sets the execution order.
    4. Add a conditional edge after budget_validator for early exit on budget failure.
    5. Set an interrupt_before human_approval so the graph pauses for user review.
    6. Attach a MemorySaver (checkpointer) so state is saved between steps.
    7. Compile and return the graph.
    """
    builder = StateGraph(TripState)

    # Register all agent functions as nodes
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

    # Set the first node to run when the graph starts
    builder.set_entry_point("budget_validator")

    # Conditional edge: after budget_validator, decide where to go next
    # If error → END, if OK → destination_agent
    builder.add_conditional_edges(
        "budget_validator", route_after_validation,
        {"destination_agent": "destination_agent", END: END},
    )

    # Linear edges: each agent runs one after another in this fixed order
    builder.add_edge("destination_agent",  "weather_agent")
    builder.add_edge("weather_agent",      "safety_agent")
    builder.add_edge("safety_agent",       "budget_agent")
    builder.add_edge("budget_agent",       "hotel_agent")
    builder.add_edge("hotel_agent",        "food_culture_agent")
    builder.add_edge("food_culture_agent", "transport_agent")
    builder.add_edge("transport_agent",    "itinerary_agent")
    builder.add_edge("itinerary_agent",    "human_approval")
    builder.add_edge("human_approval",     END)

    # MemorySaver stores the state in RAM so the graph can be paused and resumed
    # (needed for the human approval interrupt to work across Streamlit reruns)
    memory = MemorySaver()

    # interrupt_before=["human_approval"] → graph pauses BEFORE running that node
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["human_approval"],
    )
    return graph, memory


# Build the graph once at module load time (reused for all requests)
_graph, _memory = build_graph()

# Public accessors — used by app.py to get the graph and memory
def get_graph():  return _graph
def get_memory(): return _memory