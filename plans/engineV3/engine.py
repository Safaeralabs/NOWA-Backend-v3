from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .presets import choose_template, INTENT_TEMPLATES, SlotSpec
from .time_rules import get_daypart, compute_open_status, build_weather_profile
from .scoring import score_place_for_slot
from .optimizer import order_stops_nearest_neighbor
from .llm import SlotLLM
from .providers import Providers


@dataclass
class V3PlanResult:
    slots: List[Dict[str, Any]]        # slots con opciones + selected_place_ids + why_now
    chosen_stops: List[Dict[str, Any]] # 1 stop por slot seleccionado
    legs: List[Dict[str, Any]]         # [] en core si no hay directions
    debug: Dict[str, Any]


class V3PlannerEngine:
    def __init__(self, *, providers: Providers, llm: Optional[SlotLLM] = None):
        self.providers = providers
        self.llm = llm or SlotLLM(client=None)

    def generate(self, *, inputs: Dict[str, Any], context: Dict[str, Any]) -> V3PlanResult:
        """
        V3 core entrypoint.

        Required:
          - inputs: city_name, user_location, intent, when_selection, discovery_mode, constraints
          - context: dt_local (tz-aware)
        Weather:
          - mandatory: if not in context, fetched via providers.get_weather()
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

        hour = dt_local.hour
        daypart = get_daypart(dt_local)

        # Weather is mandatory
        weather = context.get("weather")
        if not weather:
            weather = self.providers.get_weather(user_location=user_location)

        # Choose template based on intent + time
        template_key = choose_template(intent=intent, when_selection=when, hour=hour)
        slot_specs: List[SlotSpec] = INTENT_TEMPLATES.get(template_key, [])

        # Build slots (climate affects STRUCTURE)
        slots = self._build_slots(dt_local=dt_local, slot_specs=slot_specs, weather=weather)

        # Rank options for each slot
        ranked_slots = self._rank_slots(
            slots=slots,
            city=city,
            user_location=user_location,
            daypart=daypart,
            discovery_mode=discovery_mode,
            constraints=constraints,
        )

        # Fill: deterministic fallback (or LLM if you add a client later)
        filled_slots = self.llm.fill(
            context={"hour": hour, "daypart": daypart, "weather": weather},
            ranked_slots=ranked_slots,
        )

        # Materialize chosen stops (1 per slot)
        chosen_stops = self._materialize_stops(filled_slots)

        # Order stops (simple deterministic)
        chosen_stops = order_stops_nearest_neighbor(chosen_stops)

        # Legs: core can be [] if no directions provider
        legs = self.providers.get_legs(stops=chosen_stops, mode="walking")

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
                "weather_confidence": (weather or {}).get("confidence"),
            },
        )

    def _build_slots(self, *, dt_local: datetime, slot_specs: List[SlotSpec], weather: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Climate affects:
          - drop outdoor slots in hostile weather
          - add indoor_only / prefer_short_legs constraints
          - adjust durations
          - tweak categories (e.g. hotel_bar first on very cold)
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
            if spec.slot_id in ("photo_stop", "walk", "viewpoint_walk"):
                if wp.very_cold or wp.rain or wp.snow:
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
        ranked: List[Dict[str, Any]] = []

        for slot in slots:
            # cats = categories del slot (lo que preguntaste)
            cats: List[str] = slot.get("categories") or []

            slot_constraints = list(dict.fromkeys((constraints or []) + (slot.get("constraints") or [])))

            # Fetch normalized candidates from Google Places
            # Enrich opening_hours via Details so compute_open_status can work better.
            candidates = self.providers.fetch_candidates(
                city=city,
                user_location=user_location,
                categories=cats,
                radius_m=2500,
                enrich_opening_hours=True,
                enrich_limit=25,
            )

            options = []
            for place in candidates:
                open_status = compute_open_status(place, slot["start"], slot["duration_min"])
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

            options.sort(key=lambda x: x["score"], reverse=True)

            ranked.append({
                **slot,
                "options": options[:10],  # topN por slot
            })

        return ranked

    def _materialize_stops(self, slots_filled: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        stops: List[Dict[str, Any]] = []

        for i, slot in enumerate(slots_filled):
            picks = slot.get("selected_place_ids") or []
            if not picks:
                continue
            chosen_id = picks[0]

            chosen_opt = None
            for opt in (slot.get("options") or []):
                if opt["place"]["place_id"] == chosen_id:
                    chosen_opt = opt
                    break

            if not chosen_opt:
                continue

            p = chosen_opt["place"]

            stops.append({
                "order_index": i,
                "slot_id": slot["slot_id"],
                "slot_title": slot["title"],
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
                "opening_hours_json": p.get("opening_hours"),
                "open_status": chosen_opt.get("open"),
                "open_confidence": chosen_opt.get("open_confidence"),
                "open_reason": chosen_opt.get("open_reason"),
                "place_types": p.get("types"),
                "popularity": p.get("user_ratings_total"),
                "photo_reference": (p.get("photos") or [{}])[0].get("photo_reference") if isinstance(p.get("photos"), list) else None,
            })

        return stops
