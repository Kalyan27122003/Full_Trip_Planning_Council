# tools/weather_tool.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

def get_weather(city: str) -> str:
    """Get current weather for a city."""
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "⚠️ Weather API key not configured."
    try:
        resp = requests.get(
            BASE_URL,
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10,
        )
        data = resp.json()
        if resp.status_code != 200:
            return f"Weather data unavailable for {city}: {data.get('message','')}"

        weather = data["weather"][0]["description"].title()
        temp    = data["main"]["temp"]
        feels   = data["main"]["feels_like"]
        humidity= data["main"]["humidity"]
        wind    = data["wind"]["speed"]

        return (
            f"🌤️ Weather in {city}:\n"
            f"  Condition : {weather}\n"
            f"  Temperature: {temp}°C (feels like {feels}°C)\n"
            f"  Humidity  : {humidity}%\n"
            f"  Wind Speed: {wind} m/s"
        )
    except Exception as e:
        return f"Weather fetch error: {str(e)}"

def get_forecast(city: str, days: int = 5) -> str:
    """Get 5-day weather forecast for a city."""
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "⚠️ Weather API key not configured."
    try:
        resp = requests.get(
            FORECAST_URL,
            params={"q": city, "appid": api_key, "units": "metric", "cnt": days * 8},
            timeout=10,
        )
        data = resp.json()
        if resp.status_code != 200:
            return f"Forecast unavailable for {city}."

        # Sample one reading per day
        seen_dates, lines = set(), [f"📅 5-Day Forecast for {city}:"]
        for item in data.get("list", []):
            date = item["dt_txt"][:10]
            if date not in seen_dates:
                seen_dates.add(date)
                desc = item["weather"][0]["description"].title()
                tmin = item["main"]["temp_min"]
                tmax = item["main"]["temp_max"]
                lines.append(f"  {date}: {desc}, {tmin}°C – {tmax}°C")
            if len(seen_dates) >= days:
                break
        return "\n".join(lines)
    except Exception as e:
        return f"Forecast fetch error: {str(e)}"
