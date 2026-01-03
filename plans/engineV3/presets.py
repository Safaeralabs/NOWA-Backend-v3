from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass(frozen=True)
class SlotSpec:
    slot_id: str
    title: str
    duration_min: int
    categories: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    role: str = "nice"  # anchor/reward/optional/nice

# ========== INTENT TEMPLATES (EXPANDED V3) ==========

INTENT_TEMPLATES: Dict[str, List[SlotSpec]] = {
    # === CHILL & DRINKS ===
    "chill_evening": [
        SlotSpec("drinks", "🍸 Bar acogedor (indoor)", 75,
                 categories=["bar", "cocktail_bar", "wine_bar", "hotel_bar"],
                 constraints=["indoor", "quiet"], role="anchor"),
        SlotSpec("late_food", "🌭 Snack caliente", 40,
                 categories=["late_food", "fast_food"],
                 constraints=["quick"], role="reward"),
    ],
    
    # === SHOPPING ===
    "shop_local": [
        SlotSpec("shopping_cluster", "🛍️ Zona de shopping local", 90,
                 categories=["shopping_area", "market", "boutique", "concept_store", "vintage"],
                 constraints=[], role="anchor"),
        SlotSpec("coffee_break", "☕ Coffee break cercano", 25,
                 categories=["cafe", "bakery"], constraints=["warm"], role="nice"),
        SlotSpec("photo_stop", "📸 Spot fotogénico cercano", 25,
                 categories=["photo_spot", "viewpoint", "street_art"], constraints=[], role="optional"),
    ],
    
    # === CULTURE ===
    "museum_day": [
        SlotSpec("museum", "🏛️ Museo imperdible", 110,
                 categories=["museum"], constraints=["indoor"], role="reward"),
        SlotSpec("coffee_break", "☕ Café cercano", 30,
                 categories=["cafe", "bakery"], constraints=["warm"], role="anchor"),
    ],
    
    "culture_alt_late": [
        SlotSpec("culture_alt", "🎭 Cultura nocturna (indoor, abierto tarde)", 75,
                 categories=["cultural_bar", "jazz_bar", "cinema", "theater"],
                 constraints=["indoor", "quiet"], role="reward"),
        SlotSpec("late_coffee", "🍰 Postre / té caliente", 35,
                 categories=["dessert", "cafe"], constraints=["warm"], role="anchor"),
    ],
    
    # === FOOD EXPERIENCES ===
    "food_tour": [
        SlotSpec("street_food", "🌮 Street food auténtico", 35,
                 categories=["street_food", "food_truck", "market_stall"],
                 role="anchor"),
        SlotSpec("local_restaurant", "🍽️ Restaurante local típico", 75,
                 categories=["local_restaurant", "traditional_food", "ethnic_restaurant"],
                 role="reward"),
        SlotSpec("dessert_spot", "🍰 Postre típico", 30,
                 categories=["dessert", "bakery", "ice_cream", "patisserie"],
                 role="nice"),
    ],
    
    "coffee_hop": [
        SlotSpec("specialty_coffee_1", "☕ Café de especialidad", 40,
                 categories=["specialty_coffee", "roastery", "third_wave_coffee"],
                 constraints=["indoor", "quiet"], role="anchor"),
        SlotSpec("pastry", "🥐 Pastelería artesanal", 30,
                 categories=["bakery", "patisserie"], role="nice"),
        SlotSpec("specialty_coffee_2", "☕ Segunda parada café", 35,
                 categories=["cafe", "specialty_coffee"], role="optional"),
    ],
    
    # === NIGHTLIFE ===
    "nightlife": [
        SlotSpec("pre_drinks", "🍸 Pre-drinks bar", 60,
                 categories=["cocktail_bar", "wine_bar", "rooftop_bar"],
                 constraints=["indoor"], role="anchor"),
        SlotSpec("club", "💃 Club/discoteca", 120,
                 categories=["nightclub", "dance_club"],
                 role="reward"),
        SlotSpec("late_night_food", "🌭 Comida post-club", 30,
                 categories=["late_food", "kebab", "pizza", "fast_food"],
                 role="nice"),
    ],
    
    # === OUTDOOR & ACTIVE ===
    "outdoor_active": [
        SlotSpec("scenic_walk", "🚶 Caminata escénica", 50,
                 categories=["park", "trail", "waterfront"],
                 constraints=["outdoor"], role="anchor"),
        SlotSpec("viewpoint", "📸 Mirador panorámico", 25,
                 categories=["viewpoint", "observation_deck"],
                 constraints=["outdoor"], role="reward"),
        SlotSpec("outdoor_cafe", "☕ Café con terraza", 35,
                 categories=["cafe"], 
                 constraints=["prefer_terrace"], role="nice"),
    ],
    
    # === ROMANTIC DATE ===
    "romantic_date": [
        SlotSpec("romantic_dinner", "🌹 Cena romántica", 90,
                 categories=["romantic_restaurant", "fine_dining", "upscale_restaurant"],
                 constraints=["quiet", "indoor"], role="reward"),
        SlotSpec("sunset_spot", "🌅 Spot para atardecer", 30,
                 categories=["viewpoint", "waterfront", "rooftop"],
                 constraints=["outdoor"], role="anchor"),
        SlotSpec("cocktail_lounge", "🍸 Lounge íntimo", 60,
                 categories=["cocktail_bar", "lounge", "speakeasy"],
                 constraints=["quiet", "indoor"], role="nice"),
    ],
}

