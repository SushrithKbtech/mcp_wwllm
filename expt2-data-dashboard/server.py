"""
Expt 2: The "Data Dashboard" Connector
MCP server exposing get_current_weather(location), backed by the free wttr.in API.
"""
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Data Dashboard")


@mcp.tool()
def get_current_weather(location: str) -> str:
    """Get the current weather for a given city or location.

    Args:
        location: City name, e.g. "Tokyo" or "Bengaluru".
    """
    url = f"https://wttr.in/{location}?format=j1"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"Error fetching weather for '{location}': {e}"

    data = resp.json()
    current = data["current_condition"][0]
    area = data["nearest_area"][0]

    city = area["areaName"][0]["value"]
    country = area["country"][0]["value"]
    temp_c = current["temp_C"]
    feels_like_c = current["FeelsLikeC"]
    desc = current["weatherDesc"][0]["value"]
    humidity = current["humidity"]
    wind_kmph = current["windspeedKmph"]

    return (
        f"Weather in {city}, {country}:\n"
        f"- Condition: {desc}\n"
        f"- Temperature: {temp_c}°C (feels like {feels_like_c}°C)\n"
        f"- Humidity: {humidity}%\n"
        f"- Wind speed: {wind_kmph} km/h"
    )


if __name__ == "__main__":
    mcp.run()
