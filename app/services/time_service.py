import logging
import urllib.parse
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

logger = logging.getLogger("aichatbot.time")

CITY_TIMEZONE_MAP = {
    # India
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "patna": "Asia/Kolkata",
    "pune": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "ahmedabad": "Asia/Kolkata",
    "jaipur": "Asia/Kolkata",
    "lucknow": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    
    # Global major cities
    "london": "Europe/London",
    "uk": "Europe/London",
    "tokyo": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "paris": "Europe/Paris",
    "france": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "germany": "Europe/Berlin",
    "dubai": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney",
    "australia": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "toronto": "America/Toronto",
    "canada": "America/Toronto",
    "beijing": "Asia/Shanghai",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "bangkok": "Asia/Bangkok",
    "thailand": "Asia/Bangkok",
    "moscow": "Europe/Moscow",
    "russia": "Europe/Moscow",
}

class TimeService:
    @staticmethod
    def get_time_for_tz(tz_name: str = "Asia/Kolkata", location_label: str = "Local Time") -> Dict[str, Any]:
        """Return current time, date, and day for a given IANA timezone."""
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
            return {
                "status": "success",
                "location": location_label,
                "timezone": tz_name,
                "time_formatted": now.strftime("%I:%M:%S %p"),
                "time_short": now.strftime("%I:%M %p"),
                "date_formatted": now.strftime("%A, %B %d, %Y"),
                "day_name": now.strftime("%A"),
                "iso_time": now.isoformat(),
                "hour_24": now.hour,
                "minute": now.minute
            }
        except Exception as e:
            logger.error(f"Invalid timezone '{tz_name}': {e}")
            now = datetime.now()
            return {
                "status": "success",
                "location": location_label,
                "timezone": "Local System Time",
                "time_formatted": now.strftime("%I:%M:%S %p"),
                "time_short": now.strftime("%I:%M %p"),
                "date_formatted": now.strftime("%A, %B %d, %Y"),
                "day_name": now.strftime("%A"),
                "iso_time": now.isoformat(),
                "hour_24": now.hour,
                "minute": now.minute
            }

    @staticmethod
    async def get_time_for_city(city: str) -> Dict[str, Any]:
        """Determine timezone for given city and return current local time."""
        city_clean = city.strip().lower()
        
        # Check static map first
        if city_clean in CITY_TIMEZONE_MAP:
            tz_str = CITY_TIMEZONE_MAP[city_clean]
            return TimeService.get_time_for_tz(tz_str, location_label=city.title())

        # Fallback to Open-Meteo Geocoding API to resolve timezone for ANY city in the world
        try:
            encoded_city = urllib.parse.quote(city)
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json")
                if res.status_code == 200:
                    results = res.json().get("results")
                    if results and len(results) > 0:
                        first = results[0]
                        tz_str = first.get("timezone", "Asia/Kolkata")
                        display_name = f"{first.get('name')}, {first.get('country')}" if first.get('country') else first.get('name')
                        return TimeService.get_time_for_tz(tz_str, location_label=display_name)
        except Exception as e:
            logger.warning(f"Timezone lookup for city '{city}' failed: {e}")

        # Fallback to Asia/Kolkata default
        return TimeService.get_time_for_tz("Asia/Kolkata", location_label=city.title())
