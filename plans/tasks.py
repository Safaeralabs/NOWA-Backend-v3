import logging
from decimal import Decimal
from typing import Any, Dict, Optional
import traceback
import time

import pytz
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from .models import Plan, Stop, Leg

from .engineV3.engine import V3PlannerEngine
from .engineV3.llm import SlotLLM
from .engineV3.providers import Providers as V3Providers
from .engineV3.providers.google_places_provider import build_google_places_provider
from .engineV3.providers.weather_provider import build_weather_provider
from .engineV3.providers.google_directions_provider import build_google_directions_provider

logger = logging.getLogger(__name__)


def safe_cache_incr(key, delta=1, default=0):
    """
    Safely increment cache key (creates if doesn't exist).
    Django's cache.incr() fails if key doesn't exist.
    """
    try:
        return cache.incr(key, delta)
    except ValueError:
        # Key doesn't exist, initialize and return
        cache.set(key, default + delta, None)
        return default + delta


import datetime
import uuid
from decimal import Decimal


def make_json_safe(obj):
    """
    Recursively convert obj to JSON-serializable types:
    - datetime/date/time → isoformat
    - Decimal → float
    - UUID → str
    - set/tuple → list
    - dict/list → recurse
    - Pydantic → model_dump if present
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
    """Build V3 engine with providers + optional LLM"""
    places = build_google_places_provider()
    weather = build_weather_provider()

    providers = V3Providers(
        places=places,
        weather=weather,
        directions=None,  # engine core returns legs=[], we build legs in task
        language="es",
        region=None,
    )

    # Optional OpenAI client (only for guide copy + soft pick)
    use_llm = bool(inputs.get("use_llm", False))
    client = None
    if use_llm:
        try:
            from openai import OpenAI
            client = OpenAI()
            logger.info("LLM enabled: using OpenAI")
        except Exception as e:
            logger.warning(f"LLM client creation failed: {e}. Using fallback.")
            client = None

    llm = SlotLLM(client=client, model=inputs.get("llm_model") or "gpt-4o-mini")
    engine = V3PlannerEngine(providers=providers, llm=llm)

    # Attach directions provider for leg-building
    engine._directions_provider = build_google_directions_provider()
    return engine


def _derive_open_confidence(open_status: Optional[bool], open_conf: Optional[str]) -> str:
    """
    Model allows '' as default/unknown.
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
    """
    V3 Plan Generation Task
    
    Steps:
    1. Validate inputs
    2. Fetch weather (mandatory)
    3. Build engine (providers + LLM)
    4. Generate plan (slots, scoring, selection)
    5. Calculate city_dna + guide BEFORE saving metadata ← FIX
    6. Persist stops + legs
    7. Mark plan ready
    """
    start_time = time.time()
    logger.info(f"    V3 generate_plan_task START plan_id={plan_id}")

    try:
        plan = Plan.objects.get(id=plan_id)
        inputs: Dict[str, Any] = plan.inputs_json or {}

        # Validate
        _validate_inputs(inputs)

        tz = _get_tz(inputs)
        dt_local = plan.start_time_utc.astimezone(tz)

        city_name = inputs.get("city_name") or inputs.get("city")
        user_location = inputs.get("user_location") or inputs.get("current_location")

        logger.info(f"    Plan {plan_id}: city={city_name}, dt={dt_local.isoformat()}")

        # Build engine
        engine = _build_engine(inputs)

        # Weather mandatory (provider returns fallback if API fails)
        logger.info(f"   Fetching weather for {city_name}...")
        weather_snapshot = engine.providers.get_weather(user_location=user_location)
        logger.info(f"    Weather: {weather_snapshot.get('temp')}°C, {weather_snapshot.get('condition')}")

        # Generate plan
        logger.info(f"    Generating plan with intent={inputs.get('intent')}...")
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

        logger.info(f"    Plan generated: {len(result.chosen_stops)} stops, {len(result.slots)} slots")

        # ========== CRITICAL: Save everything in transaction ==========
        with transaction.atomic():
            plan = Plan.objects.select_for_update().get(id=plan_id)

            plan.status = "building"
            plan.last_error_code = None
            plan.last_error_context = None
            plan.weather_snapshot_json = make_json_safe(weather_snapshot)

            # Track generation method
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

            # ========== FIX: Calculate city_dna & guide BEFORE saving metadata ==========
            meta = plan.optimization_metadata or {}
            v3 = meta.get("v3") or {}

            # 1) City DNA (cached 30 days)
            logger.info(f"    Getting City DNA for {city_name}...")
            city_name_clean = (city_name or "").strip()
            city_dna = engine.llm.get_city_dna(city=city_name_clean, language="es")
            logger.info(f"    City DNA: {len(city_dna.get('food_typicals', []))} foods, {len(city_dna.get('drink_typicals', []))} drinks")

            # 2) Guardar slots/debug
            v3["slots"] = make_json_safe(result.slots)
            v3["debug"] = make_json_safe(result.debug)
            v3["city_dna"] = make_json_safe(city_dna)

            # 3) Build options_by_slot (for guide + presentation endpoint)
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
                        "open": opt.get("open"),
                        "open_confidence": opt.get("open_confidence"),
                    })
                options_by_slot.append({"slot_id": slot_id, "options": opts})

            # 4) LLM local guide (qué pedir / típico / tips clima)
            logger.info(f"    Building local guide...")
            guide = engine.llm.build_local_guide(
                city_dna=city_dna,
                intent=(inputs.get("intent") or "chill"),
                subtypes=(inputs.get("intent_subtype") or []),
                weather=weather_snapshot,
                options_by_slot=options_by_slot,
                constraints=(inputs.get("constraints") or []),
                language="es",
            )
            logger.info(f"    Guide: {guide.get('headline')}")

            v3["guide"] = make_json_safe(guide)
            v3["options_by_slot"] = make_json_safe(options_by_slot)

            # 5) NOW save metadata (with city_dna + guide included!)
            meta["v3"] = v3
            plan.optimization_metadata = make_json_safe(meta)
            plan.save(update_fields=["optimization_metadata"])

            logger.info(f"    Metadata saved (city_dna + guide included)")

            # ========== Create stops with COMPACT order_index ==========
            created_stops = []
            idx = 0
            
            for st in (result.chosen_stops or []):
                # Ensure required coords exist
                if st.get("lat") is None or st.get("lng") is None:
                    logger.warning(f"    Skipping stop without coordinates: {st.get('name')}")
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

                    # Optional signals
                    is_indoor=None,
                    price_level=None,
                    rating=st.get("rating"),
                    queue_score=1,
                    crowd_score=1,
                    noise_level=1,
                    is_tourist_trap=False,
                    local_favorite=False,
                    closing_time=None,
                    peak_hours=[],
                    rank_in_cluster=0,

                    # Opening hours + status
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

            logger.info(f"    Created {len(created_stops)} stops")

            # ========== Create legs between consecutive stops ==========
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
                    except Exception as e:
                        logger.warning(f"    Directions failed for {mode}: {e}")
                        modes_json[mode] = {"distance_m": 0, "duration_sec": 0, "polyline": None}

                walk_dist = modes_json.get("walk", {}).get("distance_m", 0) or 0
                
                # Recommended mode logic
                if "no_walk" in (inputs.get("constraints") or []):
                    recommended_mode = "drive"
                elif walk_dist and walk_dist <= 1500:
                    recommended_mode = "walk"
                else:
                    recommended_mode = "drive"

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

            logger.info(f"    Created {len(created_stops) - 1} legs")

            # ========== Plan ready ==========
            plan.status = "ready"
            plan.save(update_fields=["status"])

        # Metrics
        duration = time.time() - start_time
        logger.info(f"    V3 generate_plan_task SUCCESS plan_id={plan_id}, stops={len(created_stops)}, duration={duration:.2f}s")
        
        # Track metrics
        safe_cache_incr('metrics:plan_generation_count', 1)
        safe_cache_incr('metrics:plan_generation_time', int(duration))

        return True

    except Exception as e:
        logger.error(f"    Plan {plan_id} FAILED: {e}", exc_info=True)
        
        # Save error context
        try:
            plan = Plan.objects.get(id=plan_id)
            plan.status = "failed"
            plan.last_error_code = type(e).__name__
            plan.last_error_context = {
                "error": str(e),
                "traceback": traceback.format_exc()[:2000],  # Limit size
                "inputs": plan.inputs_json,
            }
            plan.save()
        except Exception as save_error:
            logger.error(f"Failed to save error context: {save_error}")
        
        # Track failure
        safe_cache_incr('metrics:plan_generation_failures', 1)
        
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def regenerate_plan_task(self, plan_id: str) -> bool:
    """Regenerate an existing plan"""
    logger.info(f"    Regenerating plan {plan_id}")
    return generate_plan_task(plan_id)


