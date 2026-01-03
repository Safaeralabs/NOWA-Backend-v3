from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, conlist, constr
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

WHY_MAX = 50
CITY_DNA_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días


class CityDNA(BaseModel):
    city: str
    language: str = "es"
    food_typicals: List[Dict[str, Any]] = Field(default_factory=list)
    drink_typicals: List[Dict[str, Any]] = Field(default_factory=list)
    local_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    etiquette: List[str] = Field(default_factory=list)
    neighborhood_hints: List[Dict[str, Any]] = Field(default_factory=list)


class LocalGuide(BaseModel):
    headline: str
    summary: str
    climate_advice: List[str] = Field(default_factory=list)
    local_typicals: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    per_slot_order_tips: List[Dict[str, Any]] = Field(default_factory=list)
    practical_notes: List[str] = Field(default_factory=list)


def _cache_key_city_dna(city: str, language: str) -> str:
    safe_city = (city or "").strip().lower().replace(" ", "_")
    safe_lang = (language or "es").strip().lower()
    return f"city_dna:v1:{safe_city}:{safe_lang}"


class SlotPick(BaseModel):
    slot_id: str
    selected_place_id: str
    why_now: constr(min_length=0, max_length=WHY_MAX) = ""


class SlotsFill(BaseModel):
    picks: conlist(SlotPick, min_length=0) = Field(default_factory=list)


