from __future__ import annotations

from typing import Dict, Any, List, Optional, Protocol
import math


class PlacesProvider(Protocol):
    def nearby(
        self,
        *,
        location: Dict[str, float],
        radius_m: int,
        place_type: Optional[str] = None,
        keyword: Optional[str] = None,
        language: str = "en",
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    def details(
        self,
        *,
        place_id: str,
        fields: Optional[List[str]] = None,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Dict[str, Any]: ...


class WeatherProvider(Protocol):
    def snapshot(self, *, location: Dict[str, float]) -> Dict[str, Any]: ...


class DirectionsProvider(Protocol):
    def legs(self, *, stops: List[Dict[str, Any]], mode: str = "walking") -> List[Dict[str, Any]]: ...


def haversine_m(a: Dict[str, float], b: Dict[str, float]) -> float:
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lng"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lng"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    r = 6371000
    x = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(min(1, math.sqrt(x)))


class Providers:
    """
    V3 Providers:
      - places: REQUIRED
      - weather: REQUIRED
      - directions: optional (core V3 can return legs=[])
    """

    # Map internal V3 categories -> Google Place types/keywords
    CATEGORY_TO_GOOGLE = {
        # food/drink
        "bar": {"type": "bar", "keyword": None},
        "cocktail_bar": {"type": "bar", "keyword": "cocktail"},
        "wine_bar": {"type": "bar", "keyword": "wine"},
        "hotel_bar": {"type": "bar", "keyword": "hotel bar"},
        "nightclub": {"type": "night_club", "keyword": None},

        "cafe": {"type": "cafe", "keyword": None},
        "bakery": {"type": "bakery", "keyword": None},
        "dessert": {"type": "bakery", "keyword": "dessert"},

        "fast_food": {"type": "meal_takeaway", "keyword": None},
        "late_food": {"type": "meal_takeaway", "keyword": "late night"},

        # culture
        "museum": {"type": "museum", "keyword": None},
        "cinema": {"type": "movie_theater", "keyword": None},
        "theater": {"type": "performing_arts_theater", "keyword": None},
        "jazz_bar": {"type": "bar", "keyword": "jazz"},
        "cultural_bar": {"type": "bar", "keyword": "live music"},

        # shopping (Google types are limited; keywords help)
        "market": {"type": "store", "keyword": "market"},
        "boutique": {"type": "clothing_store", "keyword": "boutique"},
        "concept_store": {"type": "store", "keyword": "concept store"},
        "vintage": {"type": "clothing_store", "keyword": "vintage"},
        "shopping_area": {"type": "store", "keyword": "shopping street"},

        # photos / outdoor
        "photo_spot": {"type": "tourist_attraction", "keyword": "viewpoint"},
        "viewpoint": {"type": "tourist_attraction", "keyword": "viewpoint"},
        "street_art": {"type": "tourist_attraction", "keyword": "street art"},
    }

    def __init__(
        self,
        *,
        places: PlacesProvider,
        weather: WeatherProvider,
        directions: Optional[DirectionsProvider] = None,
        language: str = "en",
        region: Optional[str] = None,
    ):
        self.places = places
        self.weather = weather
        self.directions = directions
        self.language = language
        self.region = region

    def distance_m(self, *, user_location: Dict[str, float], place: Dict[str, Any]) -> float:
        return haversine_m(user_location, {"lat": place["lat"], "lng": place["lng"]})

    def fetch_candidates(
        self,
        *,
        city: str,
        user_location: Dict[str, float],
        categories: List[str],
        radius_m: int = 2500,
        enrich_opening_hours: bool = False,
        enrich_limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Returns normalized place dicts:
          {
            place_id, name, lat, lng, rating, user_ratings_total,
            types, opening_hours (dict), business_status, category
          }
        - Uses Nearby Search for each category mapping (bounded).
        - Optionally enriches candidates with Details to obtain opening_hours.periods.
        """
        seen = set()
        normalized: List[Dict[str, Any]] = []

        # Limit number of category queries (cost control)
        for cat in (categories or [])[:6]:
            mapping = self.CATEGORY_TO_GOOGLE.get(cat, {"type": "tourist_attraction", "keyword": None})
            gtype = mapping.get("type")
            keyword = mapping.get("keyword")

            raw = self.places.nearby(
                location=user_location,
                radius_m=radius_m,
                place_type=gtype,
                keyword=keyword,
                language=self.language,
                region=self.region,
            )

            for p in raw:
                pid = p.get("place_id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                n = self._normalize_google_place(p, preferred_categories=categories)
                if n:
                    normalized.append(n)

        # Optional enrichment: fetch Details to get opening_hours.periods etc.
        if enrich_opening_hours:
            for i in range(min(enrich_limit, len(normalized))):
                pid = normalized[i]["place_id"]
                details = self.places.details(
                    place_id=pid,
                    fields=[
                        "place_id",
                        "name",
                        "geometry/location",
                        "types",
                        "rating",
                        "user_ratings_total",
                        "opening_hours",
                        "business_status",
                    ],
                    language=self.language,
                    region=self.region,
                )
                if details:
                    # merge key fields back
                    merged = self._normalize_google_place(details, preferred_categories=categories)
                    if merged:
                        # keep score-related fields
                        normalized[i]["opening_hours"] = merged.get("opening_hours") or normalized[i].get("opening_hours") or {}
                        normalized[i]["types"] = merged.get("types") or normalized[i].get("types") or []
                        normalized[i]["business_status"] = merged.get("business_status") or normalized[i].get("business_status")
                        # category guess could improve with details types
                        normalized[i]["category"] = merged.get("category") or normalized[i].get("category")

        return normalized

    def get_weather(self, *, user_location: Dict[str, float]) -> Dict[str, Any]:
        # required provider; should never raise
        return self.weather.snapshot(location=user_location)

    def get_legs(self, *, stops: List[Dict[str, Any]], mode: str = "walking") -> List[Dict[str, Any]]:
        if not self.directions or len(stops) < 2:
            return []
        return self.directions.legs(stops=stops, mode=mode)

    # --------------------
    # Normalization helpers
    # --------------------
    def _normalize_google_place(self, p: Dict[str, Any], preferred_categories: List[str]) -> Optional[Dict[str, Any]]:
        # Google structures: either top-level "geometry.location" or already "location"
        geom = p.get("geometry", {}) if isinstance(p.get("geometry"), dict) else {}
        loc = geom.get("location") if isinstance(geom.get("location"), dict) else None
        if not loc:
            # sometimes details may return "geometry": {"location": {...}} always
            # if absent, try alternative
            loc = p.get("location") if isinstance(p.get("location"), dict) else None
        if not loc or "lat" not in loc or "lng" not in loc:
            return None

        types = p.get("types") or []
        category_guess = self._guess_category(types, preferred_categories)

        opening_hours = p.get("opening_hours") or {}
        # Keep structure as dict; compute_open_status in time_rules expects periods inside.
        if not isinstance(opening_hours, dict):
            opening_hours = {}

        return {
            "place_id": p.get("place_id"),
            "name": p.get("name"),
            "lat": float(loc["lat"]),
            "lng": float(loc["lng"]),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("user_ratings_total"),
            "types": types,
            "opening_hours": opening_hours,
            "business_status": p.get("business_status"),
            "category": category_guess,
            # simple additional signals (can be improved later)
            "is_indoor": True,
            "noise_level": None,
            "tourist_density": 0,
            "local_favorite": False,
        }

    def _guess_category(self, provider_types: List[str], desired_categories: List[str]) -> str:
        t = set(provider_types or [])

        # Strong matches
        if "museum" in t:
            return "museum"
        if "night_club" in t:
            return "nightclub"
        if "movie_theater" in t:
            return "cinema"
        if "performing_arts_theater" in t:
            return "theater"
        if "cafe" in t:
            return "cafe"
        if "bakery" in t:
            return "bakery"
        if "bar" in t:
            # respect desired categories if present
            if "cocktail_bar" in desired_categories:
                return "cocktail_bar"
            if "wine_bar" in desired_categories:
                return "wine_bar"
            if "hotel_bar" in desired_categories:
                return "hotel_bar"
            return "bar"
        if "clothing_store" in t:
            # if vintage requested
            if "vintage" in desired_categories:
                return "vintage"
            return "boutique"
        if "store" in t:
            return "shopping_area"

        # fallback: pick first desired
        return desired_categories[0] if desired_categories else "other"
