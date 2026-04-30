# ✈️ Full Trip Planning Council

> **A Multi-Agent AI Travel Planner** — Plan trips anywhere in the world with 9 specialist AI agents, live web search, real-time weather, Gmail notifications, and Google Calendar integration.

---

## 🖥️ App UI

![App UI12]

---

## 📧 Email Output — Full Itinerary

### Email Header & Trip Summary
![Email Header13]

### Day-by-Day Plan
![Day by Day Plan14]

### More Days
![More Days15]

### Budget Summary Table
![Budget Summary16]

### Packing List & Emergency Contacts
![Packing List17]

### Google Calendar Button & Agent Badges
![Calendar and Footer18]

---

## 🤖 Tech Stack

| Component | Tool |
|-----------|------|
| 🧠 LLM | Groq (llama-3.1-8b-instant) |
| 🔍 Web Search | Tavily (all agents) |
| 🤖 Orchestration | LangGraph Multi-Agent |
| 🌤️ Weather | OpenWeatherMap API |
| 📧 Notifications | Gmail SMTP + Google Calendar API |
| 🎨 UI | Streamlit |
| 🌍 Global Support | 30+ countries, auto currency detection |

---

## 🧠 Agent Pipeline

| Agent | Role |
|-------|------|
| 💰 Budget Validator | Checks if budget is feasible before proceeding |
| 🗺️ Destination Agent | Researches destination via live web search |
| 🌤️ Weather Agent | Fetches real weather forecast |
| 🛡️ Safety Agent | Travel advisories via web search |
| 💵 Budget Agent | Allocates budget using real price data |
| 🏨 Hotel Agent | Finds real hotels within budget via web search |
| 🍜 Food & Culture Agent | Real restaurants & cultural experiences |
| 🚌 Transport Agent | Distance-based transport with real fares |
| 📅 Itinerary Agent | Builds final day-by-day plan from real data |
| 📧 Notifier Agent | Sends plan via Gmail + Google Calendar |

---

## 🌍 Global Support

- **30+ countries** supported — India, Japan, Thailand, UAE, Europe, USA, and more
- **Auto currency detection** — detects destination country and shows prices in local currency (¥, €, $, £, ₹) with INR equivalent
- **India domestic** — full support for all Indian destinations with state-wise emergency contacts
- **International trips** — visa info, international flight cost estimates, global booking platforms

---

## 🚀 Setup

```bash
# Clone the repo
git clone https://github.com/Kalyan27122003/full-trip-planning-council
cd full-trip-planning-council

# Install dependencies
uv venv
uv pip install -r requirements.txt

# Add your API keys to .env
cp .env.example .env

# Run the app
streamlit run app.py
```

---

## 🔑 .env Keys Required

```env
GROQ_API_KEY=
TAVILY_API_KEY=
OPENWEATHERMAP_API_KEY=
GMAIL_SENDER=
GMAIL_APP_PASSWORD=
LANGSMITH_API_KEY=        # optional
LANGSMITH_PROJECT=full_trip_planner
```

---

## 📁 Project Structure

```
full-trip-planning-council/
├── app.py                    # Streamlit UI
├── agents/
│   ├── currency_helper.py    # Global currency & country detection
│   ├── budget_validator.py   # Budget feasibility check
│   ├── destination_agent.py  # Destination research
│   ├── weather_agent.py      # Weather forecast
│   ├── safety_agent.py       # Safety advisories
│   ├── budget_agent.py       # Budget breakdown
│   ├── hotel_agent.py        # Hotel recommendations
│   ├── food_culture_agent.py # Food & culture guide
│   ├── transport_agent.py    # Transport planning
│   ├── itinerary_agent.py    # Final itinerary builder
│   ├── notifier_agent.py     # Gmail + Calendar notifier
│   └── groq_helper.py        # LLM wrapper with retry
├── graph/
│   ├── orchestrator.py       # LangGraph pipeline
│   └── state.py              # Shared trip state
└── tools/
    ├── web_search_tool.py    # Tavily web search
    ├── weather_tool.py       # OpenWeatherMap
    ├── gmail_tool.py         # Gmail SMTP
    └── calendar_tool.py      # Google Calendar OAuth
```

---

## ✨ Key Features

- ✅ **Real data only** — all agents use live Tavily web search, no hallucinated places
- ✅ **Accurate budget math** — distance-based transport cost, budget sums to exact total
- ✅ **Seasonal warnings** — alerts for Ladakh road closures, monsoon seasons, etc.
- ✅ **No place repetition** — every day visits unique named attractions
- ✅ **Correct transport mode** — auto-rickshaw for 10km, flight for 2000km
- ✅ **Beautiful HTML email** — sent to multiple recipients with Google Calendar button
- ✅ **Human approval step** — review itinerary before sending notifications
- ✅ **Global destinations** — works for any country worldwide