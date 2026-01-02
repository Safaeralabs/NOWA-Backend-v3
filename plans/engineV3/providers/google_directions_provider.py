from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
import requests
from django.conf import settings
from django.core.cache import cache

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

MODE_MAP = {
    "walk": "walking",
    "bike": "bicycling",
    "drive": "driving",
}

@dataclass
class GoogleDirectionsProvider:
    api_key: str

    def get_directions(
        self,
        *,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        gmode = MODE_MAP.get(mode, mode)

        (olat, olng) = origin
        (dlat, dlng) = destination

        cache_key = f"gdir:{olat:.5f},{olng:.5f}:{dlat:.5f},{dlng:.5f}:{gmode}:{language}:{region}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "key": self.api_key,
            "origin": f"{olat},{olng}",
            "destination": f"{dlat},{dlng}",
            "mode": gmode,
            "language": language,
        }
        if region:
            params["region"] = region

        r = requests.get(GOOGLE_DIRECTIONS_URL, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()

        routes = j.get("routes") or []
        if not routes:
            out = {"distance_m": 0, "duration_sec": 0, "polyline": None, "raw": j}
            cache.set(cache_key, out, 60 * 10)
            return out

        route0 = routes[0]
        leg0 = (route0.get("legs") or [{}])[0]

        distance_m = int((leg0.get("distance") or {}).get("value") or 0)
        duration_sec = int((leg0.get("duration") or {}).get("value") or 0)
        polyline = (route0.get("overview_polyline") or {}).get("points")

        out = {
            "distance_m": distance_m,
            "duration_sec": duration_sec,
            "polyline": polyline,
        }
        cache.set(cache_key, out, 60 * 10)
        return out


def build_google_directions_provider() -> GoogleDirectionsProvider:
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None) or getattr(settings, "GOOGLE_PLACES_API_KEY", None)
    if not api_key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY (or GOOGLE_PLACES_API_KEY as fallback)")
    return GoogleDirectionsProvider(api_key=api_key)
