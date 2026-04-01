# ✈️ Full Trip Planning Council

A Multi-Agent AI Travel Planner using:
- 🧠 Groq LLM (llama-3.1-8b-instant)
- 📚 RAG with ChromaDB + HuggingFace Embeddings
- 🤖 LangGraph Multi-Agent Orchestration
- 🛠️ MCP Tools: Web Search, Weather, Gmail, Google Calendar
- 🎨 Streamlit UI

## Agents
| Agent | Role |
|-------|------|
| Destination Agent | Shortlists best destinations |
| Budget Agent | Allocates budget across categories |
| Hotel Agent | Finds best hotels |
| Food & Culture Agent | Local food + cultural experiences |
| Transport Agent | Bus/Train/Flight options |
| Weather Agent | Weather forecast for travel dates |
| Safety Agent | Travel advisories + safety tips |
| Itinerary Agent | Builds final day-by-day plan |
| Notifier Agent | Sends plan via Gmail + Google Calendar |

## Setup

```bash
# Install dependencies
uv venv
uv pip install -r requirements.txt

# Add your API keys to .env
cp .env.example .env

# Ingest RAG data
python rag/ingest.py

# Run app
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
