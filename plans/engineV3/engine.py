from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from .presets import choose_template, INTENT_TEMPLATES, SlotSpec
from .time_rules import get_daypart, compute_open_status, build_weather_profile
from .scoring import score_place_for_slot
from .optimizer import order_stops_nearest_neighbor
from .llm import SlotLLM
from .providers import Providers

logger = logging.getLogger(__name__)


@dataclass
class V3PlanResult:
    """Result from V3 engine generation"""
    slots: List[Dict[str, Any]]        # slots con opciones + selected_place_ids + why_now
    chosen_stops: List[Dict[str, Any]] # 1 stop por slot seleccionado
    legs: List[Dict[str, Any]]         # [] en core si no hay directions
    debug: Dict[str, Any]


class V3PlannerEngine:
    """
    NOWA V3 Planning Engine
    
    Key features:
    - Weather-driven (mandatory)
    - Opening hours validation (compute_open_status)
    - Deterministic scoring (no LLM for selection)
    - Optional LLM for copy (why_now, guide)
    - Real Google Places candidates (no hallucination)
    """

    def __init__(self, *, providers: Providers, llm: Optional[SlotLLM] = None):
        self.providers = providers
        self.llm = llm or SlotLLM(client=None)

    def generate(self, *, inputs: Dict[str, Any], context: Dict[str, Any]) -> V3PlanResult:
        """
        V3 core entrypoint.

        Required inputs:
        - city_name: str
        - user_location: {lat, lng}
        - intent: str (chill, food_tour, etc)
        - when_selection: str (now, later_today, tonight, tomorrow)
        - discovery_mode: str (local, tourist, mixed)  ← FIXED: accept mixed
        - constraints: List[str]

        Required context:
        - dt_local: datetime (tz-aware)
        - weather: dict (mandatory, fetched by providers if missing)

        Returns:
        V3PlanResult with slots, chosen_stops, legs, debug
        """
        dt_local: datetime = context["dt_local"]

        user_location = (
            inputs.get("user_location")
            or inputs.get("current_location")
            or context.get("user_location")
        )
        if not user_location or "lat" not in user_location or "lng" not in user_location:
            raise ValueError("V3 requires user_location/current_location with lat/lng")

        city = inputs.get("city_name") or inputs.get("city") or ""
        if not city:
            raise ValueError("V3 requires city_name/city")

        intent = (inputs.get("intent") or "chill").strip().lower()
        when = (inputs.get("when_selection") or "now").strip().lower()
        discovery_mode = (inputs.get("discovery_mode") or "local").strip().lower()
        constraints = inputs.get("constraints") or []

        # ========== FIX: Extract energy & duration for dynamic templates ==========
        energy_level = inputs.get("energy", 2)  # 0-3 scale
        energy_str = "low" if energy_level <= 1 else ("high" if energy_level >= 2 else "medium")
        
        # Calculate duration in hours
        start_time = context.get("start_time") or dt_local
        end_time = context.get("end_time")
        if end_time:
            try:
                duration_hours = (end_time - start_time).total_seconds() / 3600.0
            except:
                duration_hours = 4.0
        else:
            duration_hours = inputs.get("duration_hours", 4.0)

        hour = dt_local.hour
        daypart = get_daypart(dt_local)

        logger.info(f"    V3 Generate: intent={intent}, when={when}, daypart={daypart}, hour={hour}, duration={duration_hours:.1f}h, energy={energy_str}")

        # Weather is mandatory
        weather = context.get("weather")
        if not weather:
            logger.info("   Weather not in context, fetching...")
            weather = self.providers.get_weather(user_location=user_location)

        logger.info(f"   Weather: {weather.get('temp')}°C, {weather.get('condition')}, confidence={weather.get('confidence')}")

        # ========== FIX: Use dynamic choose_template ==========
        template_key, slot_specs = choose_template(
            intent=intent, 
            when_selection=when, 
            hour=hour,
            duration_hours=duration_hours,
            energy=energy_str
        )

        logger.info(f"    Template: {template_key}, slots={len(slot_specs)} (adjusted for {duration_hours:.1f}h, energy={energy_str})")

        # Build slots (climate affects STRUCTURE)
        slots = self._build_slots(dt_local=dt_local, slot_specs=slot_specs, weather=weather)

        logger.info(f"    Built {len(slots)} slots (after climate filtering)")

        # Rank options for each slot
        ranked_slots = self._rank_slots(
            slots=slots,
            city=city,
            user_location=user_location,
            daypart=daypart,
            discovery_mode=discovery_mode,
            constraints=constraints,
        )

        logger.info(f"   Ranked slots: {[len(s.get('options', [])) for s in ranked_slots]} candidates per slot")

        # Fill: deterministic fallback (or LLM if client exists)
        filled_slots = self.llm.fill(
            context={"hour": hour, "daypart": daypart, "weather": weather},
            ranked_slots=ranked_slots,
        )

        logger.info(f"   Filled slots with selections")

        # Materialize chosen stops (1 per slot)
        chosen_stops = self._materialize_stops(filled_slots)

        logger.info(f"  Materialized {len(chosen_stops)} stops")

        # Order stops (simple deterministic nearest neighbor)
        chosen_stops = order_stops_nearest_neighbor(chosen_stops)

        # Legs: core can be [] if no directions provider
        # (tasks.py will build legs later)
        legs = []

        return V3PlanResult(
            slots=filled_slots,
            chosen_stops=chosen_stops,
            legs=legs,
            debug={
                "engine": "v3",
                "template": template_key,
                "intent": intent,
                "daypart": daypart,
                "slot_count": len(filled_slots),
                "duration_hours": duration_hours,
                "energy_level": energy_str,
                "weather_confidence": (weather or {}).get("confidence"),
            },
        )

    def _build_slots(
        self, 
        *, 
        dt_local: datetime, 
        slot_specs: List[SlotSpec], 
        weather: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build slots with climate-driven adjustments.
        
        Climate affects:
          - Drop outdoor slots in hostile weather (rain, snow, very cold)
          - Add indoor_only / prefer_short_legs constraints
          - Adjust durations
          - Tweak categories (e.g. hotel_bar first on very cold)
        """
        wp = build_weather_profile(weather)

        cursor = dt_local + timedelta(minutes=5)
        slots: List[Dict[str, Any]] = []

        climate_constraints: List[str] = []
        if wp.very_cold or wp.rain or wp.snow:
            climate_constraints.append("indoor_only")
            climate_constraints.append("prefer_short_legs")

        for spec in slot_specs:
            # Skip outdoor-ish slots on hostile weather
            if spec.slot_id in ("photo_stop", "walk", "viewpoint_walk", "scenic_walk"):
                if wp.very_cold or wp.rain or wp.snow:
                    logger.info(f"  Skipping outdoor slot '{spec.slot_id}' due to weather")
                    continue

            # Duration adjustments (keep simple)
            duration = spec.duration_min
            if wp.very_cold and spec.slot_id in ("shopping_cluster", "explore_area"):
                duration = max(60, int(duration * 0.75))
            if wp.pleasant and spec.slot_id in ("photo_stop", "walk"):
                duration = int(duration * 1.2)

            # Merge constraints
            slot_constraints = list(spec.constraints)
            slot_constraints.extend(climate_constraints)
            slot_constraints = list(dict.fromkeys(slot_constraints))

            # Category tweaks
            categories = list(spec.categories)
            if wp.very_cold and spec.slot_id == "drinks":
                # Prioritize hotel_bar (warm, indoor)
                if "hotel_bar" in categories:
                    categories.remove("hotel_bar")
                categories.insert(0, "hotel_bar")

            slot_start = cursor
            slot_end = cursor + timedelta(minutes=duration)

            slots.append({
                "slot_id": spec.slot_id,
                "title": spec.title,
                "start": slot_start,
                "end": slot_end,
                "duration_min": duration,
                "categories": categories,
                "constraints": slot_constraints,
                "role": spec.role,
            })

            cursor = slot_end

        return slots

    def _rank_slots(
        self,
        *,
        slots: List[Dict[str, Any]],
        city: str,
        user_location: Dict[str, float],
        daypart: str,
        discovery_mode: str,
        constraints: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates for each slot using deterministic scoring.
        
           FIX: Now calls fetch_candidates with enrich_opening_hours=True
        """
        ranked: List[Dict[str, Any]] = []

        for slot in slots:
            cats: List[str] = slot.get("categories") or []

            slot_constraints = list(dict.fromkeys((constraints or []) + (slot.get("constraints") or [])))

            logger.info(f"    Fetching candidates for slot '{slot['slot_id']}': categories={cats}")

            #    FIX: ACTIVATE enrich_opening_hours
            candidates = self.providers.fetch_candidates(
                city=city,
                user_location=user_location,
                categories=cats,
                radius_m=2500,
                enrich_opening_hours=True,  # ← FIX: Ensure opening_hours.periods is fetched
                enrich_limit=25,            # ← FIX: Limit Details API calls
            )

            logger.info(f"    Fetched {len(candidates)} candidates for slot '{slot['slot_id']}'")

            options = []
            for place in candidates:
                # Compute open status using enriched opening_hours
                open_status = compute_open_status(place, slot["start"], slot["duration_min"])
                
                # Hard filter: skip if confirmed closed
                if open_status.is_open is False:
                    continue

                dist_m = self.providers.distance_m(user_location=user_location, place=place)

                score = score_place_for_slot(
                    place=place,
                    slot_categories=cats,
                    daypart=daypart,
                    discovery_mode=discovery_mode,
                    constraints=slot_constraints,
                    open_status=open_status,
                    distance_m=dist_m,
                )

                options.append({
                    "place": place,
                    "score": score,
                    "distance_m": dist_m,
                    "open": open_status.is_open,
                    "open_confidence": open_status.confidence,
                    "open_reason": open_status.reason,
                })

            # Sort by score (highest first)
            options.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"   Slot '{slot['slot_id']}': {len(options)} valid options (top score={options[0]['score']:.1f})" if options else f"  Slot '{slot['slot_id']}': NO valid options")

            ranked.append({
                **slot,
                "options": options[:10],  # topN per slot
            })

        return ranked

    def _materialize_stops(self, slots_filled: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert filled slots to materialized stops.
        
        Each slot should have:
          - selected_place_ids: [place_id, ...]
          - why_now: str (short reason)
        
        We take the first selected_place_id and create a stop.
        """
        stops: List[Dict[str, Any]] = []

        for i, slot in enumerate(slots_filled):
            picks = slot.get("selected_place_ids") or []
            if not picks:
                logger.warning(f"  Slot '{slot['slot_id']}' has no selection, skipping")
                continue
            
            chosen_id = picks[0]

            # Find the chosen option in slot's options
            chosen_opt = None
            for opt in (slot.get("options") or []):
                if opt["place"]["place_id"] == chosen_id:
                    chosen_opt = opt
                    break

            if not chosen_opt:
                logger.warning(f"  Slot '{slot['slot_id']}': selected place_id={chosen_id} not in options, skipping")
                continue

            p = chosen_opt["place"]

            stops.append({
                "order_index": i,
                "slot_id": slot["slot_id"],
                "slot_title": slot["title"],
                "slot_role": slot.get("role"),
                "why_now": slot.get("why_now", ""),
                "place_id": p["place_id"],
                "name": p.get("name") or "",
                "lat": p["lat"],
                "lng": p["lng"],
                "category": p.get("category") or "other",
                "start": slot["start"],
                "duration_min": int(slot["duration_min"]),
                "open_status": chosen_opt["open"],
                "open_confidence": chosen_opt["open_confidence"],
                "open_reason": chosen_opt["open_reason"],
                "opening_hours_json": p.get("opening_hours"),
                "place_types": p.get("types"),
                "business_status": p.get("business_status"),
                "rating": p.get("rating"),
                "popularity": p.get("user_ratings_total"),
                "photo_reference": (p.get("photos") or [{}])[0].get("photo_reference") if isinstance(p.get("photos"), list) and p.get("photos") else None,
            })

        return stops