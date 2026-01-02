from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class WeatherProfile:
    cold: bool
    very_cold: bool
    rain: bool
    snow: bool
    windy: bool
    pleasant: bool
    confidence: str

def build_weather_profile(weather: Dict[str, Any]) -> WeatherProfile:
    temp = weather.get("temp")
    feels = weather.get("feels_like", temp)
    cond = (weather.get("condition") or "").lower()

    rain = bool(weather.get("is_raining")) or ("rain" in cond) or ("drizzle" in cond)
    snow = bool(weather.get("is_snowing")) or ("snow" in cond)
    windy = bool(weather.get("windy")) or ("wind" in cond)

    if feels is None:
        # fallback conservador
        return WeatherProfile(
            cold=False, very_cold=False, rain=rain, snow=snow, windy=windy,
            pleasant=True, confidence=weather.get("confidence", "low")
        )

    cold = feels <= 8
    very_cold = feels <= 2
    pleasant = (10 <= feels <= 22) and not rain and not snow and not windy

    return WeatherProfile(
        cold=cold,
        very_cold=very_cold,
        rain=rain,
        snow=snow,
        windy=windy,
        pleasant=pleasant,
        confidence=weather.get("confidence", "high")
    )

# --------------------------
# Dayparts (determinístico)
# --------------------------
def get_daypart(dt: datetime) -> str:
    h = dt.hour
    if 6 <= h < 11:
        return "morning"
    if 11 <= h < 15:
        return "midday"
    if 15 <= h < 18:
        return "afternoon"
    if 18 <= h < 22:
        return "evening"
    return "late"

# “No bar 11am”: suitability por daypart (soft/hard según uses)
CATEGORY_DAYPART_ALLOWED = {
    "bar": {"evening", "late"},
    "cocktail_bar": {"evening", "late"},
    "wine_bar": {"evening", "late"},
    "hotel_bar": {"evening", "late"},
    "nightclub": {"late"},
    "museum": {"morning", "midday", "afternoon"},
    "shopping_area": {"morning", "midday", "afternoon", "evening"},
    "market": {"morning", "midday", "afternoon"},
    "boutique": {"morning", "midday", "afternoon", "evening"},
    "concept_store": {"morning", "midday", "afternoon", "evening"},
    "vintage": {"morning", "midday", "afternoon", "evening"},
    "cafe": {"morning", "midday", "afternoon", "evening"},
    "bakery": {"morning", "midday", "afternoon"},
    "dessert": {"afternoon", "evening", "late"},
    "late_food": {"late"},
    "fast_food": {"midday", "afternoon", "evening", "late"},
    "cinema": {"evening", "late", "afternoon"},
    "theater": {"evening", "late"},
    "jazz_bar": {"evening", "late"},
    "cultural_bar": {"evening", "late"},
    "photo_spot": {"morning", "midday", "afternoon", "evening"},
    "viewpoint": {"morning", "midday", "afternoon", "evening"},
    "street_art": {"morning", "midday", "afternoon", "evening"},
}

def is_category_suitable(category: str, daypart: str) -> bool:
    allowed = CATEGORY_DAYPART_ALLOWED.get(category)
    if not allowed:
        return True
    return daypart in allowed

# --------------------------
# Open-hours evaluation
# --------------------------
@dataclass(frozen=True)
class OpenStatus:
    is_open: Optional[bool]  # True/False/None
    confidence: str          # "high"|"medium"|"low"
    reason: str              # e.g. "open_now", "closed_now", "hours_missing", "unknown"

def _weekday_google(dt: datetime) -> int:
    """
    Google uses 0=Sunday..6=Saturday in opening_hours.periods[].open.day
    Python weekday(): Monday=0..Sunday=6
    """
    py = dt.weekday()
    return (py + 1) % 7  # Monday->1 ... Sunday->0

def _parse_hhmm(hhmm: str) -> time:
    # "1730" -> 17:30
    if not hhmm or len(hhmm) != 4:
        return time(0, 0)
    return time(int(hhmm[:2]), int(hhmm[2:]))

def _dt_at_local_date(dt: datetime, t: time) -> datetime:
    return dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

def compute_open_status(place: Dict[str, Any], start_dt: datetime, duration_min: int) -> OpenStatus:
    """
    Uses Google Places-like structure if present:
      place["opening_hours"]["periods"] = [{open:{day,time}, close:{day,time}} ...]
    If missing or unparseable -> is_open=None with low confidence.
    """
    oh = place.get("opening_hours") or place.get("opening_hours_json") or {}
    periods = oh.get("periods") if isinstance(oh, dict) else None

    if not periods or not isinstance(periods, list):
        return OpenStatus(None, "low", "hours_missing")

    end_dt = start_dt + timedelta(minutes=duration_min)
    wd = _weekday_google(start_dt)

    # Build candidate open intervals for the relevant day (and possible overnight crossing)
    intervals: List[Tuple[datetime, datetime]] = []

    for p in periods:
        o = (p or {}).get("open")
        c = (p or {}).get("close")
        if not o or not isinstance(o, dict) or "day" not in o or "time" not in o:
            continue

        o_day = int(o["day"])
        o_time = _parse_hhmm(str(o["time"]))

        # Some businesses may be "open 24 hours" represented oddly; handle best-effort.
        if not c or not isinstance(c, dict) or "day" not in c or "time" not in c:
            # If close missing, assume unknown but likely open; we don't hard-true it.
            continue

        c_day = int(c["day"])
        c_time = _parse_hhmm(str(c["time"]))

        # Only consider periods that could cover start_dt's weekday (including overnight)
        # We'll map them to datetimes around start_dt date.
        # Create a base date aligned to start_dt
        base = start_dt
        # Compute open datetime
        # If o_day matches wd, open on base date; otherwise shift by day difference
        delta_open_days = (o_day - wd) % 7
        open_dt = _dt_at_local_date(base + timedelta(days=delta_open_days), o_time)

        delta_close_days = (c_day - wd) % 7
        close_dt = _dt_at_local_date(base + timedelta(days=delta_close_days), c_time)

        # If close is "earlier" than open due to overnight but same computed date, fix by +7? (rare)
        if close_dt <= open_dt:
            close_dt = close_dt + timedelta(days=1)

        intervals.append((open_dt, close_dt))

    if not intervals:
        return OpenStatus(None, "low", "hours_unusable")

    # Determine if the entire requested window [start_dt, end_dt] is within any interval
    for open_dt, close_dt in intervals:
        if open_dt <= start_dt and end_dt <= close_dt:
            return OpenStatus(True, "high", "open_for_slot")

    # If start is within an interval but end isn't, it’s closing soon
    for open_dt, close_dt in intervals:
        if open_dt <= start_dt < close_dt and end_dt > close_dt:
            return OpenStatus(True, "medium", "open_but_closing_during_slot")

    # Otherwise closed
    return OpenStatus(False, "high", "closed_for_slot")
