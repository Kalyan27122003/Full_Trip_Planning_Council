# WEATHER AGENT — Fetch Real Weather + Packing Advice
#
# Uses OpenWeatherMap API (via weather_tool.py) to get:
#   - Current weather at the destination (live data)
#   - 3-day forecast
# Then asks the LLM to summarise it and give packing tips for the trip dates.
#
# Runs: 3rd in the pipeline
# ─────────────────────────────────────────────────────────────────────────────
import os
from dotenv import load_dotenv
from tools.weather_tool import get_weather, get_forecast
from agents.groq_helper import get_llm, invoke_with_retry
from graph.state import TripState
 
load_dotenv()
 
 
def weather_agent(state: TripState) -> TripState:
    print("🌤️  Weather Agent running...")
    llm = get_llm(temperature=0.2, max_tokens=400)
 
    # Call real-time OpenWeatherMap API
    current  = get_weather(state['destination_preference'])   # Current conditions
    forecast = get_forecast(state['destination_preference'], days=3)  # Next 3 days
 
    prompt = f"""You are a travel weather advisor. Be concise.
 
DESTINATION: {state['destination_preference']} | Travel: {state['travel_dates']} | Activities: {state['interests']}
 
CURRENT WEATHER: {current}
FORECAST: {forecast}
 
Provide:
- Weather summary for travel dates
- Top 5 packing essentials
- Best time of day for outdoor activities
- Any weather warning
Keep it short."""
 
    return {**state, "weather_report": invoke_with_retry(llm, prompt)}
 