@shared_task(bind=True)
def swap_stop_task(self, plan_id: str, stop_id: str, reason: str):
    """
    V3 stub: swap stop functionality
    TODO: Implement stop swapping logic
    """
    logger.info(f"    swap_stop_task: plan={plan_id}, stop={stop_id}, reason={reason}")
    
    try:
        plan = Plan.objects.get(id=plan_id)
        stop = Stop.objects.get(id=stop_id, plan=plan)
        
        # TODO: Implement actual swap logic
        # For now, just mark plan as ready again
        plan.status = "ready"
        plan.save()
        
        logger.info(f"    Swap completed (stub)")
        return True
        
    except Exception as e:
        logger.error(f"    Swap failed: {e}", exc_info=True)
        
        try:
            plan = Plan.objects.get(id=plan_id)
            plan.status = "ready"  # Restore to ready
            plan.save()
        except:
            pass
        
        raise


@shared_task(bind=True)
def delay_replan_task(self, plan_id: str, stop_id: str, delta_min: int):
    """
    V3 stub: delay and replan
    TODO: Implement delay logic
    """
    logger.info(f"    delay_replan_task: plan={plan_id}, stop={stop_id}, delta={delta_min}min")
    
    try:
        plan = Plan.objects.get(id=plan_id)
        
        # TODO: Implement actual delay logic
        # For now, just mark as ready
        plan.status = "ready"
        plan.save()
        
        logger.info(f"    Delay completed (stub)")
        return True
        
    except Exception as e:
        logger.error(f"    Delay failed: {e}", exc_info=True)
        raise


@shared_task(bind=True)
def undo_swap_task(self, plan_id: str, stop_id: str):
    """
    V3 stub: undo last swap
    TODO: Implement undo logic
    """
    logger.info(f"    undo_swap_task: plan={plan_id}, stop={stop_id}")
    
    try:
        plan = Plan.objects.get(id=plan_id)
        stop = Stop.objects.get(id=stop_id, plan=plan)
        
        if not stop.previous_stop_data:
            logger.warning(f"    No previous data to restore for stop {stop_id}")
            plan.status = "ready"
            plan.save()
            return False
        
        # TODO: Implement actual undo logic
        plan.status = "ready"
        plan.save()
        
        logger.info(f"    Undo completed (stub)")
        return True
        
    except Exception as e:
        logger.error(f"    Undo failed: {e}", exc_info=True)
        raise