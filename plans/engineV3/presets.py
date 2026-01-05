from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass(frozen=True)
class SlotSpec:
    slot_id: str
    title: str
    duration_min: int
    categories: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    role: str = "nice"  # anchor/reward/optional/nice

# ========== INTENT TEMPLATES (EXPANDED V3 + HIGHLIGHTS) ==========

INTENT_TEMPLATES: Dict[str, List[SlotSpec]] = {
    # === HIGHLIGHTS (NEW) ===
    "highlights_tour": [
        SlotSpec("landmark_1", "🏛️ Landmark icónico", 60,
                 categories=["landmark", "monument", "tourist_attraction"],
                 constraints=[], role="reward"),
        SlotSpec("photo_stop_1", "📸 Foto panorámica", 20,
                 categories=["viewpoint", "observation_deck", "photo_spot"],
                 constraints=[], role="nice"),
        SlotSpec("museum", "🎨 Museo principal", 90,
                 categories=["museum", "art_gallery"],
                 constraints=["indoor"], role="reward"),
        SlotSpec("coffee_break", "☕ Café local", 30,
                 categories=["cafe", "bakery"], constraints=["warm"], role="anchor"),
        SlotSpec("landmark_2", "🏰 Segunda atracción", 50,
                 categories=["landmark", "historic_site", "castle"],
                 constraints=[], role="reward"),
        SlotSpec("viewpoint", "🌅 Mirador final", 25,
                 categories=["viewpoint", "scenic_spot"],
                 constraints=[], role="optional"),
    ],
    
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
                 categories=["fine_dining", "upscale_restaurant", "romantic_restaurant"],
                 constraints=["quiet", "indoor"], role="reward"),
        SlotSpec("sunset_spot", "🌅 Spot para atardecer", 30,
                 categories=["viewpoint", "waterfront", "rooftop", "scenic_spot"],
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
    
    # HIGHLIGHTS (NEW)
    "highlights": "highlights_tour",
    "sightseeing": "highlights_tour",
    "tourist": "highlights_tour",
    "landmarks": "highlights_tour",
    
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
    "museum": "culture_alt_late",  # Si museo de noche → cultura alternativa
}

# ========== DYNAMIC SLOT ADJUSTMENT ==========

def adjust_template_for_duration(template_key: str, duration_hours: float, energy_level: str = "medium") -> List[SlotSpec]:
    """
    Ajustar slots del template según duración y energy.
    
    LÓGICA:
    - Short (< 3h): Reduce slots a los esenciales (anchor + reward)
    - Medium (3-6h): Usa template normal
    - Long (> 6h): Expande con slots opcionales
    - High energy: +20% duración por slot
    - Low energy: -20% duración por slot, menos slots totales
    """
    base_slots = INTENT_TEMPLATES.get(template_key, INTENT_TEMPLATES["chill_evening"])
    
    # Calcular cuántos slots caben en la duración
    total_slot_minutes = sum(s.duration_min for s in base_slots)
    avg_slot_duration = total_slot_minutes / len(base_slots) if base_slots else 60
    
    # Ajustar duración según energy
    energy_multipliers = {
        "low": 0.8,      # Más corto, menos intenso
        "medium": 1.0,
        "high": 1.2,     # Más largo, más energético
    }
    multiplier = energy_multipliers.get(energy_level, 1.0)
    
    # Calcular slots ideales para la duración
    duration_minutes = duration_hours * 60
    ideal_slot_count = int(duration_minutes / (avg_slot_duration * multiplier))
    
    # Ajustar según template
    if ideal_slot_count < len(base_slots):
        # Reducir: mantener anchor + reward
        priority_order = ["reward", "anchor", "nice", "optional"]
        sorted_slots = sorted(base_slots, key=lambda s: priority_order.index(s.role) if s.role in priority_order else 99)
        adjusted_slots = sorted_slots[:ideal_slot_count]
    elif ideal_slot_count > len(base_slots):
        # Expandir: duplicar "nice" o "optional" slots si el template lo permite
        adjusted_slots = list(base_slots)
        # Para highlights, agregar más landmarks si hay tiempo
        if template_key == "highlights_tour" and ideal_slot_count > len(base_slots):
            extra_landmark = SlotSpec(
                f"landmark_{ideal_slot_count}", 
                "🏛️ Atracción adicional", 
                50,
                categories=["landmark", "tourist_attraction", "historic_site"],
                constraints=[], 
                role="nice"
            )
            adjusted_slots.insert(-1, extra_landmark)  # Antes del viewpoint final
    else:
        adjusted_slots = list(base_slots)
    
    # Ajustar duraciones individuales según energy
    if multiplier != 1.0:
        adjusted_slots = [
            SlotSpec(
                slot_id=s.slot_id,
                title=s.title,
                duration_min=int(s.duration_min * multiplier),
                categories=s.categories,
                constraints=s.constraints,
                role=s.role
            )
            for s in adjusted_slots
        ]
    
    return adjusted_slots


# ========== TEMPLATE SELECTION LOGIC (UPDATED) ==========

def choose_template(
    intent: str, 
    when_selection: str, 
    hour: int, 
    duration_hours: float = 4.0, 
    energy: str = "medium"
) -> Tuple[str, List[SlotSpec]]:
    """
    Choose template based on intent, when_selection, hour, duration, and energy.
    
    Returns:
        (template_key: str, adjusted_slots: List[SlotSpec])
    
    Rules:
    - Museum at night (hour >= 18 or when_selection == 'tonight') → culture_alt_late
    - Chill late night → chill_evening (works fine)
    - Highlights always uses highlights_tour
    - Adjust slots dynamically based on duration + energy
    """
    intent = (intent or "chill").strip().lower()
    when_selection = (when_selection or "now").strip().lower()

    # Get base template
    base_key = INTENT_TO_TEMPLATE.get(intent, "chill_evening")

    # Fallback rules
    if intent == "museum" and (hour >= 18 or hour <= 6 or when_selection == "tonight"):
        base_key = INTENT_FALLBACK_TEMPLATE["museum"]
    
    # Nightlife should work at any "tonight" time
    if when_selection == "tonight" and intent in ["party", "dance", "club"]:
        base_key = "nightlife"
    
    # Outdoor should avoid very late hours
    if intent in ["outdoor", "walk", "hike"] and (hour >= 21 or hour <= 6):
        base_key = "chill_evening"  # Indoor fallback

    # Adjust slots for duration + energy
    adjusted_slots = adjust_template_for_duration(base_key, duration_hours, energy)
    
    return base_key, adjusted_slots