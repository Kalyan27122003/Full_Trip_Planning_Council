# tools/weather_tool.py
# This module fetches current weather and multi-day forecasts using the OpenWeatherMap API.

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file (e.g., OPENWEATHERMAP_API_KEY)
load_dotenv()

# Base URL for fetching CURRENT weather data
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Base URL for fetching FORECAST data (up to 5 days, in 3-hour intervals)
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def get_weather(city: str) -> str:
    """
    Fetches the current weather for a given city.

    Args:
        city: Name of the city (e.g., "Hyderabad", "Paris").

    Returns:
        A formatted string with weather details, or an error message.

    Notes:
        - Uses metric units (°C, m/s).
        - Requires OPENWEATHERMAP_API_KEY in the .env file.
    """
    # Read the API key from environment variables
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    # Abort early if the API key is missing
    if not api_key:
        return "⚠️ Weather API key not configured."

    try:
        # Make a GET request to the current weather endpoint
        # "units=metric" returns temperature in Celsius and wind in m/s
        resp = requests.get(
            BASE_URL,
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10,  # Fail after 10 seconds if no response
        )
        data = resp.json()  # Parse JSON response into a Python dictionary

        # If the city wasn't found or another API error occurred, return the error message
        if resp.status_code != 200:
            return f"Weather data unavailable for {city}: {data.get('message', '')}"

        # Extract relevant fields from the API response
        weather  = data["weather"][0]["description"].title()  # e.g., "Partly Cloudy"
        temp     = data["main"]["temp"]                        # Actual temperature in °C
        feels    = data["main"]["feels_like"]                  # Perceived temperature in °C
        humidity = data["main"]["humidity"]                    # Humidity percentage
        wind     = data["wind"]["speed"]                       # Wind speed in m/s

        # Format and return all weather details as a readable string
        return (
            f"🌤️ Weather in {city}:\n"
            f"  Condition : {weather}\n"
            f"  Temperature: {temp}°C (feels like {feels}°C)\n"
            f"  Humidity  : {humidity}%\n"
            f"  Wind Speed: {wind} m/s"
        )

    except Exception as e:
        # Catch any network errors, timeouts, or JSON parse failures
        return f"Weather fetch error: {str(e)}"


def get_forecast(city: str, days: int = 5) -> str:
    """
    Fetches a multi-day weather forecast for a given city.

    Args:
        city: Name of the city (e.g., "Hyderabad", "Paris").
        days: Number of days to forecast (default: 5, max supported by API: 5).

    Returns:
        A formatted string with one forecast entry per day, or an error message.

    Notes:
        - The OpenWeatherMap forecast API returns data in 3-hour intervals.
        - "cnt = days * 8" fetches enough intervals to cover the requested days
          (8 intervals × 3 hours = 24 hours per day).
        - We deduplicate by date so only one reading per day is shown.
        - Requires OPENWEATHERMAP_API_KEY in the .env file.
    """
    # Read the API key from environment variables
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    # Abort early if the API key is missing
    if not api_key:
        return "⚠️ Weather API key not configured."

    try:
        # Request forecast data — "cnt" controls how many 3-hour intervals to fetch
        resp = requests.get(
            FORECAST_URL,
            params={"q": city, "appid": api_key, "units": "metric", "cnt": days * 8},
            timeout=10,  # Fail after 10 seconds if no response
        )
        data = resp.json()  # Parse JSON response into a Python dictionary

        # If the API returned an error (e.g., city not found), return early
        if resp.status_code != 200:
            return f"Forecast unavailable for {city}."

        # Track which dates we've already added (to show only 1 reading per day)
        seen_dates = set()

        # Start the output with a header line
        lines = [f"📅 5-Day Forecast for {city}:"]

        # Loop through each 3-hour forecast interval returned by the API
        for item in data.get("list", []):
            # Extract just the date part (first 10 chars) from "2026-06-20 12:00:00"
            date = item["dt_txt"][:10]

            # Only process this interval if we haven't seen this date yet
            if date not in seen_dates:
                seen_dates.add(date)

                desc = item["weather"][0]["description"].title()  # e.g., "Light Rain"
                tmin = item["main"]["temp_min"]                   # Min temp for this interval
                tmax = item["main"]["temp_max"]                   # Max temp for this interval

                # Append a formatted line for this day
                lines.append(f"  {date}: {desc}, {tmin}°C – {tmax}°C")

            # Stop once we've collected enough unique days
            if len(seen_dates) >= days:
                break

        # Join all lines into a single return string
        return "\n".join(lines)

    except Exception as e:
        # Catch any network errors, timeouts, or JSON parse failures
        return f"Forecast fetch error: {str(e)}"