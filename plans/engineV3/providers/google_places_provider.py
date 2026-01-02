from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache


GOOGLE_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


@dataclass
class GooglePlacesProvider:
    api_key: str

    def nearby(
        self,
        *,
        location: Dict[str, float],
        radius_m: int,
        place_type: Optional[str] = None,
        keyword: Optional[str] = None,
        language: str = "en",
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        lat, lng = location["lat"], location["lng"]

        params = {
            "key": self.api_key,
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "language": language,
        }
        if place_type:
            params["type"] = place_type
        if keyword:
            params["keyword"] = keyword
        if region:
            params["region"] = region

        cache_key = f"gplaces:nearby:{lat:.4f}:{lng:.4f}:{radius_m}:{place_type}:{keyword}:{language}:{region}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(GOOGLE_PLACES_NEARBY_URL, params=params, timeout=10)
        data = resp.json()
        results = data.get("results") or []

        cache.set(cache_key, results, 60 * 10)  # 10 min
        return results

    def details(
        self,
        *,
        place_id: str,
        fields: Optional[List[str]] = None,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        fields = fields or [
            "place_id",
            "name",
            "geometry/location",
            "types",
            "rating",
            "user_ratings_total",
            "opening_hours",
            "business_status",
        ]

        cache_key = f"gplaces:details:{place_id}:{language}:{region}:{','.join(fields)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "key": self.api_key,
            "place_id": place_id,
            "fields": ",".join(fields),
            "language": language,
        }
        if region:
            params["region"] = region

        resp = requests.get(GOOGLE_PLACES_DETAILS_URL, params=params, timeout=10)
        data = resp.json()
        result = data.get("result") or {}

        cache.set(cache_key, result, 60 * 60 * 24)  # 24h
        return result


def build_google_places_provider() -> GooglePlacesProvider:
    api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", None)
    if not api_key:
        raise RuntimeError("Missing settings.GOOGLE_PLACES_API_KEY")
    return GooglePlacesProvider(api_key=api_key)
