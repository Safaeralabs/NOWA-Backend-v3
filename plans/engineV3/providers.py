"""
V3 Providers wrapper with enhanced error handling and logging.
"""
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def safe_cache_incr(key, delta=1, default=0):
    """
    Safely increment cache key (creates if doesn't exist).
    Django's safe_cache_incr() fails if key doesn't exist.
    """
    from django.core.cache import cache
    try:
        return safe_cache_incr(key, delta)
    except ValueError:
        # Key doesn't exist, initialize and return
        cache.set(key, default + delta, None)
        return default + delta


@dataclass
class PlacesProvider(Protocol):
    """Protocol for places providers (Google, Yelp, etc)"""
    def nearby_search(
        self,
        location: Dict[str, float],
        radius: int,
        keyword: Optional[str] = None,
        type_filter: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ...
    
    def place_details(
        self,
        place_id: str,
        fields: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        ...


@dataclass
class WeatherProvider(Protocol):
    """Protocol for weather providers"""
    def get_weather(
        self,
        location: Dict[str, float],
        units: str = "metric"
    ) -> Dict[str, Any]:
        ...


@dataclass
class DirectionsProvider(Protocol):
    """Protocol for directions providers"""
    def get_directions(
        self,
        origin: tuple,
        destination: tuple,
        mode: str = "walk",
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        ...


class Providers:
    """
    V3 Providers aggregator with enhanced error handling.
    
    Features:
    - Unified interface for Google Places, Weather, Directions
    - Built-in error handling and logging
    - Metrics tracking
    - Opening hours enrichment with configurable limit
    """
    
    def __init__(
        self,
        places: PlacesProvider,
        weather: WeatherProvider,
        directions: Optional[DirectionsProvider] = None,
        language: str = "es",
        region: Optional[str] = None
    ):
        self.places = places
        self.weather_provider = weather
        self.directions = directions
        self.language = language
        self.region = region

    def fetch_candidates(
        self,
        *,
        city: str,
        user_location: Dict[str, float],
        categories: List[str],
        radius_m: int = 2500,
        enrich_opening_hours: bool = False,
        enrich_limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Fetch candidates from Google Places.
        
        Args:
            city: City name (for logging)
            user_location: {lat, lng}
            categories: List of category strings
            radius_m: Search radius in meters
            enrich_opening_hours: If True, fetch opening_hours.periods (requires Details API)
            enrich_limit: Max places to enrich (to control API cost)
        
        Returns:
            List of place dicts with optional opening_hours enrichment
        """
        from django.core.cache import cache
        
        # Build cache key
        cats_str = "-".join(sorted(categories[:3]))
        cache_key = f"candidates:v3:{city}:{cats_str}:{radius_m}"
        
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"    Cache HIT: {cache_key}")
            return cached
        
        logger.info(f"    Fetching candidates: categories={categories}, radius={radius_m}m")
        
        try:
            # Call Google Places Nearby Search
            results = []
            for category in categories:
                try:
                    nearby = self.places.nearby_search(
                        location=user_location,
                        radius=radius_m,
                        keyword=category,
                        language=self.language
                    )
                    results.extend(nearby)
                    logger.info(f"    Category '{category}': {len(nearby)} results")
                except Exception as e:
                    logger.warning(f"    Nearby search failed for category '{category}': {e}")
                    safe_cache_incr('metrics:places_api_failures', 1)
                    continue
            
            # Deduplicate by place_id
            seen = set()
            unique = []
            for r in results:
                pid = r.get("place_id")
                if pid and pid not in seen:
                    seen.add(pid)
                    unique.append(r)
            
            logger.info(f"    Total unique candidates: {len(unique)}")
            
            # Enrich opening hours (if requested)
            if enrich_opening_hours:
                logger.info(f"    Enriching opening hours for top {enrich_limit} places...")
                unique = self._enrich_opening_hours(unique[:enrich_limit])
            
            # Cache results (15 minutes for non-enriched, 1 hour for enriched)
            ttl = 3600 if enrich_opening_hours else 900
            cache.set(cache_key, unique, ttl)
            
            # Track metrics
            safe_cache_incr('metrics:places_api_calls', len(categories))
            if enrich_opening_hours:
                safe_cache_incr('metrics:places_details_calls', min(len(unique), enrich_limit))
            
            return unique
            
        except Exception as e:
            logger.error(f"    fetch_candidates failed: {e}", exc_info=True)
            safe_cache_incr('metrics:places_api_failures', 1)
            return []

    def _enrich_opening_hours(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich places with opening_hours.periods from Details API.
        
        This is critical for compute_open_status() to work properly.
        """
        enriched = []
        
        for place in places:
            place_id = place.get("place_id")
            if not place_id:
                enriched.append(place)
                continue
            
            try:
                details = self.places.place_details(
                    place_id=place_id,
                    fields=["opening_hours", "business_status"],
                    language=self.language
                )
                
                # Merge opening_hours into place
                if details.get("opening_hours"):
                    place["opening_hours"] = details["opening_hours"]
                
                if details.get("business_status"):
                    place["business_status"] = details["business_status"]
                
                enriched.append(place)
                
            except Exception as e:
                logger.warning(f"    Failed to enrich place {place_id}: {e}")
                enriched.append(place)  # Keep original without enrichment
        
        logger.info(f"    Enriched {len(enriched)} places with opening hours")
        return enriched

    def get_weather(self, *, user_location: Dict[str, float]) -> Dict[str, Any]:
        """
        Fetch weather with fallback.
        
        Returns:
            Weather dict with temp, feels_like, condition, is_raining, confidence
        """
        from django.core.cache import cache
        
        lat = user_location.get("lat")
        lng = user_location.get("lng")
        
        cache_key = f"weather:v3:{lat:.2f}:{lng:.2f}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"    Weather cache HIT")
            return cached
        
        logger.info(f"   Fetching weather for ({lat:.4f}, {lng:.4f})...")
        
        try:
            weather = self.weather_provider.get_weather(
                location=user_location,
                units="metric"
            )
            
            # Validate required fields
            if weather.get("temp") is None:
                logger.warning("    Weather API returned no temperature, using fallback")
                weather = self._weather_fallback()
            else:
                weather["confidence"] = "high"
            
            # Cache for 30 minutes
            cache.set(cache_key, weather, 1800)
            
            # Track metrics
            safe_cache_incr('metrics:weather_api_calls', 1)
            
            logger.info(f"    Weather: {weather.get('temp')}°C, {weather.get('condition')}")
            return weather
            
        except Exception as e:
            logger.error(f"    Weather API failed: {e}", exc_info=True)
            safe_cache_incr('metrics:weather_api_failures', 1)
            return self._weather_fallback()

    def _weather_fallback(self) -> Dict[str, Any]:
        """Fallback weather when API fails"""
        import datetime
        now = datetime.datetime.now()
        month = now.month
        
        # Seasonal defaults
        if month in [12, 1, 2]:  # Winter
            temp = 8
            condition = "cloudy"
        elif month in [3, 4, 5]:  # Spring
            temp = 15
            condition = "partly cloudy"
        elif month in [6, 7, 8]:  # Summer
            temp = 25
            condition = "clear"
        else:  # Fall
            temp = 12
            condition = "cloudy"
        
        logger.warning(f"    Using seasonal fallback weather: {temp}°C, {condition}")
        
        return {
            "temp": temp,
            "feels_like": temp,
            "condition": condition,
            "is_raining": False,
            "is_snowing": False,
            "precip_prob": 0,
            "confidence": "low",
            "source": "fallback"
        }

    def distance_m(self, *, user_location: Dict[str, float], place: Dict[str, Any]) -> int:
        """
        Calculate distance in meters using Haversine formula.
        
        Args:
            user_location: {lat, lng}
            place: Place dict with geometry.location.lat/lng
        
        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Extract coordinates
        lat1 = user_location.get("lat")
        lng1 = user_location.get("lng")
        
        geom = place.get("geometry") or {}
        loc = geom.get("location") or {}
        lat2 = loc.get("lat")
        lng2 = loc.get("lng")
        
        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            logger.warning(f"    Missing coordinates for distance calculation")
            return 999999
        
        # Haversine formula
        R = 6371000  # Earth radius in meters
        
        phi1 = radians(lat1)
        phi2 = radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lng2 - lng1)
        
        a = sin(delta_phi/2)**2 + cos(phi1) * cos(phi2) * sin(delta_lambda/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        return int(distance)