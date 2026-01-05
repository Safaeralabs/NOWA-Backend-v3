from __future__ import annotations

from typing import Dict, Any, List, Optional, Protocol, Set
import math
import logging

logger = logging.getLogger(__name__)


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
    V3     with OFFICIAL Google Places API type mapping.
    
    Based on: https://developers.google.com/maps/documentation/places/web-service/place-types
    - Table A: Types for filtering and responses
    - Table B: Additional types for responses only
    """

    # ========== OFFICIAL GOOGLE PLACES API TYPE MAPPING ==========
    # Map internal V3 categories -> Google Place types from Table A
    # Reference: https://developers.google.com/maps/documentation/places/web-service/place-types
    
    CATEGORY_TO_GOOGLE = {
        # ==================== FOOD & DRINK (Table A) ====================
        # Restaurants - Specific cuisines
        "restaurant": {"type": "restaurant", "keyword": None},
        "fine_dining": {"type": "fine_dining_restaurant", "keyword": None},
        "fast_food": {"type": "fast_food_restaurant", "keyword": None},
        "casual_dining": {"type": "restaurant", "keyword": "casual"},
        
        # Cuisine-specific
        "mexican_restaurant": {"type": "mexican_restaurant", "keyword": None},
        "italian_restaurant": {"type": "italian_restaurant", "keyword": None},
        "chinese_restaurant": {"type": "chinese_restaurant", "keyword": None},
        "japanese_restaurant": {"type": "japanese_restaurant", "keyword": None},
        "indian_restaurant": {"type": "indian_restaurant", "keyword": None},
        "french_restaurant": {"type": "french_restaurant", "keyword": None},
        "thai_restaurant": {"type": "thai_restaurant", "keyword": None},
        "spanish_restaurant": {"type": "spanish_restaurant", "keyword": None},
        "greek_restaurant": {"type": "greek_restaurant", "keyword": None},
        "korean_restaurant": {"type": "korean_restaurant", "keyword": None},
        "vietnamese_restaurant": {"type": "vietnamese_restaurant", "keyword": None},
        "middle_eastern_restaurant": {"type": "middle_eastern_restaurant", "keyword": None},
        "lebanese_restaurant": {"type": "lebanese_restaurant", "keyword": None},
        "turkish_restaurant": {"type": "turkish_restaurant", "keyword": None},
        "brazilian_restaurant": {"type": "brazilian_restaurant", "keyword": None},
        "indonesian_restaurant": {"type": "indonesian_restaurant", "keyword": None},
        "mediterranean_restaurant": {"type": "mediterranean_restaurant", "keyword": None},
        "african_restaurant": {"type": "african_restaurant", "keyword": None},
        "asian_restaurant": {"type": "asian_restaurant", "keyword": None},
        
        # Restaurant types
        "barbecue_restaurant": {"type": "barbecue_restaurant", "keyword": None},
        "seafood_restaurant": {"type": "seafood_restaurant", "keyword": None},
        "steak_house": {"type": "steak_house", "keyword": None},
        "sushi_restaurant": {"type": "sushi_restaurant", "keyword": None},
        "ramen_restaurant": {"type": "ramen_restaurant", "keyword": None},
        "pizza_restaurant": {"type": "pizza_restaurant", "keyword": None},
        "hamburger_restaurant": {"type": "hamburger_restaurant", "keyword": None},
        "sandwich_shop": {"type": "sandwich_shop", "keyword": None},
        "breakfast_restaurant": {"type": "breakfast_restaurant", "keyword": None},
        "brunch_restaurant": {"type": "brunch_restaurant", "keyword": None},
        "vegan_restaurant": {"type": "vegan_restaurant", "keyword": None},
        "vegetarian_restaurant": {"type": "vegetarian_restaurant", "keyword": None},
        "buffet_restaurant": {"type": "buffet_restaurant", "keyword": None},
        "dessert_restaurant": {"type": "dessert_restaurant", "keyword": None},
        
        # Informal dining
        "diner": {"type": "diner", "keyword": None},
        "food_court": {"type": "food_court", "keyword": None},
        "cafeteria": {"type": "cafeteria", "keyword": None},
        
        # For "local_restaurant" use generic restaurant + "local" keyword
        "local_restaurant": {"type": "restaurant", "keyword": "local"},
        "traditional_food": {"type": "restaurant", "keyword": "traditional"},
        "ethnic_restaurant": {"type": "restaurant", "keyword": "ethnic"},
        "romantic_restaurant": {"type": "restaurant", "keyword": "romantic"},
        "upscale_restaurant": {"type": "fine_dining_restaurant", "keyword": None},
        
        # Bars & Nightlife
        "bar": {"type": "bar", "keyword": None},
        "wine_bar": {"type": "wine_bar", "keyword": None},
        "pub": {"type": "pub", "keyword": None},
        "night_club": {"type": "night_club", "keyword": None},
        "nightclub": {"type": "night_club", "keyword": None},
        "dance_club": {"type": "night_club", "keyword": "dance"},
        "cocktail_bar": {"type": "bar", "keyword": "cocktail"},
        "hotel_bar": {"type": "bar", "keyword": "hotel"},
        "lounge": {"type": "bar", "keyword": "lounge"},
        "speakeasy": {"type": "bar", "keyword": "speakeasy"},
        "jazz_bar": {"type": "bar", "keyword": "jazz"},
        "karaoke": {"type": "karaoke", "keyword": None},
        "comedy_club": {"type": "comedy_club", "keyword": None},
        
        # Cafes & Coffee
        "cafe": {"type": "cafe", "keyword": None},
        "coffee_shop": {"type": "coffee_shop", "keyword": None},
        "tea_house": {"type": "tea_house", "keyword": None},
        "bakery": {"type": "bakery", "keyword": None},
        "ice_cream_shop": {"type": "ice_cream_shop", "keyword": None},
        "dessert_shop": {"type": "dessert_shop", "keyword": None},
        "donut_shop": {"type": "donut_shop", "keyword": None},
        "bagel_shop": {"type": "bagel_shop", "keyword": None},
        "chocolate_shop": {"type": "chocolate_shop", "keyword": None},
        "candy_store": {"type": "candy_store", "keyword": None},
        "juice_shop": {"type": "juice_shop", "keyword": None},
        
        "specialty_coffee": {"type": "coffee_shop", "keyword": "specialty"},
        "roastery": {"type": "coffee_shop", "keyword": "roastery"},
        "third_wave_coffee": {"type": "coffee_shop", "keyword": "third wave"},
        
        # Takeaway & Delivery
        "meal_takeaway": {"type": "meal_takeaway", "keyword": None},
        "meal_delivery": {"type": "meal_delivery", "keyword": None},
        "fast_food_restaurant": {"type": "fast_food_restaurant", "keyword": None},
        "late_food": {"type": "meal_takeaway", "keyword": "late night"},
        "street_food": {"type": "meal_takeaway", "keyword": "street food"},
        "food_truck": {"type": "meal_takeaway", "keyword": "food truck"},
        
        # ==================== ENTERTAINMENT & RECREATION (Table A) ====================
        # Major attractions
        "tourist_attraction": {"type": "tourist_attraction", "keyword": None},
        "amusement_park": {"type": "amusement_park", "keyword": None},
        "amusement_center": {"type": "amusement_center", "keyword": None},
        "water_park": {"type": "water_park", "keyword": None},
        "theme_park": {"type": "amusement_park", "keyword": "theme"},
        "aquarium": {"type": "aquarium", "keyword": None},
        "zoo": {"type": "zoo", "keyword": None},
        "wildlife_park": {"type": "wildlife_park", "keyword": None},
        "wildlife_refuge": {"type": "wildlife_refuge", "keyword": None},
        
        # Landmarks & Views
        "landmark": {"type": "tourist_attraction", "keyword": "landmark"},
        "historical_landmark": {"type": "historical_landmark", "keyword": None},
        "monument": {"type": "monument", "keyword": None},
        "observation_deck": {"type": "observation_deck", "keyword": None},
        "viewpoint": {"type": "observation_deck", "keyword": "viewpoint"},
        "scenic_spot": {"type": "observation_deck", "keyword": "scenic"},
        "photo_spot": {"type": "tourist_attraction", "keyword": "photo"},
        
        # Historical & Cultural
        "historic_site": {"type": "historical_landmark", "keyword": None},
        "historical_place": {"type": "historical_place", "keyword": None},
        "cultural_landmark": {"type": "cultural_landmark", "keyword": None},
        "castle": {"type": "historical_landmark", "keyword": "castle"},
        "sculpture": {"type": "sculpture", "keyword": None},
        
        # Parks & Gardens
        "park": {"type": "park", "keyword": None},
        "national_park": {"type": "national_park", "keyword": None},
        "state_park": {"type": "state_park", "keyword": None},
        "dog_park": {"type": "dog_park", "keyword": None},
        "botanical_garden": {"type": "botanical_garden", "keyword": None},
        "garden": {"type": "garden", "keyword": None},
        "plaza": {"type": "plaza", "keyword": None},
        "picnic_ground": {"type": "picnic_ground", "keyword": None},
        "barbecue_area": {"type": "barbecue_area", "keyword": None},
        
        # Outdoor Activities
        "hiking_area": {"type": "hiking_area", "keyword": None},
        "trail": {"type": "hiking_area", "keyword": "trail"},
        "cycling_park": {"type": "cycling_park", "keyword": None},
        "skateboard_park": {"type": "skateboard_park", "keyword": None},
        "adventure_sports_center": {"type": "adventure_sports_center", "keyword": None},
        "off_roading_area": {"type": "off_roading_area", "keyword": None},
        "beach": {"type": "beach", "keyword": None},
        "waterfront": {"type": "tourist_attraction", "keyword": "waterfront"},
        "marina": {"type": "marina", "keyword": None},
        
        # Entertainment Venues
        "movie_theater": {"type": "movie_theater", "keyword": None},
        "cinema": {"type": "movie_theater", "keyword": None},
        "bowling_alley": {"type": "bowling_alley", "keyword": None},
        "casino": {"type": "casino", "keyword": None},
        "event_venue": {"type": "event_venue", "keyword": None},
        "convention_center": {"type": "convention_center", "keyword": None},
        "wedding_venue": {"type": "wedding_venue", "keyword": None},
        "banquet_hall": {"type": "banquet_hall", "keyword": None},
        "video_arcade": {"type": "video_arcade", "keyword": None},
        "internet_cafe": {"type": "internet_cafe", "keyword": None},
        
        # Rides & Attractions
        "ferris_wheel": {"type": "ferris_wheel", "keyword": None},
        "roller_coaster": {"type": "roller_coaster", "keyword": None},
        
        # ==================== CULTURE (Table A) ====================
        "museum": {"type": "museum", "keyword": None},
        "art_gallery": {"type": "art_gallery", "keyword": None},
        "art_studio": {"type": "art_studio", "keyword": None},
        "performing_arts_theater": {"type": "performing_arts_theater", "keyword": None},
        "theater": {"type": "performing_arts_theater", "keyword": None},
        "opera_house": {"type": "opera_house", "keyword": None},
        "concert_hall": {"type": "concert_hall", "keyword": None},
        "philharmonic_hall": {"type": "philharmonic_hall", "keyword": None},
        "auditorium": {"type": "auditorium", "keyword": None},
        "amphitheatre": {"type": "amphitheatre", "keyword": None},
        "planetarium": {"type": "planetarium", "keyword": None},
        "cultural_center": {"type": "cultural_center", "keyword": None},
        "community_center": {"type": "community_center", "keyword": None},
        "visitor_center": {"type": "visitor_center", "keyword": None},
        
        # ==================== SHOPPING (Table A) ====================
        "shopping_mall": {"type": "shopping_mall", "keyword": None},
        "shopping_area": {"type": "store", "keyword": "shopping street"},
        "market": {"type": "market", "keyword": None},
        "supermarket": {"type": "supermarket", "keyword": None},
        "grocery_store": {"type": "grocery_store", "keyword": None},
        "convenience_store": {"type": "convenience_store", "keyword": None},
        "department_store": {"type": "department_store", "keyword": None},
        "store": {"type": "store", "keyword": None},
        
        # Specialty stores
        "book_store": {"type": "book_store", "keyword": None},
        "clothing_store": {"type": "clothing_store", "keyword": None},
        "shoe_store": {"type": "shoe_store", "keyword": None},
        "jewelry_store": {"type": "jewelry_store", "keyword": None},
        "gift_shop": {"type": "gift_shop", "keyword": None},
        "electronics_store": {"type": "electronics_store", "keyword": None},
        "furniture_store": {"type": "furniture_store", "keyword": None},
        "home_goods_store": {"type": "home_goods_store", "keyword": None},
        "sporting_goods_store": {"type": "sporting_goods_store", "keyword": None},
        
        "boutique": {"type": "clothing_store", "keyword": "boutique"},
        "vintage": {"type": "clothing_store", "keyword": "vintage"},
        "concept_store": {"type": "store", "keyword": "concept"},
        
        # ==================== SPORTS & FITNESS (Table A) ====================
        "gym": {"type": "gym", "keyword": None},
        "fitness_center": {"type": "fitness_center", "keyword": None},
        "yoga_studio": {"type": "yoga_studio", "keyword": None},
        "sports_club": {"type": "sports_club", "keyword": None},
        "sports_complex": {"type": "sports_complex", "keyword": None},
        "stadium": {"type": "stadium", "keyword": None},
        "arena": {"type": "arena", "keyword": None},
        "golf_course": {"type": "golf_course", "keyword": None},
        "swimming_pool": {"type": "swimming_pool", "keyword": None},
        "ice_skating_rink": {"type": "ice_skating_rink", "keyword": None},
        "ski_resort": {"type": "ski_resort", "keyword": None},
        "playground": {"type": "playground", "keyword": None},
        "athletic_field": {"type": "athletic_field", "keyword": None},
        
        # ==================== HEALTH & WELLNESS (Table A) ====================
        "spa": {"type": "spa", "keyword": None},
        "sauna": {"type": "sauna", "keyword": None},
        "massage": {"type": "massage", "keyword": None},
        "wellness_center": {"type": "wellness_center", "keyword": None},
        "beauty_salon": {"type": "beauty_salon", "keyword": None},
        "hair_salon": {"type": "hair_salon", "keyword": None},
        "nail_salon": {"type": "nail_salon", "keyword": None},
        "barber_shop": {"type": "barber_shop", "keyword": None},
        
        # ==================== LODGING (Table A) ====================
        "hotel": {"type": "hotel", "keyword": None},
        "lodging": {"type": "lodging", "keyword": None},
        "resort_hotel": {"type": "resort_hotel", "keyword": None},
        "motel": {"type": "motel", "keyword": None},
        "hostel": {"type": "hostel", "keyword": None},
        "bed_and_breakfast": {"type": "bed_and_breakfast", "keyword": None},
        "guest_house": {"type": "guest_house", "keyword": None},
        "campground": {"type": "campground", "keyword": None},
        
        # ==================== SERVICES (Table A) ====================
        "travel_agency": {"type": "travel_agency", "keyword": None},
        "tour_agency": {"type": "tour_agency", "keyword": None},
        "tourist_information_center": {"type": "tourist_information_center", "keyword": None},
        
        # ==================== PLACES OF WORSHIP (Table A) ====================
        "church": {"type": "church", "keyword": None},
        "mosque": {"type": "mosque", "keyword": None},
        "synagogue": {"type": "synagogue", "keyword": None},
        "hindu_temple": {"type": "hindu_temple", "keyword": None},
        
        # ==================== TRANSPORTATION (Table A) ====================
        "airport": {"type": "airport", "keyword": None},
        "train_station": {"type": "train_station", "keyword": None},
        "bus_station": {"type": "bus_station", "keyword": None},
        "subway_station": {"type": "subway_station", "keyword": None},
        "transit_station": {"type": "transit_station", "keyword": None},
        "parking": {"type": "parking", "keyword": None},
        "gas_station": {"type": "gas_station", "keyword": None},
    }
    
    # ========== ALL GOOGLE TYPES FOR RECOGNITION (Table A + Table B) ==========
    # These are ALL the types Google can return - used for _guess_category matching
    GOOGLE_TYPES_TABLE_A: Set[str] = {
        # Food & Drink
        "restaurant", "fine_dining_restaurant", "fast_food_restaurant",
        "mexican_restaurant", "italian_restaurant", "chinese_restaurant", "japanese_restaurant",
        "indian_restaurant", "french_restaurant", "thai_restaurant", "spanish_restaurant",
        "greek_restaurant", "korean_restaurant", "vietnamese_restaurant", "middle_eastern_restaurant",
        "lebanese_restaurant", "turkish_restaurant", "brazilian_restaurant", "indonesian_restaurant",
        "mediterranean_restaurant", "african_restaurant", "asian_restaurant", "american_restaurant",
        "barbecue_restaurant", "seafood_restaurant", "steak_house", "sushi_restaurant",
        "ramen_restaurant", "pizza_restaurant", "hamburger_restaurant", "sandwich_shop",
        "breakfast_restaurant", "brunch_restaurant", "vegan_restaurant", "vegetarian_restaurant",
        "buffet_restaurant", "dessert_restaurant", "diner", "food_court", "cafeteria",
        "bar", "wine_bar", "pub", "night_club", "karaoke", "comedy_club",
        "cafe", "coffee_shop", "tea_house", "bakery", "ice_cream_shop", "dessert_shop",
        "donut_shop", "bagel_shop", "chocolate_shop", "candy_store", "juice_shop",
        "meal_takeaway", "meal_delivery",
        # Entertainment
        "tourist_attraction", "amusement_park", "amusement_center", "water_park",
        "aquarium", "zoo", "wildlife_park", "wildlife_refuge",
        "historical_landmark", "monument", "observation_deck", "historical_place", "cultural_landmark", "sculpture",
        "park", "national_park", "state_park", "dog_park", "botanical_garden", "garden", "plaza",
        "picnic_ground", "barbecue_area", "hiking_area", "cycling_park", "skateboard_park",
        "adventure_sports_center", "off_roading_area", "beach", "marina",
        "movie_theater", "bowling_alley", "casino", "event_venue", "convention_center",
        "wedding_venue", "banquet_hall", "video_arcade", "internet_cafe",
        "ferris_wheel", "roller_coaster",
        # Culture
        "museum", "art_gallery", "art_studio", "performing_arts_theater", "opera_house",
        "concert_hall", "philharmonic_hall", "auditorium", "amphitheatre", "planetarium",
        "cultural_center", "community_center", "visitor_center",
        # Shopping
        "shopping_mall", "market", "supermarket", "grocery_store", "convenience_store",
        "department_store", "store", "book_store", "clothing_store", "shoe_store",
        "jewelry_store", "gift_shop", "electronics_store", "furniture_store",
        "home_goods_store", "sporting_goods_store",
        # Sports
        "gym", "fitness_center", "yoga_studio", "sports_club", "sports_complex",
        "stadium", "arena", "golf_course", "swimming_pool", "ice_skating_rink",
        "ski_resort", "playground", "athletic_field",
        # Health & Wellness
        "spa", "sauna", "massage", "wellness_center", "beauty_salon", "hair_salon",
        "nail_salon", "barber_shop",
        # Lodging
        "hotel", "lodging", "resort_hotel", "motel", "hostel", "bed_and_breakfast",
        "guest_house", "campground",
        # Services
        "travel_agency", "tour_agency", "tourist_information_center",
        # Places of Worship
        "church", "mosque", "synagogue", "hindu_temple",
        # Transportation
        "airport", "train_station", "bus_station", "subway_station", "transit_station",
        "parking", "gas_station",
    }
    
    # Table B types (response-only, cannot be used for filtering)
    GOOGLE_TYPES_TABLE_B: Set[str] = {
        "establishment", "point_of_interest", "food", "place_of_worship",
        "landmark", "natural_feature", "neighborhood", "political",
        "locality", "sublocality", "route", "street_address", "premise",
        "administrative_area_level_1", "administrative_area_level_2",
        "administrative_area_level_3", "administrative_area_level_4",
        "administrative_area_level_5", "country", "postal_code",
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
        Returns normalized place dicts with STRICT category validation.
        Only includes places that match requested categories based on Google's official types.
        """
        seen = set()
        normalized: List[Dict[str, Any]] = []

        # Limit number of category queries (cost control)
        for cat in (categories or [])[:6]:
            mapping = self.CATEGORY_TO_GOOGLE.get(cat)
            if not mapping:
                logger.warning(f"    Unknown category '{cat}' - skipping")
                continue
                
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

            # Diagnostic logging
            logger.info(f"    Google search for '{cat}' (type={gtype}, keyword={keyword}): {len(raw)} results")
            for i, p in enumerate(raw[:3]):  # Log first 3
                logger.info(f"  {i+1}. {p.get('name')} - types: {p.get('types')}")

            for p in raw:
                pid = p.get("place_id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                n = self._normalize_google_place(p, preferred_categories=categories)
                if n:  # Only include if category is valid
                    normalized.append(n)

        logger.info(f"   Total normalized candidates: {len(normalized)} (from {len(seen)} raw results)")

        # Optional enrichment
        if enrich_opening_hours:
            for i in range(min(enrich_limit, len(normalized))):
                pid = normalized[i]["place_id"]
                details = self.places.details(
                    place_id=pid,
                    fields=[
                        "place_id", "name", "geometry/location", "types",
                        "rating", "user_ratings_total", "opening_hours", "business_status",
                    ],
                    language=self.language,
                    region=self.region,
                )
                if details:
                    merged = self._normalize_google_place(details, preferred_categories=categories)
                    if merged:
                        normalized[i]["opening_hours"] = merged.get("opening_hours") or normalized[i].get("opening_hours") or {}
                        normalized[i]["types"] = merged.get("types") or normalized[i].get("types") or []
                        normalized[i]["business_status"] = merged.get("business_status") or normalized[i].get("business_status")
                        normalized[i]["category"] = merged.get("category") or normalized[i].get("category")

        return normalized

    def get_weather(self, *, user_location: Dict[str, float]) -> Dict[str, Any]:
        return self.weather.snapshot(location=user_location)

    def get_legs(self, *, stops: List[Dict[str, Any]], mode: str = "walking") -> List[Dict[str, Any]]:
        if not self.directions or len(stops) < 2:
            return []
        return self.directions.legs(stops=stops, mode=mode)

    # --------------------
    # Normalization helpers
    # --------------------
    def _normalize_google_place(self, p: Dict[str, Any], preferred_categories: List[str]) -> Optional[Dict[str, Any]]:
        """
        Normalize Google place with STRICT category filtering based on official Google types.
        Returns None if place doesn't match any requested category.
        """
        geom = p.get("geometry", {}) if isinstance(p.get("geometry"), dict) else {}
        loc = geom.get("location") if isinstance(geom.get("location"), dict) else None
        if not loc:
            loc = p.get("location") if isinstance(p.get("location"), dict) else None
        if not loc or "lat" not in loc or "lng" not in loc:
            return None

        types = p.get("types") or []
        category_guess = self._guess_category(types, preferred_categories)
        
        #    STRICT FILTER: Only include if category matches request
        if category_guess == "other":
            logger.debug(f"    Filtered '{p.get('name')}' - no valid category match (types: {types})")
            return None

        opening_hours = p.get("opening_hours") or {}
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
            "is_indoor": True,
            "noise_level": None,
            "tourist_density": 0,
            "local_favorite": False,
        }

    def _guess_category(self, provider_types: List[str], desired_categories: List[str]) -> str:
        """
        Guess category from Google types using OFFICIAL Google Places API types.
        
        Strategy:
        1. Check for exact matches with Table A types
        2. Check for exact matches with Table B generic types
        3. Return "other" if no match (place will be filtered)
        
        Reference: https://developers.google.com/maps/documentation/places/web-service/place-types
        """
        t = set(provider_types or [])
        
        # ========== EXACT MATCHING WITH GOOGLE OFFICIAL TYPES ==========
        
        # Check Table A types (specific categories)
        table_a_matches = t & self.GOOGLE_TYPES_TABLE_A
        if table_a_matches:
            # Priority order for matching
            # 1. Exact match with desired categories
            for desired in desired_categories:
                # Check if any Google type matches our category mapping
                mapping = self.CATEGORY_TO_GOOGLE.get(desired, {})
                expected_type = mapping.get("type")
                if expected_type in table_a_matches:
                    return desired
            
            # 2. Use the most specific Google type available
            # Restaurant hierarchy
            if "fine_dining_restaurant" in table_a_matches:
                return "fine_dining"
            if "fast_food_restaurant" in table_a_matches:
                return "fast_food"
            # Specific cuisines
            for cuisine in ["mexican_restaurant", "italian_restaurant", "chinese_restaurant",
                           "japanese_restaurant", "indian_restaurant", "french_restaurant",
                           "thai_restaurant", "spanish_restaurant", "korean_restaurant",
                           "vietnamese_restaurant", "seafood_restaurant", "steak_house",
                           "sushi_restaurant", "pizza_restaurant"]:
                if cuisine in table_a_matches:
                    return cuisine.replace("_", "_")
            if "restaurant" in table_a_matches:
                return "restaurant"
            
            # Bars & Nightlife
            if "night_club" in table_a_matches:
                return "nightclub"
            if "wine_bar" in table_a_matches:
                return "wine_bar"
            if "pub" in table_a_matches:
                return "pub"
            if "bar" in table_a_matches:
                return "bar"
            
            # Cafes & Coffee
            if "coffee_shop" in table_a_matches:
                return "coffee_shop"
            if "cafe" in table_a_matches:
                return "cafe"
            if "tea_house" in table_a_matches:
                return "tea_house"
            if "bakery" in table_a_matches:
                return "bakery"
            if "ice_cream_shop" in table_a_matches:
                return "ice_cream_shop"
            
            # Takeaway
            if "meal_takeaway" in table_a_matches or "meal_delivery" in table_a_matches:
                return "meal_takeaway"
            
            # Landmarks & Views
            if "monument" in table_a_matches:
                return "monument"
            if "historical_landmark" in table_a_matches:
                return "landmark"
            if "observation_deck" in table_a_matches:
                return "viewpoint"
            if "historical_place" in table_a_matches:
                return "historic_site"
            if "cultural_landmark" in table_a_matches:
                return "landmark"
            
            # Culture
            if "museum" in table_a_matches:
                return "museum"
            if "art_gallery" in table_a_matches:
                return "art_gallery"
            if "performing_arts_theater" in table_a_matches:
                return "theater"
            
            # Parks
            if "national_park" in table_a_matches:
                return "national_park"
            if "dog_park" in table_a_matches:
                return "dog_park"
            if "botanical_garden" in table_a_matches:
                return "botanical_garden"
            if "park" in table_a_matches:
                return "park"
            
            # Entertainment
            if "amusement_park" in table_a_matches:
                return "amusement_park"
            if "water_park" in table_a_matches:
                return "water_park"
            if "aquarium" in table_a_matches:
                return "aquarium"
            if "zoo" in table_a_matches:
                return "zoo"
            if "movie_theater" in table_a_matches:
                return "cinema"
            if "casino" in table_a_matches:
                return "casino"
            
            # Shopping
            if "shopping_mall" in table_a_matches:
                return "shopping_mall"
            if "market" in table_a_matches:
                return "market"
            if "supermarket" in table_a_matches:
                return "supermarket"
            if "store" in table_a_matches:
                return "store"
            
            # Sports
            if "gym" in table_a_matches or "fitness_center" in table_a_matches:
                return "gym"
            if "stadium" in table_a_matches:
                return "stadium"
            
            # Lodging
            if "hotel" in table_a_matches or "lodging" in table_a_matches:
                return "hotel"
            
            # Use first Table A match as fallback
            return list(table_a_matches)[0]
        
        # Check Table B generic types
        if "tourist_attraction" in t or "point_of_interest" in t:
            # Only accept if specifically requested
            if "tourist_attraction" in desired_categories:
                return "tourist_attraction"
            if "landmark" in desired_categories:
                return "landmark"
            if "viewpoint" in desired_categories:
                return "viewpoint"
        
        # ========== NO VALID MATCH - FILTER THIS PLACE ==========
        return "other"