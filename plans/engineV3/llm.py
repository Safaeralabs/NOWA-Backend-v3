from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, conlist, constr
from typing import Tuple
from django.core.cache import cache
# OpenAI SDK (official)
# pip install openai
# from openai import OpenAI
# We'll import lazily to avoid hard dependency if you run without LLM.

WHY_MAX = 50


CITY_DNA_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días


class CityDNA(BaseModel):
    city: str
    language: str = "es"

    # “Lo típico” por ciudad (estable)
    food_typicals: List[Dict[str, Any]] = Field(default_factory=list)
    drink_typicals: List[Dict[str, Any]] = Field(default_factory=list)

    # Keywords para mejorar queries Places sin inventar lugares
    local_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)

    # Etiqueta / costumbres
    etiquette: List[str] = Field(default_factory=list)

    # “barrio/zonas” opcional (si el LLM lo sabe)
    neighborhood_hints: List[Dict[str, Any]] = Field(default_factory=list)


class LocalGuide(BaseModel):
    headline: str
    summary: str
    climate_advice: List[str] = Field(default_factory=list)

    # Lo típico, por ciudad (qué comer / beber)
    local_typicals: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    # Consejos por slot (qué pedir, cómo ordenar, qué buscar en menú)
    per_slot_order_tips: List[Dict[str, Any]] = Field(default_factory=list)

    # Notas prácticas / seguridad alimentaria suave (sin alarmismo)
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
    LLM is OPTIONAL.
    - If client is None -> deterministic fallback
    - If client exists -> soft selection + better copy, structured output
    """

    def __init__(self, client: Optional[Any] = None, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def fill(self, *, context: Dict[str, Any], ranked_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.client:
            return self._deterministic_fallback(context, ranked_slots)

        try:
            return self._llm_fill(context, ranked_slots)
        except Exception:
            # Never break the plan because LLM failed
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
        # Build a compact input so cost stays low and it can't hallucinate new places.
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

        # Structured Outputs via Responses API parse (Pydantic)
        # See OpenAI docs: responses.parse + Pydantic schema :contentReference[oaicite:3]{index=3}
        from openai import OpenAI  # lazy import

        # self.client is expected to be OpenAI() instance
        resp = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": sys},
                {"role": "user", "content": str(user)},
            ],
            text_format=SlotsFill,
        )

        parsed: SlotsFill = resp.output_parsed  # provided by SDK when using parse :contentReference[oaicite:4]{index=4}
        picks_by_slot = {p.slot_id: p for p in parsed.picks}

        out = []
        for slot in ranked_slots:
            p = picks_by_slot.get(slot["slot_id"])
            if not p:
                # fallback per-slot
                options = slot.get("options") or []
                chosen = options[0]["place"]["place_id"] if options else None
                why = self._simple_why_now(slot, context)
                out.append({**slot, "selected_place_ids": [chosen] if chosen else [], "why_now": why})
                continue

            # ensure selected_place_id exists in candidates list
            valid_ids = {o["place"]["place_id"] for o in (slot.get("options") or [])}
            if p.selected_place_id not in valid_ids:
                options = slot.get("options") or []
                chosen = options[0]["place"]["place_id"] if options else None
                why = self._simple_why_now(slot, context)
                out.append({**slot, "selected_place_ids": [chosen] if chosen else [], "why_now": why})
                continue

            out.append({
                **slot,
                "selected_place_ids": [p.selected_place_id],
                "why_now": (p.why_now or "")[:WHY_MAX],
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
    def get_city_dna(self, *, city: str, language: str = "es") -> Dict[str, Any]:
        """
        Genera City DNA una vez y cachea 30 días.
        Si no hay client, devuelve fallback mínimo.
        """
        key = _cache_key_city_dna(city, language)
        cached = cache.get(key)
        if cached:
            return cached

        # fallback si LLM desactivado
        if not self.client:
            fallback = {
                "city": city,
                "language": language,
                "food_typicals": [],
                "drink_typicals": [],
                "local_keywords": [],
                "negative_keywords": [],
                "etiquette": [],
                "neighborhood_hints": [],
            }
            cache.set(key, fallback, CITY_DNA_TTL_SECONDS)
            return fallback

        try:
            dna = self._llm_build_city_dna(city=city, language=language)
            # valida con Pydantic
            parsed = CityDNA(**dna).model_dump()
            cache.set(key, parsed, CITY_DNA_TTL_SECONDS)
            return parsed
        except Exception:
            # si falla, cacheamos fallback corto para no reintentar sin parar
            fallback = {
                "city": city,
                "language": language,
                "food_typicals": [],
                "drink_typicals": [],
                "local_keywords": [],
                "negative_keywords": [],
                "etiquette": [],
                "neighborhood_hints": [],
            }
            cache.set(key, fallback, 6 * 60 * 60)  # 6h
            return fallback

    def _llm_build_city_dna(self, *, city: str, language: str) -> Dict[str, Any]:
        """
        LLM produce CityDNA estructurado.
        """
        sys = (
            "You are an expert local travel guide. "
            "Create a compact City DNA for shopping/food/nightlife that is culturally accurate. "
            "Return STRICT JSON only, no markdown."
        )

        user = {
            "city": city,
            "language": language,
            "schema": {
                "city": "string",
                "language": "string",
                "food_typicals": [
                    {"name": "string", "note": "string", "when": ["string"], "how_to_order": "string"}
                ],
                "drink_typicals": [
                    {"name": "string", "note": "string", "when": ["string"], "how_to_order": "string"}
                ],
                "local_keywords": ["string"],
                "negative_keywords": ["string"],
                "etiquette": ["string"],
                "neighborhood_hints": [
                    {"name": "string", "vibe": ["string"], "best_for": ["string"]}
                ]
            },
            "constraints": [
                "Avoid hallucinating specific venues.",
                "Do not claim a dish is served at a particular place.",
                "Focus on typical dishes/drinks and helpful keywords."
            ],
        }

        resp = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": sys},
                {"role": "user", "content": str(user)},
            ],
        )

        # SDK devuelve texto en resp.output_text (según versión); hacemos parse simple:
        text = getattr(resp, "output_text", None) or ""
        # intenta parsear JSON
        import json
        return json.loads(text)

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
        Devuelve guía tipo “local guide”:
        - qué es típico de la ciudad (comida/bebida)
        - qué pedir en restaurantes/bares (sin inventar menús)
        - tips por clima/hora
        """
        if not self.client:
            # fallback determinístico básico (sin LLM)
            return {
                "headline": "✔️ Plan adaptado al clima",
                "summary": "Plan construido con clima y horarios en mente.",
                "climate_advice": [],
                "local_typicals": {
                    "food": city_dna.get("food_typicals", [])[:5],
                    "drinks": city_dna.get("drink_typicals", [])[:5],
                },
                "per_slot_order_tips": [],
                "practical_notes": [],
            }

        # Compactar opciones para que el LLM NO invente lugares
        compact_slots = []
        for s in options_by_slot:
            slot_id = s.get("slot_id")
            opts = []
            for o in (s.get("options") or [])[:8]:
                opts.append({
                    "place_id": o.get("place_id"),
                    "name": o.get("name"),
                    "category": o.get("category"),
                    "rating": o.get("rating"),
                    "distance_m": o.get("distance_m"),
                    "open": o.get("open"),
                    "open_confidence": o.get("open_confidence"),
                })
            compact_slots.append({"slot_id": slot_id, "options": opts})

        sys = (
            "You are a warm, practical local tour guide. "
            "You MUST NOT invent venues or claim a dish is served at a specific place. "
            "You may suggest what to order ONLY as: 'If you see X on the menu, order it' or 'Ask for X'. "
            "Return STRICT JSON only, no markdown."
        )

        user = {
            "language": language,
            "intent": intent,
            "subtypes": subtypes,
            "constraints": constraints,
            "weather": weather,
            "city_dna": city_dna,
            "options_by_slot": compact_slots,
            "schema": {
                "headline": "string",
                "summary": "string",
                "climate_advice": ["string"],
                "local_typicals": {
                    "food": [{"name": "string", "note": "string", "how_to_order": "string"}],
                    "drinks": [{"name": "string", "note": "string", "how_to_order": "string"}]
                },
                "per_slot_order_tips": [
                    {"slot_id": "string", "tips": ["string"]}
                ],
                "practical_notes": ["string"]
            }
        }

        resp = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": sys},
                {"role": "user", "content": str(user)},
            ],
        )

        text = getattr(resp, "output_text", None) or ""
        import json
        guide = json.loads(text)
        # validar / normalizar
        parsed = LocalGuide(**guide).model_dump()
        return parsed