# ========== INTENT MAPPING ==========

INTENT_TO_TEMPLATE = {
    # Core intents
    "chill": "chill_evening",
    "drink": "chill_evening",
    "drinks": "chill_evening",
    
    "shop_local": "shop_local",
    "shopping": "shop_local",
    "shop": "shop_local",
    
    "museum": "museum_day",
    "culture": "museum_day",
    "art": "museum_day",
    
    # Food experiences
    "food": "food_tour",
    "food_tour": "food_tour",
    "eat": "food_tour",
    "foodie": "food_tour",
    
    "coffee": "coffee_hop",
    "coffee_hop": "coffee_hop",
    "cafe": "coffee_hop",
    
    # Nightlife
    "nightlife": "nightlife",
    "party": "nightlife",
    "dance": "nightlife",
    "club": "nightlife",
    "night": "nightlife",
    
    # Outdoor
    "outdoor": "outdoor_active",
    "walk": "outdoor_active",
    "hike": "outdoor_active",
    "nature": "outdoor_active",
    "active": "outdoor_active",
    
    # Romantic
    "date": "romantic_date",
    "romantic": "romantic_date",
    "romance": "romantic_date",
}

# ========== FALLBACK TEMPLATES ==========

INTENT_FALLBACK_TEMPLATE = {
    "museum": "culture_alt_late",  # Si museo de noche -> cultura alternativa
}

# ========== TEMPLATE SELECTION LOGIC ==========

def choose_template(intent: str, when_selection: str, hour: int) -> str:
    """
    Choose template based on intent, when_selection, and hour.
    
    Rules:
    - Museum at night (hour >= 18 or when_selection == 'tonight') → culture_alt_late
    - Chill late night → chill_evening (works fine)
    - Default to intent mapping, fallback to chill_evening
    """
    intent = (intent or "chill").strip().lower()
    when_selection = (when_selection or "now").strip().lower()

    # Get base template
    base = INTENT_TO_TEMPLATE.get(intent, "chill_evening")

    # Fallback rules
    if intent == "museum" and (hour >= 18 or hour <= 6 or when_selection == "tonight"):
        return INTENT_FALLBACK_TEMPLATE["museum"]
    
    # Nightlife should work at any "tonight" time
    if when_selection == "tonight" and intent in ["party", "dance", "club"]:
        return "nightlife"
    
    # Outdoor should avoid very late hours
    if intent in ["outdoor", "walk", "hike"] and (hour >= 21 or hour <= 6):
        return "chill_evening"  # Indoor fallback

    return base