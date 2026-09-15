import logging
import urllib.parse
import re
import httpx
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("aichatbot.weather")

WMO_WEATHER_CODES = {
    0: ("Clear Sky", "☀️", "Sunny and clear skies"),
    1: ("Mainly Clear", "🌤️", "Mostly clear skies"),
    2: ("Partly Cloudy", "⛅", "Partly cloudy"),
    3: ("Overcast", "☁️", "Cloudy and overcast"),
    45: ("Foggy", "🌫️", "Foggy conditions"),
    48: ("Depositing Rime Fog", "🌫️", "Freezing fog"),
    51: ("Light Drizzle", "🌧️", "Light drizzle"),
    53: ("Moderate Drizzle", "🌧️", "Moderate drizzle"),
    55: ("Dense Drizzle", "🌧️", "Heavy drizzle"),
    61: ("Slight Rain", "🌧️", "Light rain showers"),
    63: ("Moderate Rain", "🌧️", "Moderate rainfall"),
    65: ("Heavy Rain", "🌧️", "Heavy rain"),
    71: ("Slight Snow", "❄️", "Light snowfall"),
    73: ("Moderate Snow", "❄️", "Moderate snow"),
    75: ("Heavy Snow", "❄️", "Heavy snowfall"),
    80: ("Slight Rain Showers", "🌦️", "Light rain showers"),
    81: ("Moderate Rain Showers", "🌦️", "Rain showers"),
    82: ("Violent Rain Showers", "🌧️", "Heavy rain showers"),
    95: ("Thunderstorm", "🌩️", "Thunderstorms"),
    96: ("Thunderstorm with Hail", "⛈️", "Thunderstorms with light hail"),
    99: ("Heavy Thunderstorm with Hail", "⛈️", "Severe thunderstorm with hail"),
}

REGIONAL_FALLBACK: Dict[str, Dict[str, Any]] = {
    "maharashtra": {"name": "Maharashtra", "country": "India", "type": "State", "lat": 19.5670, "lon": 76.4165},
    "maharastra": {"name": "Maharashtra", "country": "India", "type": "State", "lat": 19.5670, "lon": 76.4165},
    "bihar": {"name": "Bihar", "country": "India", "type": "State", "lat": 25.6441, "lon": 85.9065},
    "gujarat": {"name": "Gujarat", "country": "India", "type": "State", "lat": 22.2587, "lon": 71.1924},
    "uttar pradesh": {"name": "Uttar Pradesh", "country": "India", "type": "State", "lat": 26.8467, "lon": 80.9462},
    "up": {"name": "Uttar Pradesh", "country": "India", "type": "State", "lat": 26.8467, "lon": 80.9462},
    "delhi": {"name": "Delhi", "country": "India", "type": "State/Territory", "lat": 28.6139, "lon": 77.2090},
    "karnataka": {"name": "Karnataka", "country": "India", "type": "State", "lat": 15.3173, "lon": 75.7139},
    "tamil nadu": {"name": "Tamil Nadu", "country": "India", "type": "State", "lat": 11.1271, "lon": 78.6569},
    "india": {"name": "India", "country": "India", "type": "Country", "lat": 22.3511, "lon": 78.6677},
    "usa": {"name": "United States", "country": "United States", "type": "Country", "lat": 37.0902, "lon": -95.7129},
    "united states": {"name": "United States", "country": "United States", "type": "Country", "lat": 37.0902, "lon": -95.7129},
    "uk": {"name": "United Kingdom", "country": "United Kingdom", "type": "Country", "lat": 55.3781, "lon": -3.4360},
    "united kingdom": {"name": "United Kingdom", "country": "United Kingdom", "type": "Country", "lat": 55.3781, "lon": -3.4360},
    "england": {"name": "United Kingdom", "country": "United Kingdom", "type": "Country", "lat": 55.3781, "lon": -3.4360},
    "saran": {"name": "Saran (Chapra)", "state": "Bihar", "country": "India", "type": "District", "lat": 25.9182, "lon": 84.7471},
    "mumbai": {"name": "Mumbai", "state": "Maharashtra", "country": "India", "type": "City", "lat": 19.0760, "lon": 72.8777},
    "pune": {"name": "Pune", "state": "Maharashtra", "country": "India", "type": "City", "lat": 18.5204, "lon": 73.8567},
    "patna": {"name": "Patna", "state": "Bihar", "country": "India", "type": "City", "lat": 25.5941, "lon": 85.1376},
    "nashik": {"name": "Nashik", "state": "Maharashtra", "country": "India", "type": "City", "lat": 19.9975, "lon": 73.7898},
    "london": {"name": "London", "country": "United Kingdom", "type": "City", "lat": 51.5074, "lon": -0.1278},
}

