from typing import Dict, Any, List, Optional, Protocol, Tuple
import math

class PlacesProvider(Protocol):
    def search(self, *, city: str, location: Dict[str, float], radius_m: int, query: str | None, types: List[str]) -> List[Dict[str, Any]]: ...
    def details(self, *, place_id: str) -> Dict[str, Any]: ...

class DirectionsProvider(Protocol):
    def legs(self, *, stops: List[Dict[str, Any]], mode: str = "walking") -> List[Dict[str, Any]]: ...

class WeatherProvider(Protocol):
    def snapshot(self, *, location: Dict[str, float]) -> Dict[str, Any]: ...

def haversine_m(a: Dict[str, float], b: Dict[str, float]) -> float:
    # simple distance in meters
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lng"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lng"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    r = 6371000
    x = (math.sin(dlat/2)**2 +
         math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)
    return 2*r*math.asin(min(1, math.sqrt(x)))

class Providers:
    def __init__(self, places: PlacesProvider, directions: DirectionsProvider | None = None, weather: WeatherProvider | None = None):
        self.places = places
        self.directions = directions
        self.weather = weather

    # Map internal categories to provider "types"/queries
    CATEGORY_TO_TYPES = {
        "museum": ["museum"],
        "bar": ["bar"],
        "cocktail_bar": ["bar"],
        "wine_bar": ["bar"],
        "hotel_bar": ["bar"],
        "nightclub": ["night_club"],
        "cafe": ["cafe"],
        "bakery": ["bakery"],
        "dessert": ["bakery", "cafe"],
        "fast_food": ["meal_takeaway", "restaurant"],
        "late_food": ["meal_takeaway", "restaurant"],
        "market": ["shopping_mall", "store"],  # provider-limited; refine later
        "boutique": ["clothing_store", "store"],
        "concept_store": ["store"],
        "vintage": ["clothing_store", "store"],
        "shopping_area": ["store"],
        "cinema": ["movie_theater"],
        "theater": ["performing_arts_theater"],
        "jazz_bar": ["bar"],
        "cultural_bar": ["bar"],
        "photo_spot": ["tourist_attraction", "park"],
        "viewpoint": ["tourist_attraction"],
        "street_art": ["tourist_attraction"],
    }

    def fetch_candidates(self, *, city: str, user_location: Dict[str, float], categories: List[str], radius_m: int = 2000) -> List[Dict[str, Any]]:
        # Flatten provider types
        types: List[str] = []
        for c in categories:
            types.extend(self.CATEGORY_TO_TYPES.get(c, []))
        # Deduplicate
        types = list(dict.fromkeys(types)) or ["tourist_attraction"]

        raw = self.places.search(city=city, location=user_location, radius_m=radius_m, query=None, types=types)

        # Normalize
        out: List[Dict[str, Any]] = []
        for p in raw:
            loc = p.get("geometry", {}).get("location") or p.get("location") or {}
            lat = loc.get("lat")
            lng = loc.get("lng")
            if lat is None or lng is None:
                continue

            # Heurística: mapear provider types -> nuestra category
            provider_types = p.get("types") or []
            category_guess = self._guess_category(provider_types, categories)

            out.append({
                "place_id": p.get("place_id"),
                "name": p.get("name"),
                "lat": float(lat),
                "lng": float(lng),
                "rating": p.get("rating"),
                "user_ratings_total": p.get("user_ratings_total"),
                "types": provider_types,
                "opening_hours": p.get("opening_hours") or {},
                "category": category_guess,
                # opcionales enriquecidos:
                "is_indoor": True,  # refine later by type
                "noise_level": None,
                "tourist_density": 0,
                "local_favorite": False,
            })
        return out

    def _guess_category(self, provider_types: List[str], desired_categories: List[str]) -> str:
        # naive: if museum type -> museum, if bar -> bar, etc.
        t = set(provider_types or [])
        if "museum" in t:
            return "museum"
        if "night_club" in t:
            return "nightclub"
        if "bar" in t:
            # keep category if slot expects cocktail/wine; engine can accept bar
            if "cocktail_bar" in desired_categories:
                return "cocktail_bar"
            if "wine_bar" in desired_categories:
                return "wine_bar"
            return "bar"
        if "cafe" in t:
            return "cafe"
        if "bakery" in t:
            return "bakery"
        if "movie_theater" in t:
            return "cinema"
        if "performing_arts_theater" in t:
            return "theater"
        if "clothing_store" in t:
            return "boutique"
        if "shopping_mall" in t or "store" in t:
            return "shopping_area"
        return desired_categories[0] if desired_categories else "other"

    def distance_m(self, *, user_location: Dict[str, float], place: Dict[str, Any]) -> float:
        return haversine_m(user_location, {"lat": place["lat"], "lng": place["lng"]})

    def get_legs(self, *, stops: List[Dict[str, Any]], mode: str = "walking") -> List[Dict[str, Any]]:
        if not self.directions or len(stops) < 2:
            return []
        return self.directions.legs(stops=stops, mode=mode)

    def get_weather(self, *, user_location: Dict[str, float]) -> Dict[str, Any]:
        if not self.weather:
            return {}
        return self.weather.snapshot(location=user_location)
