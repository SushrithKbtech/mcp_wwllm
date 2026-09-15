"""
Expt 2: The "Data Dashboard" Connector
MCP server exposing get_current_weather(location), backed by the free
Open-Meteo API (geocoding + forecast, no API key required).
"""
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Data Dashboard")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


@mcp.tool()
def get_current_weather(location: str) -> str:
    """Get the current weather for a given city or location.

    Args:
        location: City name, e.g. "Tokyo" or "Bengaluru".
    """
    try:
        geo_resp = requests.get(
            GEOCODE_URL, params={"name": location, "count": 1}, timeout=10
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except requests.RequestException as e:
        return f"Error looking up location '{location}': {e}"

    results = geo_data.get("results")
    if not results:
        return f"Could not find a location matching '{location}'."

    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    city = place["name"]
    country = place.get("country", "")

    try:
        weather_resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        current = weather_resp.json()["current"]
    except requests.RequestException as e:
        return f"Error fetching weather for '{location}': {e}"

    desc = WEATHER_CODES.get(current["weather_code"], "Unknown conditions")

    return (
        f"Weather in {city}, {country}:\n"
        f"- Condition: {desc}\n"
        f"- Temperature: {current['temperature_2m']}°C\n"
        f"- Humidity: {current['relative_humidity_2m']}%\n"
        f"- Wind speed: {current['wind_speed_10m']} km/h"
    )


if __name__ == "__main__":
    mcp.run()
