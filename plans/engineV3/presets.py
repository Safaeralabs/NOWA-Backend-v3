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

# Categorías canónicas internas V3 (no dependas de Google types directamente)
# Las mapearás en providers.py
INTENT_TEMPLATES: Dict[str, List[SlotSpec]] = {
    # Chill "tonight" (tarde/noche)
    "chill_evening": [
        SlotSpec("drinks", "🍸 Bar acogedor (indoor)", 75,
                 categories=["bar", "cocktail_bar", "wine_bar", "hotel_bar"],
                 constraints=["indoor", "quiet"], role="anchor"),
        SlotSpec("late_food", "🌭 Snack caliente", 40,
                 categories=["late_food", "fast_food"],
                 constraints=["quick"], role="reward"),
    ],
    # Shopping local
    "shop_local": [
        SlotSpec("shopping_cluster", "🛍️ Zona de shopping local", 90,
                 categories=["shopping_area", "market", "boutique", "concept_store", "vintage"],
                 constraints=[], role="anchor"),
        SlotSpec("coffee_break", "☕ Coffee break cercano", 25,
                 categories=["cafe", "bakery"], constraints=["warm"], role="nice"),
        SlotSpec("photo_stop", "📸 Spot fotogénico cercano", 25,
                 categories=["photo_spot", "viewpoint", "street_art"], constraints=[], role="optional"),
    ],
    # Museos (día)
    "museum_day": [
        SlotSpec("museum", "🏛️ Museo imperdible", 110,
                 categories=["museum"], constraints=["indoor"], role="reward"),
        SlotSpec("coffee_break", "☕ Café cercano", 30,
                 categories=["cafe", "bakery"], constraints=["warm"], role="anchor"),
    ],
    # Alternativa cultural nocturna (cuando museo no procede)
    "culture_alt_late": [
        SlotSpec("culture_alt", "🎭 Cultura ‘tipo museo’ (indoor, abierto tarde)", 75,
                 categories=["cultural_bar", "jazz_bar", "cinema", "theater"],
                 constraints=["indoor", "quiet"], role="reward"),
        SlotSpec("late_coffee", "🍰 Postre / té caliente", 35,
                 categories=["dessert", "cafe"], constraints=["warm"], role="anchor"),
    ],
}

# Mapeo intent del usuario → template base
INTENT_TO_TEMPLATE = {
    "chill": "chill_evening",
    "drink": "chill_evening",
    "shop_local": "shop_local",
    "museum": "museum_day",
}

# Fallback semántico (ej: museo de noche -> culture_alt_late)
INTENT_FALLBACK_TEMPLATE = {
    "museum": "culture_alt_late",
}

def choose_template(intent: str, when_selection: str, hour: int) -> str:
    intent = (intent or "chill").strip().lower()
    when_selection = (when_selection or "now").strip().lower()

    base = INTENT_TO_TEMPLATE.get(intent, "chill_evening")

    # Reglas simples: si es museo y es noche, mandamos fallback
    if intent == "museum" and (hour >= 18 or hour <= 6 or when_selection == "tonight"):
        return INTENT_FALLBACK_TEMPLATE["museum"]

    # Chill de madrugada -> igual chill_evening (sirve)
    return base