class SlotLLM:
    """
    LLM with robust fallbacks:
    - If client exists: use LLM for better copy
    - If client None or fails: deterministic fallback
    """

    def __init__(self, client: Optional[Any] = None, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def fill(self, *, context: Dict[str, Any], ranked_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fill slots with selections + why_now"""
        if not self.client:
            return self._deterministic_fallback(context, ranked_slots)

        try:
            return self._llm_fill(context, ranked_slots)
        except Exception as e:
            logger.warning(f"LLM fill failed: {e}, using fallback")
            return self._deterministic_fallback(context, ranked_slots)

    def _deterministic_fallback(self, context: Dict[str, Any], ranked_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for slot in ranked_slots:
            options = slot.get("options") or []
            if not options:
                out.append({**slot, "selected_place_ids": [], "why_now": ""})
                continue
            chosen = options[0]["place"]["place_id"]
            why = self._simple_why_now(slot, context)
            out.append({**slot, "selected_place_ids": [chosen], "why_now": why})
        return out

    def _llm_fill(self, context: Dict[str, Any], ranked_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM for soft picks + better why_now copy"""
        compact_slots = []
        for slot in ranked_slots:
            opts = []
            for opt in (slot.get("options") or [])[:5]:
                p = opt["place"]
                opts.append({
                    "place_id": p.get("place_id"),
                    "name": p.get("name"),
                    "category": p.get("category"),
                    "rating": p.get("rating"),
                    "popularity": p.get("user_ratings_total"),
                    "distance_m": opt.get("distance_m"),
                })

            compact_slots.append({
                "slot_id": slot["slot_id"],
                "title": slot["title"],
                "start": slot["start"].isoformat(),
                "duration_min": slot["duration_min"],
                "candidates": opts,
            })

        sys = (
            "You are a local travel planner. "
            "Pick exactly one candidate place_id per slot from the provided candidates. "
            f"Return a short why_now (max {WHY_MAX} chars) for each slot. "
            "Do NOT invent place_ids."
        )

        user = {
            "context": {
                "daypart": context.get("daypart"),
                "hour": context.get("hour"),
                "weather": context.get("weather", {}),
            },
            "slots": compact_slots,
        }

        from openai import OpenAI
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": str(user)},
            ],
            response_format={"type": "json_object"}
        )

        import json
        parsed_text = resp.choices[0].message.content
        parsed = json.loads(parsed_text)
        picks_list = parsed.get("picks") or []

        picks_by_slot = {}
        for p_data in picks_list:
            slot_id = p_data.get("slot_id")
            place_id = p_data.get("selected_place_id")
            why = p_data.get("why_now", "")[:WHY_MAX]
            picks_by_slot[slot_id] = {"place_id": place_id, "why": why}

        out = []
        for slot in ranked_slots:
            p = picks_by_slot.get(slot["slot_id"])
            if not p:
                options = slot.get("options") or []
                chosen = options[0]["place"]["place_id"] if options else None
                why = self._simple_why_now(slot, context)
                out.append({**slot, "selected_place_ids": [chosen] if chosen else [], "why_now": why})
                continue

            valid_ids = {o["place"]["place_id"] for o in (slot.get("options") or [])}
            if p["place_id"] not in valid_ids:
                options = slot.get("options") or []
                chosen = options[0]["place"]["place_id"] if options else None
                why = self._simple_why_now(slot, context)
                out.append({**slot, "selected_place_ids": [chosen] if chosen else [], "why_now": why})
                continue

            out.append({
                **slot,
                "selected_place_ids": [p["place_id"]],
                "why_now": p["why"],
            })

        return out

    def _simple_why_now(self, slot: Dict[str, Any], context: Dict[str, Any]) -> str:
        weather = context.get("weather") or {}
        cond = str(weather.get("condition") or "").lower()
        feels = weather.get("feels_like", weather.get("temp"))
        daypart = context.get("daypart") or ""
        base = "Buen timing"

        if isinstance(feels, (int, float)) and feels <= 5:
            base = "Mejor indoor por frío"
        elif "rain" in cond or "drizzle" in cond:
            base = "Ideal para cubrirte"
        elif daypart == "late":
            base = "Abierto a esta hora"

        return base[:WHY_MAX]

    # ========== City DNA (con hybrid fallback) ==========
    
    def get_city_dna(self, *, city: str, language: str = "es") -> Dict[str, Any]:
        """
        Get City DNA with robust fallback strategy:
        1. Check cache
        2. Try LLM
        3. Fall back to static data from city_fallbacks.py
        """
        key = _cache_key_city_dna(city, language)
        cached = cache.get(key)
        if cached:
            logger.info(f"   City DNA cache HIT: {city}")
            return cached

        # Try LLM
        if self.client:
            try:
                logger.info(f"    Generating City DNA via LLM: {city}")
                dna = self._llm_build_city_dna(city=city, language=language)
                parsed = CityDNA(**dna).model_dump()
                cache.set(key, parsed, CITY_DNA_TTL_SECONDS)
                logger.info(f"   City DNA generated: {len(parsed['food_typicals'])} foods")
                return parsed
            except Exception as e:
                logger.warning(f"  LLM City DNA failed for {city}: {e}")
        
        # Fall back to static
        logger.info(f"    Using static fallback for City DNA: {city}")
        from .city_fallbacks import get_city_fallback
        fallback = get_city_fallback(city)
        
        # Cache fallback with shorter TTL
        cache.set(key, fallback, 7*24*60*60)  # 7 days
        return fallback

    def _llm_build_city_dna(self, *, city: str, language: str) -> Dict[str, Any]:
        """LLM generates City DNA"""
        sys = (
            "You are an expert local travel guide. "
            "Create a compact City DNA for food/drink/culture that is culturally accurate. "
            "Return STRICT JSON only, no markdown. "
            "Do NOT invent venues, only describe typical dishes/drinks."
        )

        schema_example = {
            "city": city,
            "language": language,
            "food_typicals": [
                {"name": "Dish Name", "note": "Description", "when": ["morning"], "how_to_order": "Tip"}
            ],
            "drink_typicals": [
                {"name": "Drink Name", "note": "Description", "when": ["evening"], "how_to_order": "Tip"}
            ],
            "local_keywords": ["keyword1", "keyword2"],
            "negative_keywords": ["tourist_trap"],
            "etiquette": ["Tip 1", "Tip 2"],
            "neighborhood_hints": [
                {"name": "Neighborhood", "vibe": ["cool", "local"], "best_for": ["nightlife"]}
            ]
        }

        user = f"Generate City DNA for {city} in {language}. Schema: {schema_example}"

        from openai import OpenAI
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"}
        )

        import json
        text = resp.choices[0].message.content
        return json.loads(text)

    # ========== Local Guide (con fallback determinístico) ==========

    def build_local_guide(
        self,
        *,
        city_dna: Dict[str, Any],
        intent: str,
        subtypes: List[str],
        weather: Dict[str, Any],
        options_by_slot: List[Dict[str, Any]],
        constraints: List[str],
        language: str = "es",
    ) -> Dict[str, Any]:
        """
        Build local guide with robust fallback.
        """
        if not self.client:
            logger.info("  Building deterministic local guide (no LLM)")
            return self._deterministic_guide(
                city_dna=city_dna,
                weather=weather,
                constraints=constraints
            )
        
        try:
            logger.info("    Building local guide via LLM")
            return self._llm_build_local_guide(
                city_dna=city_dna,
                intent=intent,
                subtypes=subtypes,
                weather=weather,
                options_by_slot=options_by_slot,
                constraints=constraints,
                language=language
            )
        except Exception as e:
            logger.warning(f"  LLM guide failed: {e}, using deterministic fallback")
            return self._deterministic_guide(
                city_dna=city_dna,
                weather=weather,
                constraints=constraints
            )

    def _deterministic_guide(
        self,
        city_dna: Dict[str, Any],
        weather: Dict[str, Any],
        constraints: List[str]
    ) -> Dict[str, Any]:
        """Create guide without LLM using city_dna"""
        feels = weather.get('feels_like', weather.get('temp', 18))
        cond = (weather.get('condition') or '').lower()
        
        climate_advice = []
        if feels <= 5:
            climate_advice.append("Hace mucho frío - busca lugares indoor")
        elif feels >= 28:
            climate_advice.append("Hace calor - hidrátate y busca sombra")
        if 'rain' in cond or 'drizzle' in cond:
            climate_advice.append("Lluvia prevista - lleva paraguas")
        if 'snow' in cond:
            climate_advice.append("Nieve - abrígate bien y ten cuidado al caminar")
        
        return {
            "headline": "    Plan adaptado al clima actual",
            "summary": f"Plan optimizado para {city_dna.get('city', 'la ciudad')} considerando clima y horarios.",
            "climate_advice": climate_advice,
            "local_typicals": {
                "food": city_dna.get('food_typicals', [])[:5],
                "drinks": city_dna.get('drink_typicals', [])[:5]
            },
            "per_slot_order_tips": [],
            "practical_notes": city_dna.get('etiquette', [])
        }

    def _llm_build_local_guide(
        self,
        city_dna: Dict[str, Any],
        intent: str,
        subtypes: List[str],
        weather: Dict[str, Any],
        options_by_slot: List[Dict[str, Any]],
        constraints: List[str],
        language: str
    ) -> Dict[str, Any]:
        """LLM generates local guide"""
        compact_slots = []
        for s in options_by_slot:
            slot_id = s.get("slot_id")
            opts = []
            for o in (s.get("options") or [])[:5]:
                opts.append({
                    "place_id": o.get("place_id"),
                    "name": o.get("name"),
                    "category": o.get("category"),
                })
            compact_slots.append({"slot_id": slot_id, "options": opts})

        sys = (
            "You are a warm, practical local tour guide. "
            "You MUST NOT invent venues or claim a dish is served at a specific place. "
            "Suggest what to order ONLY as: 'If you see X on the menu, order it' or 'Ask for X'. "
            "Return STRICT JSON only, no markdown."
        )

        user_content = {
            "language": language,
            "intent": intent,
            "subtypes": subtypes,
            "constraints": constraints,
            "weather": weather,
            "city_dna": city_dna,
            "options_by_slot": compact_slots,
        }

        from openai import OpenAI
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": str(user_content)},
            ],
            response_format={"type": "json_object"}
        )

        import json
        text = resp.choices[0].message.content
        guide = json.loads(text)
        parsed = LocalGuide(**guide).model_dump()
        return parsed