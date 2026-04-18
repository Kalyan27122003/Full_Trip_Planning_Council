# ✈️ Full Trip Planning Council

A Multi-Agent AI Travel Planner using:
- 🧠 Groq LLM (llama-3.1-8b-instant)
- 🔍 Tavily Live Web Search (all agents — no RAG/ChromaDB)
- 🤖 LangGraph Multi-Agent Orchestration
- 🌤️ OpenWeatherMap
- 📧 Gmail SMTP + Google Calendar API
- 🎨 Streamlit UI

## Agents
| Agent | Role |
|-------|------|
| Budget Validator | Checks if budget is feasible before proceeding |
| Destination Agent | Researches destination via live web search |
| Weather Agent | Fetches real weather forecast |
| Safety Agent | Travel advisories via web search |
| Budget Agent | Allocates budget using real price data |
| Hotel Agent | Finds real hotels via web search |
| Food & Culture Agent | Real restaurants & cultural experiences |
| Transport Agent | Distance-based transport with real fares |
| Itinerary Agent | Builds final day-by-day plan from real data |
| Notifier Agent | Sends plan via Gmail + Google Calendar |

## Setup

```bash
# Install dependencies (no ChromaDB needed)
uv venv
uv pip install -r requirements.txt

# Add your API keys to .env
cp .env.example .env

# Run app directly — no ingest step needed
streamlit run app.py
```

## .env Keys Required
```
GROQ_API_KEY=
TAVILY_API_KEY=
OPENWEATHERMAP_API_KEY=
GMAIL_SENDER=
GMAIL_APP_PASSWORD=
LANGSMITH_API_KEY=       # optional
LANGSMITH_PROJECT=full_trip_planner
```

## What Changed (v2 — No RAG)
- Removed ChromaDB, HuggingFace embeddings, and all RAG code
- Every agent now uses Tavily web search for real, current data
- Stronger anti-hallucination prompts — agents only use web search results
- Transport agent uses actual distance from web to pick correct mode
- Hotel agent only recommends hotels found in web search
- Faster startup — no ingest step required