WEATHER_KEYWORDS = [
    "weather", "temperature", "temp", "forecast", "rain", "raining", "rainy",
    "humidity", "wind", "hot", "cold", "climate", "sunny", "cloudy", "storm",
    "stormy", "snow", "snowing", "drizzle", "thunderstorm", "is it raining",
    "will it rain", "how is the weather", "what's the weather", "whats the weather",
    "tell me the weather", "current temperature"
]

def get_wind_direction(degrees: float) -> str:
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((degrees + 22.5) // 45) % 8
    return directions[idx]

class WeatherService:

    @staticmethod
    def is_weather_intent(query: str) -> bool:
        """Determines if a natural language query is asking about weather."""
        if not query:
            return False
        q_lower = query.strip().lower()
        return any(kw in q_lower for kw in WEATHER_KEYWORDS)

    @staticmethod
    def extract_location(query: str) -> Optional[str]:
        """
        Extracts clean location name from a natural language query.
        Example:
        - "Tell me the weather in Maharashtra" -> "Maharashtra"
        - "What's the weather in Mumbai?" -> "Mumbai"
        - "Is it raining in Nashik?" -> "Nashik"
        """
        if not query:
            return None

        clean_q = query.strip()
        # Regex patterns to extract location after 'in', 'for', 'of', 'at'
        patterns = [
            r'(?:weather|temperature|temp|forecast|climate|rain|raining|humidity|wind)\s+(?:in|for|of|at)\s+([a-zA-Z\s,.-]{2,40})',
            r'(?:how\'s|how is|whats|what\'s|what is)\s+(?:the\s+)?(?:weather|temperature|temp|climate)\s+(?:in|for|of|at)\s+([a-zA-Z\s,.-]{2,40})',
            r'(?:is it|will it)\s+(?:rain|raining)\s+(?:in|at|for)\s+([a-zA-Z\s,.-]{2,40})',
            r'(?:tell me|give me)\s+(?:the\s+)?(?:weather|temperature|temp)\s+(?:in|of|for|at)\s+([a-zA-Z\s,.-]{2,40})',
            r'([a-zA-Z\s,.-]{2,40})\s+(?:weather|temperature|forecast)',
        ]

        for pat in patterns:
            match = re.search(pat, clean_q, re.IGNORECASE)
            if match:
                loc = match.group(1).strip(" ?!.,;:")
                # Strip trailing temporal words
                for tw in ["today", "tomorrow", "now", "right now", "current"]:
                    if loc.lower().endswith(" " + tw):
                        loc = loc[:-len(" " + tw)].strip(" ?!.,;:")
                    elif loc.lower().startswith(tw + " "):
                        loc = loc[len(tw + " "):].strip(" ?!.,;:")
                # Exclude filler phrases if captured accidentally
                if loc.lower() not in ["today", "tomorrow", "now", "current", "here", "my location", "this city", "right now"]:
                    return loc

        # Fallback filler removal
        words = clean_q.split()
        filler_words = {
            "tell", "me", "the", "weather", "temperature", "temp", "forecast", "today", "tomorrow",
            "current", "right", "now", "what", "what's", "whats", "is", "how", "how's", "hows",
            "in", "of", "for", "at", "about", "city", "state", "country", "district", "region",
            "place", "location", "please", "can", "you", "will", "it", "rain", "raining", "show", "get"
        }
        filtered = [w.strip("?!.,;:") for w in words if w.lower().strip("?!.,;:") not in filler_words]
        if filtered:
            res = " ".join(filtered).strip()
            if len(res) >= 2:
                return res

        return None

    @staticmethod
    async def geocode_location(location_name: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes any location name (City, State, Country, District, Region, or typo).
        Uses Nominatim API, Open-Meteo Geocoding, and built-in Regional Registry fallback.
        """
        if not location_name:
            return None

        clean_loc = location_name.strip().lower()

        # Check regional fallback registry first for fast, accurate state/country matching
        if clean_loc in REGIONAL_FALLBACK:
            info = REGIONAL_FALLBACK[clean_loc]
            return {
                "name": info["name"],
                "region": info.get("state", info["name"]),
                "country": info.get("country", ""),
                "location_full": f"{info['name']}, {info['country']}" if info.get("country") and info['country'] != info['name'] else info['name'],
                "latitude": info["lat"],
                "longitude": info["lon"],
                "type": info.get("type", "Location")
            }

        headers = {"User-Agent": "NexoraAI/2.0 (AI Chatbot Weather Service)"}

        # Step 1: Query Nominatim OpenStreetMap Geocoding API
        try:
            encoded = urllib.parse.quote(location_name)
            async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                res = await client.get(f"https://nominatim.openstreetmap.org/search?format=json&q={encoded}&limit=1")
                if res.status_code == 200:
                    results = res.json()
                    if results and len(results) > 0:
                        first = results[0]
                        disp_name = first.get("display_name", location_name.title())
                        parts = disp_name.split(",")
                        short_name = parts[0].strip()
                        country = parts[-1].strip() if len(parts) > 1 else ""
                        region = parts[1].strip() if len(parts) > 2 else ""

                        return {
                            "name": short_name,
                            "region": region,
                            "country": country,
                            "location_full": disp_name,
                            "latitude": float(first["lat"]),
                            "longitude": float(first["lon"]),
                            "type": first.get("addresstype", "Location")
                        }
        except Exception as e:
            logger.warning(f"Nominatim geocoding failed for '{location_name}': {e}")

        # Step 2: Query Open-Meteo Geocoding API as secondary fallback
        try:
            encoded = urllib.parse.quote(location_name)
            async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                res = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json")
                if res.status_code == 200:
                    results = res.json().get("results")
                    if results and len(results) > 0:
                        first = results[0]
                        name = first.get("name", location_name.title())
                        region = first.get("admin1", "")
                        country = first.get("country", "")
                        loc_full = name
                        if region and region != name:
                            loc_full += f", {region}"
                        if country:
                            loc_full += f", {country}"

                        return {
                            "name": name,
                            "region": region,
                            "country": country,
                            "location_full": loc_full,
                            "latitude": float(first["latitude"]),
                            "longitude": float(first["longitude"]),
                            "type": "Location"
                        }
        except Exception as e:
            logger.warning(f"Open-Meteo geocoding failed for '{location_name}': {e}")

        return None

    @staticmethod
    async def get_weather_by_coords(lat: float, lon: float) -> Dict[str, Any]:
        """Fetch weather data for explicit latitude & longitude."""
        headers = {"User-Agent": "NexoraAI/2.0 (AI Chatbot)"}
        city_name = "Current Location"
        region_name = ""
        country_name = ""

        try:
            async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                geo_res = await client.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}")
                if geo_res.status_code == 200:
                    addr = geo_res.json().get("address", {})
                    city_name = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb") or addr.get("county") or "Current Location"
                    region_name = addr.get("state") or addr.get("state_district") or ""
                    country_name = addr.get("country") or ""
        except Exception as e:
            logger.warning(f"Reverse geocoding failed for ({lat}, {lon}): {e}")

        loc_full = city_name
        if region_name and region_name != city_name:
            loc_full += f", {region_name}"
        if country_name:
            loc_full += f", {country_name}"

        return await WeatherService._fetch_open_meteo(lat, lon, city_name, region_name, country_name, loc_full)

    @staticmethod
    async def get_weather_by_city(city_or_location: str) -> Dict[str, Any]:
        """Geocodes any location (City, State, Country, District) and returns current weather."""
        if not city_or_location or not city_or_location.strip():
            return {
                "error": True,
                "message": "Which city, state, or country's weather would you like me to check? (e.g. *Weather in Maharashtra*, *Weather in Mumbai*, *Weather in London*)"
            }

        geo_info = await WeatherService.geocode_location(city_or_location)
        if not geo_info:
            return {
                "error": True,
                "location_queried": city_or_location,
                "message": f"I couldn't locate real-time weather information for **'{city_or_location}'**. Please check the spelling or provide a major city, state, or country (e.g. *Maharashtra*, *Mumbai*, *London*, *Patna*)."
            }

        return await WeatherService._fetch_open_meteo(
            lat=geo_info["latitude"],
            lon=geo_info["longitude"],
            city=geo_info["name"],
            region=geo_info["region"],
            country=geo_info["country"],
            location_full=geo_info["location_full"]
        )

    @staticmethod
    async def _fetch_open_meteo(lat: float, lon: float, city: str, region: str, country: str, location_full: str) -> Dict[str, Any]:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,precipitation,rain,showers&timezone=auto"
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    curr = data.get("current", {})

                    code = curr.get("weather_code", 0)
                    cond_info = WMO_WEATHER_CODES.get(code, ("Clear Sky", "☀️", "Clear skies"))

                    wind_deg = curr.get("wind_direction_10m", 0)
                    wind_dir = get_wind_direction(wind_deg)

                    precip = float(curr.get("precipitation", 0.0) or 0.0)
                    rain = float(curr.get("rain", 0.0) or 0.0)
                    showers = float(curr.get("showers", 0.0) or 0.0)
                    total_rain = max(precip, rain + showers)
                    is_raining = total_rain > 0.0 or code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]

                    now = datetime.now()

                    return {
                        "status": "success",
                        "city": city,
                        "region": region,
                        "country": country,
                        "location_full": location_full,
                        "latitude": lat,
                        "longitude": lon,
                        "temperature": round(curr.get("temperature_2m", 0.0), 1),
                        "feels_like": round(curr.get("apparent_temperature", 0.0), 1),
                        "humidity": curr.get("relative_humidity_2m", 0),
                        "wind_speed": round(curr.get("wind_speed_10m", 0.0), 1),
                        "wind_direction": wind_dir,
                        "condition": cond_info[0],
                        "icon": cond_info[1],
                        "description": cond_info[2],
                        "precipitation": round(total_rain, 1),
                        "is_raining": is_raining,
                        "local_time": now.strftime("%I:%M %p"),
                        "local_date": now.strftime("%A, %B %d, %Y"),
                        "updated_at": now.strftime("%I:%M %p")
                    }
        except Exception as e:
            logger.error(f"Open-Meteo API fetch error for ({lat}, {lon}): {e}")

        return {
            "error": True,
            "message": "Weather service is currently experiencing network issues. Please try again in a moment."
        }

    @staticmethod
    def format_weather_markdown(weather_data: Dict[str, Any], original_query: str = "") -> str:
        """Formats weather data into clean, natural language markdown."""
        if weather_data.get("error"):
            return weather_data.get("message", "Could not fetch weather data.")

        loc = weather_data.get("location_full") or weather_data.get("city") or "Target Location"
        temp = weather_data.get("temperature", 0.0)
        feels = weather_data.get("feels_like", temp)
        humidity = weather_data.get("humidity", 0)
        wind = weather_data.get("wind_speed", 0.0)
        wind_dir = weather_data.get("wind_direction", "N")
        condition = weather_data.get("condition", "Clear")
        icon = weather_data.get("icon", "🌤️")
        desc = weather_data.get("description", condition)
        is_raining = weather_data.get("is_raining", False)
        precip = weather_data.get("precipitation", 0.0)
        time_str = weather_data.get("local_time", "")

        q_lower = original_query.lower()

        # Special rain query format
        if "rain" in q_lower or "raining" in q_lower:
            rain_status_text = f"**Yes, raining** ({precip} mm precipitation)" if is_raining else "**No current rain reported**"
            return (
                f"### {icon} Rain & Weather Status for {loc}\n\n"
                f"* 🌧️ **Is it Raining?**: {rain_status_text}\n"
                f"* 🌡️ **Temperature**: **{temp}°C** (Feels like **{feels}°C**)\n"
                f"* 🌤️ **Condition**: **{condition}** ({desc})\n"
                f"* 💧 **Humidity**: **{humidity}%**\n"
                f"* 💨 **Wind Speed**: **{wind} km/h** ({wind_dir})\n\n"
                f"*(Real-time data updated at {time_str})*"
            )

        # Standard weather format
        return (
            f"### {icon} Current Weather in {loc}\n\n"
            f"Currently, the weather in **{loc}** is **{condition}** ({desc}), with a temperature of **{temp}°C**.\n\n"
            f"* 🌡️ **Temperature**: **{temp}°C** (Feels like **{feels}°C**)\n"
            f"* 🌤️ **Condition**: **{condition}** {icon}\n"
            f"* 💧 **Humidity**: **{humidity}%**\n"
            f"* 💨 **Wind Speed**: **{wind} km/h** ({wind_dir})\n"
            f"* 🌧️ **Precipitation**: **{precip} mm**\n\n"
            f"📍 *Real-time data retrieved via Open-Meteo API | Updated at {time_str}*"
        )
