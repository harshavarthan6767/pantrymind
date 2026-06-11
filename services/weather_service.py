"""
PantryMind — Weather Service
Uses Open-Meteo API (free, no API key needed) for weather-aware meal suggestions.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger("pantrymind.weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def get_current_weather() -> dict:
    """Fetch current weather from Open-Meteo. Returns temperature, condition, humidity."""
    lat = float(os.getenv("USER_LATITUDE", "13.0827"))
    lon = float(os.getenv("USER_LONGITUDE", "80.2707"))
    city = os.getenv("USER_CITY", "Chennai")

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    }

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(OPEN_METEO_URL, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    logger.warning(f"Open-Meteo returned {resp.status}")
                    return _fallback(city)
                data = await resp.json()

        current = data.get("current", {})
        temp = current.get("temperature_2m", 30)
        humidity = current.get("relative_humidity_2m", 60)
        weather_code = current.get("weather_code", 0)
        wind = current.get("wind_speed_10m", 0)

        condition = _weather_code_to_text(weather_code)

        return {
            "city": city,
            "temperature": temp,
            "humidity": humidity,
            "condition": condition,
            "wind_speed": wind,
            "feels_like": "hot" if temp > 32 else "warm" if temp > 24 else "cool" if temp > 16 else "cold",
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return _fallback(city)


def _fallback(city: str) -> dict:
    return {"city": city, "temperature": 30, "humidity": 60, "condition": "Unknown", "wind_speed": 0, "feels_like": "warm"}


def _weather_code_to_text(code: int) -> str:
    mapping = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, "Unknown")


def get_meal_type_from_time() -> str:
    """Infer meal type from current time of day."""
    hour = datetime.now().hour
    if hour < 10:
        return "breakfast"
    elif hour < 15:
        return "lunch"
    elif hour < 18:
        return "evening_snack"
    else:
        return "dinner"
