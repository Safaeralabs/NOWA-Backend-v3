import logging
from decimal import Decimal
from typing import Any, Dict, Optional

import pytz
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Plan, Stop, Leg

from .engineV3.engine import V3PlannerEngine
from .engineV3.llm import SlotLLM
from .engineV3.providers import Providers as V3Providers
from .engineV3.providers.google_places_provider import build_google_places_provider
from .engineV3.providers.weather_provider import build_weather_provider
from .engineV3.providers.google_directions_provider import build_google_directions_provider

logger = logging.getLogger(__name__)

import datetime
import uuid
from decimal import Decimal

def make_json_safe(obj):
    """
    Recursively convert obj to JSON-serializable types:
    - datetime/date/time -> isoformat
    - Decimal -> float
    - UUID -> str
    - set/tuple -> list
    - dict/list -> recurse
    - Pydantic -> model_dump if present
    """
    if obj is None:
        return None

    # Pydantic v2
    if hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump())

    # datetime-like
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, uuid.UUID):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(x) for x in obj]

    # primitives
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # fallback
    return str(obj)

def _to_decimal(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _get_tz(inputs: Dict[str, Any]) -> pytz.BaseTzInfo:
    tz_str = (inputs.get("timezone") or "Europe/Berlin").strip()
    try:
        return pytz.timezone(tz_str)
    except Exception:
        return pytz.timezone("Europe/Berlin")


def _validate_inputs(inputs: Dict[str, Any]) -> None:
    city = inputs.get("city_name") or inputs.get("city")
    loc = inputs.get("user_location") or inputs.get("current_location")
    if not city:
        raise ValueError("inputs_json missing city_name/city")
    if not loc or "lat" not in loc or "lng" not in loc:
        raise ValueError("inputs_json missing user_location/current_location with lat/lng")


def _build_engine(inputs: Dict[str, Any]) -> V3PlannerEngine:
    places = build_google_places_provider()
    weather = build_weather_provider()

    providers = V3Providers(
        places=places,
        weather=weather,
        directions=None,  # engine core returns legs=[], we persist legs in task
        language="es",
        region=None,
    )

    # Optional OpenAI client (only for copy + soft pick)
    use_llm = bool(inputs.get("use_llm", False))
    client = None
    if use_llm:
        from openai import OpenAI
        client = OpenAI()

    llm = SlotLLM(client=client, model=inputs.get("llm_model") or "gpt-4o-mini")
    engine = V3PlannerEngine(providers=providers, llm=llm)

    # Attach directions provider for leg-building
    engine._directions_provider = build_google_directions_provider()
    return engine


def _derive_open_confidence(open_status: Optional[bool], open_conf: Optional[str]) -> str:
    """
    Your model allows '' as default/unknown.
    - If open_status is None => unknown => ''
    - Else use provided open_conf if valid, else 'low'
    """
    if open_status is None:
        return ""
    if open_conf in ("high", "medium", "low"):
        return open_conf
    return "low"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def generate_plan_task(self, plan_id: str) -> bool:
    logger.info("V3 generate_plan_task start plan_id=%s", plan_id)

    plan = Plan.objects.get(id=plan_id)
    inputs: Dict[str, Any] = plan.inputs_json or {}

    _validate_inputs(inputs)

    tz = _get_tz(inputs)
    dt_local = plan.start_time_utc.astimezone(tz)

    city_name = inputs.get("city_name") or inputs.get("city")
    user_location = inputs.get("user_location") or inputs.get("current_location")

    engine = _build_engine(inputs)

    # Weather mandatory (provider returns fallback if API fails)
    weather_snapshot = engine.providers.get_weather(user_location=user_location)

    result = engine.generate(
        inputs={
            "intent": inputs.get("intent") or "chill",
            "when_selection": inputs.get("when_selection") or "now",
            "discovery_mode": inputs.get("discovery_mode") or "local",
            "constraints": inputs.get("constraints") or [],
            "city_name": city_name,
            "user_location": user_location,
        },
        context={
            "dt_local": dt_local,
            "user_location": user_location,
            "weather": weather_snapshot,
        },
    )

    with transaction.atomic():
        plan = Plan.objects.select_for_update().get(id=plan_id)

        plan.status = "building"
        plan.last_error_code = None
        plan.last_error_context = None
        plan.weather_snapshot_json = make_json_safe(weather_snapshot)


        # optional bookkeeping
        if inputs.get("use_llm"):
            plan.generation_method = "llm"
            plan.llm_attempts = (plan.llm_attempts or 0) + 1
        else:
            plan.generation_method = "fallback"

        plan.save(update_fields=[
            "status",
            "last_error_code",
            "last_error_context",
            "weather_snapshot_json",
            "generation_method",
            "llm_attempts",
        ])

        # Clear old results
        plan.stops.all().delete()
        plan.legs.all().delete()
        meta = plan.optimization_metadata or {}
        v3 = meta.get("v3") or {}

        # 1) guardar slots/debug (si ya lo haces, deja esto igual)
        v3["slots"] = result.slots
        v3["debug"] = result.debug
        v3["city_dna"] = make_json_safe(city_dna)
        v3["guide"] = make_json_safe(guide)

        # 2) City DNA cacheado 30 días
        city_name = (inputs.get("city_name") or inputs.get("city") or "").strip()
        city_dna = engine.llm.get_city_dna(city=city_name, language="es")
        v3["city_dna"] = city_dna

        # 3) Construir options_by_slot desde result.slots (o tu estructura real)
        # Si tus slots ya incluyen options, úsalo directo. Si no, arma la lista.
        options_by_slot = []
        for slot in (result.slots or []):
            slot_id = slot.get("slot_id")
            opts = []
            for opt in (slot.get("options") or []):
                p = opt.get("place") or {}
                opts.append({
                    "place_id": p.get("place_id"),
                    "name": p.get("name"),
                    "category": p.get("category"),
                    "rating": p.get("rating"),
                    "distance_m": opt.get("distance_m"),
                    "open": p.get("open_now"),
                    "open_confidence": p.get("open_confidence"),
                })
            options_by_slot.append({"slot_id": slot_id, "options": opts})

        # 4) LLM guía local (qué pedir / típico / tips clima)
        guide = engine.llm.build_local_guide(
            city_dna=city_dna,
            intent=(inputs.get("intent") or "chill"),
            subtypes=(inputs.get("intent_subtype") or []),
            weather=weather_snapshot,
            options_by_slot=options_by_slot,
            constraints=(inputs.get("constraints") or []),
            language="es",
        )
        v3["guide"] = guide

        meta["v3"] = v3
        plan.optimization_metadata = make_json_safe(meta)
        plan.save(update_fields=["optimization_metadata"])

        # Create stops with COMPACT order_index
        created_stops = []
        idx = 0
        for st in (result.chosen_stops or []):
            # ensure required coords exist
            if st.get("lat") is None or st.get("lng") is None:
                continue

            start_utc = st["start"].astimezone(pytz.UTC)

            why_now_long = str(st.get("why_now") or "").strip()
            why_now_short = (why_now_long[:50] or None)

            open_status = st.get("open_status")  # True/False/None
            open_conf = _derive_open_confidence(open_status, st.get("open_confidence"))

            stop = Stop.objects.create(
                plan=plan,
                order_index=idx,
                place_provider="google",
                place_id=str(st.get("place_id")),
                name=str(st.get("name") or ""),

                lat=_to_decimal(st.get("lat")),
                lng=_to_decimal(st.get("lng")),

                category=str(st.get("category") or "other"),
                tags=[],

                start_time_utc=start_utc,
                duration_min=int(st.get("duration_min") or 45),

                priority="nice",
                reason_short=why_now_long,
                ai_reasoning=why_now_long,

                # optional signals (safe defaults)
                is_indoor=None,
                price_level=None,
                rating=None,
                queue_score=1,
                crowd_score=1,
                noise_level=1,
                is_tourist_trap=False,
                local_favorite=False,
                closing_time=None,
                peak_hours=[],
                rank_in_cluster=0,

                # opening-hours + status
                business_status=st.get("business_status"),
                opening_hours_json=st.get("opening_hours_json"),
                open_status_at_planned_time=open_status,
                open_confidence=open_conf,
                open_status_reason=st.get("open_reason"),

                place_types=st.get("place_types"),
                popularity=st.get("popularity"),
                photo_reference=st.get("photo_reference"),

                why_now=why_now_short,
                score_breakdown={
                    "engine": "v3",
                    "slot_id": st.get("slot_id"),
                    "slot_title": st.get("slot_title"),
                },

                when_selection=inputs.get("when_selection", "now"),
                slot_role=st.get("slot_role"),

                closed_warning=(open_status is False),
                closed_reason=(st.get("open_reason") or "") if open_status is False else "",
                hours_unknown=(open_status is None),
            )

            created_stops.append(stop)
            idx += 1

        # Create legs between consecutive stops
        for i in range(len(created_stops) - 1):
            a = created_stops[i]
            b = created_stops[i + 1]

            origin = (float(a.lat), float(a.lng))
            dest = (float(b.lat), float(b.lng))

            modes_json = {}
            for mode in ["walk", "bike", "drive"]:
                try:
                    modes_json[mode] = engine._directions_provider.get_directions(
                        origin=origin,
                        destination=dest,
                        mode=mode,
                        language="es",
                    )
                except Exception:
                    modes_json[mode] = {"distance_m": 0, "duration_sec": 0, "polyline": None}

            walk_dist = modes_json.get("walk", {}).get("distance_m", 0) or 0
            recommended_mode = "walk" if (walk_dist and walk_dist <= 1500) else "drive"

            Leg.objects.create(
                plan=plan,
                from_stop=a,
                to_stop=b,
                modes_json=modes_json,
                recommended_mode=recommended_mode,
                recommended_distance_m=int(modes_json.get(recommended_mode, {}).get("distance_m", 0) or 0),
                recommended_duration_sec=int(modes_json.get(recommended_mode, {}).get("duration_sec", 0) or 0),
                recommended_reason="Auto (V3 core)",
                ai_pick_reason="",
                travel_warning="",
            )

        plan.status = "ready"
        plan.save(update_fields=["status"])

    logger.info("V3 generate_plan_task success plan_id=%s stops=%d", plan_id, len(result.chosen_stops or []))
    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def regenerate_plan_task(self, plan_id: str) -> bool:
    return generate_plan_task(plan_id)


@shared_task(bind=True)
def swap_stop_task():
    """
    V3 stub: por ahora no implementado.
    Mantiene compatibilidad con views.py y rutas existentes.
    """
    """
    V3 stub: por ahora no implementado.
    """
    print("swap_stop_task")



@shared_task(bind=True)
def delay_replan_task():
    """
    V3 stub: por ahora no implementado.
    """
    print("delay_replan_task")



@shared_task(bind=True)
def undo_swap_task():
    """
    V3 stub: por ahora no implementado.
    """
    print("UNDO SWAP")
