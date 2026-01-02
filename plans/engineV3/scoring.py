from typing import Dict, Any, List
from .time_rules import is_category_suitable, OpenStatus

def score_place_for_slot(
    place: Dict[str, Any],
    slot_categories: List[str],
    daypart: str,
    discovery_mode: str,
    constraints: List[str],
    open_status: OpenStatus,
    distance_m: float | None = None,
) -> float:
    """
    Determinístico: no usa LLM.
    """
    score = 0.0
    category = (place.get("category") or "").strip()
    rating = float(place.get("rating") or 0.0)
    reviews = float(place.get("user_ratings_total") or 0.0)

    # 1) Apertura (hard-ish)
    if open_status.is_open is False:
        return -10_000.0
    if open_status.is_open is True:
        score += 15.0
        if open_status.confidence == "medium":
            score -= 5.0  # closing soon
    else:
        score -= 3.0  # unknown

    # 2) Match categoría
    if category in slot_categories:
        score += 30.0
    else:
        score += 5.0

    # 3) Daypart suitability (“no bar 11am”)
    if category and not is_category_suitable(category, daypart):
        score -= 25.0

    # 4) Calidad
    score += min(rating, 5.0) * 6.0
    # reviews as weak popularity
    score += min(reviews / 500.0, 6.0) * 1.2

    # 5) Local vs iconic
    if discovery_mode == "local":
        if place.get("tourist_density", 0) >= 2:
            score -= 10.0
        if place.get("local_favorite"):
            score += 8.0
    else:
        score += 2.0

    # 6) Constraints
    if "indoor_only" in constraints and not place.get("is_indoor", True):
        score -= 50.0
    if "quiet" in constraints:
        noise = int(place.get("noise_level") or 1)  # 1..5
        score -= max(0, noise - 2) * 4.0
    if "no_walk" in constraints and distance_m is not None:
        # penaliza distancia (más fuerte)
        score -= min(distance_m / 200.0, 15.0)

    # 7) Distancia suave por defecto
    if distance_m is not None:
        score -= min(distance_m / 300.0, 10.0)

    return score
