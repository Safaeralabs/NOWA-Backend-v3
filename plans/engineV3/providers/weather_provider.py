from typing import Dict, Any
import requests
from django.conf import settings
from django.core.cache import cache


class WeatherProvider:
    """
    V3 Weather provider (MANDATORY):
    - Always returns a snapshot
    - Never raises (fallback if API fails)
    """

    def snapshot(self, *, location: Dict[str, float]) -> Dict[str, Any]:
        lat, lng = location["lat"], location["lng"]
        cache_key = f"v3weather:{lat:.3f}:{lng:.3f}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = self._fetch_openweather(lat, lng)
            cache.set(cache_key, data, 60 * 20)  # 20 min
            return data
        except Exception:
            # Hard fallback: engine keeps working even if weather provider is down
            return {
                "temp": 18,
                "feels_like": 18,
                "condition": "clear",
                "is_raining": False,
                "is_snowing": False,
                "confidence": "low",
            }

    def _fetch_openweather(self, lat: float, lng: float) -> Dict[str, Any]:
        api_key = getattr(settings, "OPENWEATHER_API_KEY", None)
        if not api_key:
            # fall back but still deterministic
            raise RuntimeError("Missing OPENWEATHER_API_KEY")

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lng,
            "appid": api_key,
            "units": "metric",
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        j = r.json()

        temp = j["main"]["temp"]
        feels = j["main"].get("feels_like", temp)
        cond = (j["weather"][0]["main"] or "").lower()

        return {
            "temp": temp,
            "feels_like": feels,
            "condition": cond,
            "is_raining": cond in ("rain", "drizzle"),
            "is_snowing": cond == "snow",
            "confidence": "high",
        }


def build_weather_provider() -> WeatherProvider:
    return WeatherProvider()
