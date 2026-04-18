# app.py
# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP — Streamlit UI Entry Point
#
# This is the file you run to start the application: `streamlit run app.py`
#
# Architecture overview:
#   - LEFT column  : Trip input form + live budget validation
#   - RIGHT column : Agent pipeline output (tabs for each agent's report)
#   - SIDEBAR      : Agent pipeline progress tracker + tech stack info
#
# Key UI flow:
#   1. User fills form → clicks "Start Planning Council"
#   2. Budget check (immediate) → if fails, show error and stop
#   3. Run LangGraph pipeline → stream events → update progress bar
#   4. Graph pauses at human_approval → show "Approve" button
#   5. User approves → call notifier_agent → send Gmail + add Calendar event
#
# Streamlit session_state is used to persist data across reruns
# (Streamlit reruns the entire script on every interaction).
# ─────────────────────────────────────────────────────────────────────────────
import uuid                       # To generate unique thread IDs for each planning run
import streamlit as st
from dotenv import load_dotenv
from agents.budget_validator import validate_budget, calculate_minimum_budget

load_dotenv()   # Load API keys from .env file

# ── Page Configuration ────────────────────────────────────────────────────────
# Must be the first Streamlit call in the script
st.set_page_config(
    page_title="✈️ Full Trip Planning Council",
    page_icon="✈️",
    layout="wide",                   # Use full browser width
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
# Inject custom styles for agent cards, budget boxes, and approval UI
st.markdown("""
<style>
  .main-header {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0ea5e9 100%);
    padding: 2rem; border-radius: 16px; text-align: center; margin-bottom: 2rem;
    color: white;
  }
  /* Agent card in sidebar — "done" = green left border, "pending" = grey */
  .agent-card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:1rem; margin:0.5rem 0; }
  .agent-card.done { border-left:4px solid #10b981; background:#f0fdf4; }
  .agent-card.pending { border-left:4px solid #cbd5e1; }
  /* Budget validation boxes */
  .budget-error {
    background:#fef2f2; border:2px solid #ef4444; border-radius:12px;
    padding:1.5rem; margin:1rem 0;
  }
  .budget-ok {
    background:#f0fdf4; border:2px solid #10b981; border-radius:12px;
    padding:1rem; margin:0.5rem 0;
  }
  .approve-box {
    background:#f0fdf4; border:2px solid #10b981; border-radius:12px;
    padding:1.5rem; margin:1rem 0;
  }
</style>
""", unsafe_allow_html=True)

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>✈️ Full Trip Planning Council</h1>
  <p style="font-size:1.1rem;opacity:0.9;">
    9 AI Agents • Live Web Search • Groq LLM • Real-Time Data
  </p>
</div>
""", unsafe_allow_html=True)

# ── Session State Initialisation ──────────────────────────────────────────────
# Streamlit reruns the whole script on every user action.
# session_state persists data between those reruns (like a global variable).
# We only initialise each key if it doesn't exist yet (to avoid resetting on rerun).
for key, default in {
    "thread_id":     None,      # Unique ID for this planning run (used by LangGraph checkpointer)
    "graph_state":   None,      # The final state returned by the LangGraph pipeline
    "planning_done": False,     # True once all agents have finished
    "approved":      False,     # True once user clicks the Approve button
    "notified":      False,     # True once Gmail + Calendar have been sent
    "agent_log":     [],        # List of completed agent indices (for sidebar progress)
    "budget_error":  None,      # Error message if budget_validator fails
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── SIDEBAR: Agent Pipeline Progress ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Agent Pipeline")

    # List of all 10 agents with icons and descriptions
    agents = [
        ("✅", "Budget Validator",    "Checks budget feasibility first"),
        ("🗺️", "Destination Agent",   "Shortlists best destinations"),
        ("🌤️", "Weather Agent",        "Checks travel-date weather"),
        ("🛡️", "Safety Agent",         "Travel advisories & tips"),
        ("💰", "Budget Agent",         "Allocates ₹ across categories"),
        ("🏨", "Hotel Agent",          "Finds best accommodation"),
        ("🍜", "Food & Culture Agent", "Local food + experiences"),
        ("🚌", "Transport Agent",      "Flights / trains / local travel"),
        ("📅", "Itinerary Agent",      "Builds day-by-day plan"),
        ("📧", "Notifier Agent",       "Gmail + Google Calendar"),
    ]

    log = st.session_state.agent_log  # How many agents have completed
    for i, (icon, name, desc) in enumerate(agents):
        # Mark as "done" if this agent's index is within the completed count
        status = "done" if i < len(log) else "pending"
        badge  = "✅" if i < len(log) else "⏳"
        st.markdown(f"""
        <div class="agent-card {status}">
          <strong>{icon} {name}</strong> {badge}<br>
          <small style="color:#64748b;">{desc}</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🛠️ Stack")
    st.markdown("""
    - 🧠 **Groq** `llama-3.1-8b-instant`
    - 🔍 **Tavily** live web search (all agents)
    - 🔗 **LangGraph** multi-agent
    - 🌤️ **OpenWeatherMap**
    - 📧 **Gmail** SMTP
    - 📅 **Google Calendar** API
    """)

# ── TWO-COLUMN LAYOUT ─────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 1.6], gap="large")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN: Trip Input Form + Live Budget Validation
# ══════════════════════════════════════════════════════════════════════════════
with left_col:
    st.markdown("### 📋 Trip Details")

    # Streamlit form — all inputs + submit button grouped together
    with st.form("trip_form", clear_on_submit=False):
        origin = st.text_input("🏠 Your City (Origin)", value="Hyderabad",
                               placeholder="e.g. Hyderabad, New York, London, Tokyo")
        destination_pref = st.text_input("🗺️ Destination Preference",
                                         placeholder="e.g. Paris, Bali, Tokyo, Goa, Manali, New York, Dubai")
        travel_dates = st.text_input("📅 Travel Dates",
                                     placeholder="e.g. 15 Dec 2024 to 22 Dec 2024")

        travelers = st.number_input("👥 Travelers", min_value=1, max_value=20, value=2)

        specific_places = st.text_input(
            "📍 Specific Places to Visit (optional)",
            placeholder="e.g. Shaniwar Wada, Lonavala, Osho Ashram",
            help="Leave empty to auto-select best places from web search"
        )

        budget = st.number_input("💰 Total Budget (₹)", min_value=1000,
                                 max_value=1000000, value=50000, step=5000, format="%d")

        # Auto-calculate duration from travel_dates as the user types
        duration = 1
        if travel_dates and " to " in travel_dates.lower():
            try:
                from tools.calendar_tool import parse_travel_dates
                _, _, duration = parse_travel_dates(travel_dates)
            except Exception:
                duration = 1

        interests = st.multiselect(
            "🎯 Your Interests",
            options=["Adventure & Trekking", "Beach & Water Sports", "Heritage & Culture",
                     "Wildlife & Nature", "Food & Cuisine", "Spiritual & Wellness",
                     "Photography", "Shopping", "Nightlife", "Family-friendly",
                     "Honeymoon / Romantic", "Solo Backpacking"],
            default=["Heritage & Culture", "Food & Cuisine"],
        )
        email = st.text_input(
            "📧 Email(s) — yours + friends (comma separated, max 100)",
            placeholder="you@gmail.com, friend1@gmail.com",
            help="First address in To:, rest in BCC (private).",
        )
        submitted = st.form_submit_button("🚀 Start Planning Council",
                                          use_container_width=True, type="primary")

    # ── Live Budget Validation (shown below the form, updates as user types) ──
    # This runs on EVERY page rerender — gives instant feedback before submitting
    if destination_pref and travelers and budget:
        validation = validate_budget(destination_pref, int(budget), int(duration), int(travelers))

        if not validation["valid"]:
            # Show red error box with shortfall + alternatives
            min_data = calculate_minimum_budget(destination_pref, int(duration), int(travelers))
            st.markdown(f"""
            <div class="budget-error">
              <h4>⚠️ Budget Insufficient</h4>
              <p>Your budget <strong>₹{int(budget):,}</strong> is too low for this trip.</p>
              <p>Minimum required: <strong>₹{min_data['minimum']:,}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("📊 See minimum cost breakdown"):
                for k, v in min_data["breakdown"].items():
                    st.write(f"• **{k}**: {v}")
            shortfall = min_data["minimum"] - int(budget)
            st.error(f"You need ₹{shortfall:,} more to make this trip feasible.")
            alt_days = max(1, int(budget) // (min_data["minimum"] // int(duration)))
            if alt_days < int(duration):
                st.info(f"💡 Alternatively, reduce trip to **{alt_days} days** within ₹{int(budget):,}")
        else:
            # Show green success box
            st.markdown(f"""
            <div class="budget-ok">
              ✅ Budget looks good! ₹{int(budget):,} is sufficient for this trip.
            </div>
            """, unsafe_allow_html=True)

        # Budget preview metrics — quick snapshot for the user
        st.markdown("### 💡 Quick Budget Preview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Per Person",     f"₹{int(budget) // int(travelers):,}")
        c2.metric("Per Day",        f"₹{int(budget) // int(duration):,}")
        c3.metric("Per Person/Day", f"₹{int(budget) // int(travelers) // int(duration):,}")

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: Agent Pipeline Output
# ══════════════════════════════════════════════════════════════════════════════
with right_col:
    st.markdown("### 🤖 Agent Outputs")

    # ── Form submitted: start the planning pipeline ────────────────────────────
    if submitted and destination_pref and travel_dates:

        # Final budget check before starting (in case user bypassed the live check)
        pre_check = validate_budget(destination_pref, int(budget), int(duration), int(travelers))
        if not pre_check["valid"]:
            min_data = calculate_minimum_budget(destination_pref, int(duration), int(travelers))
            st.error("🚫 Cannot start planning — budget is insufficient.")
            st.markdown(f"""
            <div class="budget-error">
              <h3>⚠️ Minimum Budget Required: ₹{min_data['minimum']:,}</h3>
              <p>Your budget: <strong>₹{int(budget):,}</strong> | Shortfall: <strong>₹{min_data['minimum'] - int(budget):,}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            st.stop()   # Halt execution — don't run the pipeline

        # Reset all session state for a fresh run
        st.session_state.thread_id     = str(uuid.uuid4())   # Unique ID for this run
        st.session_state.planning_done = False
        st.session_state.approved      = False
        st.session_state.notified      = False
        st.session_state.agent_log     = []
        st.session_state.budget_error  = None

        interests_str = ", ".join(interests) if interests else "General travel"

        # Auto-detect country + currency from destination (for the initial state)
        from agents.currency_helper import detect_country_and_currency
        _ci = detect_country_and_currency(destination_pref)

        # Build the initial state dict that gets passed into the LangGraph pipeline
        initial_state = {
            "user_query":             f"Plan a {duration}-day trip to {destination_pref}",
            "origin":                 origin,
            "destination_preference": destination_pref,
            "travel_dates":           travel_dates,
            "duration_days":          int(duration),
            "budget_inr":             int(budget),
            "travelers":              int(travelers),
            "interests":              interests_str,
            "specific_places":        specific_places,
            "email":                  email,
            # Currency info — will be updated by destination_agent, but pre-filled here
            "country":                _ci["country"],
            "currency_code":          _ci["currency_code"],
            "currency_symbol":        _ci["currency_symbol"],
            "inr_rate":               _ci["inr_rate"],
            # Empty placeholders for all agent outputs
            "destination_report":     "",
            "budget_report":          "",
            "hotel_report":           "",
            "food_culture_report":    "",
            "transport_report":       "",
            "weather_report":         "",
            "safety_report":          "",
            "itinerary":              "",
            "human_approved":         False,
            "notification_status":    "",
            "error":                  None,
        }

        # LangGraph config — thread_id is used by MemorySaver to track this run
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        progress_bar = st.progress(0, text="🚀 Starting Planning Council...")
        status_area  = st.empty()

        # Agent step labels for progress bar messages
        agent_steps = [
            ("✅ Budget Validator",    "Validating budget feasibility..."),
            ("🗺️ Destination Agent",   "Researching destination via web..."),
            ("🌤️ Weather Agent",        "Checking weather forecasts..."),
            ("🛡️ Safety Agent",         "Reviewing safety advisories..."),
            ("💰 Budget Agent",         "Allocating your budget..."),
            ("🏨 Hotel Agent",          "Finding real hotels via web..."),
            ("🍜 Food & Culture Agent", "Curating food & experiences..."),
            ("🚌 Transport Agent",      "Planning transport routes..."),
            ("📅 Itinerary Agent",      "Building your day-by-day plan..."),
        ]

        try:
            from graph.orchestrator import get_graph
            graph = get_graph()
            final_state = None

            # graph.stream() yields the state after EACH node runs
            # This lets us update the progress bar in real time
            for event in graph.stream(initial_state, config=config, stream_mode="values"):
                final_state = event

                # Check if budget_validator set an error → stop early
                if event.get("error"):
                    st.session_state.budget_error = event["error"]
                    break

                # Count how many agent outputs are filled so far
                completed = sum([
                    True,                                       # budget_validator always counts
                    bool(event.get("destination_report")),
                    bool(event.get("weather_report")),
                    bool(event.get("safety_report")),
                    bool(event.get("budget_report")),
                    bool(event.get("hotel_report")),
                    bool(event.get("food_culture_report")),
                    bool(event.get("transport_report")),
                    bool(event.get("itinerary")),
                ])
                st.session_state.agent_log = list(range(completed))
                pct   = int((completed / 9) * 90)   # Scale to 90% (last 10% = user approval)
                label = agent_steps[min(completed, len(agent_steps)-1)]
                status_area.info(f"{label[0]} — {label[1]}")
                progress_bar.progress(pct, text=f"Progress: {pct}%")

            st.session_state.graph_state   = final_state
            st.session_state.planning_done = True

            if st.session_state.budget_error:
                progress_bar.progress(0, text="❌ Planning stopped")
                status_area.error("Budget validation failed.")
            else:
                progress_bar.progress(95, text="⏸️ Waiting for your approval...")
                status_area.success("✅ All agents complete! Review your itinerary below.")

        except Exception as e:
            st.error(f"❌ Error during planning: {str(e)}")
            st.exception(e)

    # ── Budget error display ───────────────────────────────────────────────────
    if st.session_state.budget_error:
        st.markdown(f"""
        <div class="budget-error">
          <h3>⚠️ Budget Validation Failed</h3>
          <pre style="white-space:pre-wrap;font-family:inherit;font-size:13px;">
{st.session_state.budget_error}
          </pre>
        </div>
        """, unsafe_allow_html=True)

    # ── Display all agent outputs in tabs ──────────────────────────────────────
    elif st.session_state.planning_done and st.session_state.graph_state:
        gs = st.session_state.graph_state

        # One tab per agent output — user can review each agent's work
        tabs = st.tabs(["📅 Itinerary", "🗺️ Destination", "💰 Budget",
                        "🏨 Hotels", "🍜 Food & Culture",
                        "🚌 Transport", "🌤️ Weather", "🛡️ Safety"])

        with tabs[0]: st.markdown("#### 📅 Final Itinerary");        st.markdown(gs.get("itinerary", "Not generated yet."))
        with tabs[1]: st.markdown("#### 🗺️ Destination Report");     st.markdown(gs.get("destination_report", ""))
        with tabs[2]: st.markdown("#### 💰 Budget Plan");            st.markdown(gs.get("budget_report", ""))
        with tabs[3]: st.markdown("#### 🏨 Hotel Recommendations");  st.markdown(gs.get("hotel_report", ""))
        with tabs[4]: st.markdown("#### 🍜 Food & Culture Guide");   st.markdown(gs.get("food_culture_report", ""))
        with tabs[5]: st.markdown("#### 🚌 Transport Plan");         st.markdown(gs.get("transport_report", ""))
        with tabs[6]: st.markdown("#### 🌤️ Weather Advisory");       st.markdown(gs.get("weather_report", ""))
        with tabs[7]: st.markdown("#### 🛡️ Safety Briefing");        st.markdown(gs.get("safety_report", ""))

        # ── Human Approval Section ─────────────────────────────────────────────
        # The LangGraph pipeline is paused here (interrupt_before=["human_approval"]).
        # Showing the Approve button to resume and trigger notification.
        if not st.session_state.approved:
            st.markdown("---")
            st.markdown("""
            <div class="approve-box">
              <h3>⏸️ Human Approval Required</h3>
              <p>All agents have completed. Review the itinerary above,
                 then approve to send via Gmail + Google Calendar.</p>
            </div>
            """, unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve & Send Itinerary", type="primary", use_container_width=True):
                    st.session_state.approved = True
                    st.rerun()   # Trigger rerun to process the approval
            with col_b:
                if st.button("🔄 Re-Plan from Scratch", use_container_width=True):
                    # Reset all state to start over
                    for k in ["thread_id","graph_state","planning_done","approved","notified","agent_log","budget_error"]:
                        st.session_state[k] = None if k in ["thread_id","graph_state"] else ([] if k=="agent_log" else False)
                    st.rerun()

        # ── Post-Approval: Send Gmail + Calendar ───────────────────────────────
        # This block runs ONCE after the user approves — sends notifications
        if st.session_state.approved and not st.session_state.notified:
            st.info("📤 Sending itinerary via Gmail and adding to Google Calendar...")
            try:
                from agents.notifier_agent import notifier_agent
                # Add human_approved=True to state before calling notifier
                updated_state = {**st.session_state.graph_state, "human_approved": True}
                result = notifier_agent(updated_state)
                st.session_state.graph_state = result
                st.session_state.notified    = True
                st.success("🎉 All done! Your trip is planned!")
                st.markdown(f"**Notification Status:**\n\n{result.get('notification_status','')}")
            except Exception as e:
                st.error(f"Notification error: {str(e)}")

        # ── Celebration on completion ──────────────────────────────────────────
        if st.session_state.notified:
            st.balloons()   # Streamlit's confetti animation 🎈
            st.success("✈️ Have an amazing trip! Bon Voyage! 🌍")

    # ── Empty state (no planning started yet) ─────────────────────────────────
    elif not submitted:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:#94a3b8;">
          <div style="font-size:4rem;">🌍</div>
          <h3>Your AI Travel Council is Ready</h3>
          <p>Fill in your trip details on the left and hit<br>
             <strong>🚀 Start Planning Council</strong> to begin.</p>
          <br>
          <p><strong>9 specialist AI agents</strong> will collaborate using<br>
             live web search to build your perfect itinerary.</p>
        </div>
        """, unsafe_allow_html=True)