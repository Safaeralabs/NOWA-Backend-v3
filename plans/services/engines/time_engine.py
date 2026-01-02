"""
Time-aware logic: opening hours, daypart modifiers
"""
from datetime import datetime, time, timedelta
from plans.constants.dayparts import get_daypart
from plans.constants.categories import get_category_metadata
import logging

logger = logging.getLogger(__name__)


def is_open_at(candidate, dt_local, duration_min):
    """
    Check if a place is open at a specific time
    
    Args:
        candidate: dict with place data including:
            - business_status
            - opening_hours (dict with periods or weekday_text)
        dt_local: datetime in local timezone
        duration_min: int, duration of visit in minutes
        
    Returns:
        tuple: (is_open: bool|None, confidence: str, reason: str)
            is_open: True (open), False (closed), None (unknown)
            confidence: 'high' | 'medium' | 'low'
            reason: explanation string
    """
    # Check business status first
    business_status = candidate.get('business_status', '').upper()
    if business_status == 'CLOSED_PERMANENTLY':
        return (False, 'high', 'permanently_closed')
    
    if business_status == 'CLOSED_TEMPORARILY':
        return (False, 'high', 'temporarily_closed')
    
    if business_status and business_status != 'OPERATIONAL':
        return (False, 'medium', f'not_operational:{business_status}')
    
    # Get opening hours data
    opening_hours = candidate.get('opening_hours', {})
    
    # No hours data
    if not opening_hours:
        return (None, 'low', 'missing_hours')
    
    # Check if we have detailed periods
    periods = opening_hours.get('periods', [])
    if periods:
        return _check_periods(periods, dt_local, duration_min)
    
    # Fallback to weekday_text parsing
    weekday_text = opening_hours.get('weekday_text', [])
    if weekday_text:
        return _check_weekday_text(weekday_text, dt_local, duration_min)
    
    # Has opening_hours dict but no useful data
    return (None, 'low', 'incomplete_hours_data')


def _check_periods(periods, dt_local, duration_min):
    """
    Check opening hours using Google Places periods format
    
    periods format:
    [
        {
            'open': {'day': 0, 'time': '0900'},  # day: 0=Sunday, 1=Monday...
            'close': {'day': 0, 'time': '1700'}
        },
        ...
    ]
    """
    try:
        # Get day of week (0=Sunday in Google Places)
        weekday = (dt_local.weekday() + 1) % 7  # Convert Python's Monday=0 to Google's Sunday=0
        
        # Time as HHMM integer
        current_time = dt_local.hour * 100 + dt_local.minute
        end_time_dt = dt_local + timedelta(minutes=duration_min)
        end_time = end_time_dt.hour * 100 + end_time_dt.minute
        
        # Check if end time crosses midnight
        crosses_midnight = end_time_dt.day != dt_local.day
        
        for period in periods:
            open_day = period.get('open', {}).get('day')
            open_time = period.get('open', {}).get('time', '0000')
            close_info = period.get('close', {})
            
            # Convert times to int
            try:
                open_time_int = int(open_time)
            except (ValueError, TypeError):
                continue
            
            # Handle 24/7 (no close time)
            if not close_info:
                if open_day == weekday:
                    return (True, 'high', 'open_24_7')
                continue
            
            close_day = close_info.get('day')
            close_time = close_info.get('time', '2359')
            
            try:
                close_time_int = int(close_time)
            except (ValueError, TypeError):
                continue
            
            # Check if this period applies to our day
            if open_day == weekday:
                # Handle overnight hours (e.g., open 18:00, close 02:00 next day)
                if close_day != open_day:
                    # Overnight period
                    if current_time >= open_time_int:
                        # We're in the opening part (before midnight)
                        if crosses_midnight:
                            # Visit crosses midnight, check if end time is before close
                            next_day = (weekday + 1) % 7
                            if close_day == next_day and end_time <= close_time_int:
                                return (True, 'high', 'periods_check_overnight')
                            return (False, 'high', 'closes_during_visit')
                        return (True, 'high', 'periods_check')
                else:
                    # Same-day period
                    if open_time_int <= current_time < close_time_int:
                        # Check if visit ends before closing
                        if end_time <= close_time_int or end_time < current_time:  # Handle midnight wrap
                            return (True, 'high', 'periods_check')
                        return (False, 'high', 'closes_during_visit')
            
            # Check if we're in the closing part of overnight hours from previous day
            if close_day == weekday and open_day != weekday:
                if current_time < close_time_int:
                    if end_time <= close_time_int:
                        return (True, 'high', 'periods_check_overnight_continuation')
                    return (False, 'high', 'closes_during_visit')
        
        # No matching period found
        return (False, 'high', 'closed_at_time')
        
    except Exception as e:
        logger.error(f"Error checking periods: {e}", exc_info=True)
        return (None, 'low', f'period_parsing_error:{str(e)[:50]}')


def _check_weekday_text(weekday_text, dt_local, duration_min):
    """
    Fallback: parse weekday_text if periods not available
    
    weekday_text format:
    [
        "Monday: 9:00 AM – 5:00 PM",
        "Tuesday: 9:00 AM – 5:00 PM",
        ...
    ]
    
    This is less reliable than periods, so confidence is 'medium'
    """
    try:
        # Map Python weekday to Google's format
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = weekday_names[dt_local.weekday()]
        
        # Find matching day in weekday_text
        matching_line = None
        for line in weekday_text:
            if line.startswith(day_name):
                matching_line = line
                break
        
        if not matching_line:
            return (None, 'low', 'weekday_text_no_match')
        
        # Check for "Closed"
        if 'Closed' in matching_line or 'closed' in matching_line:
            return (False, 'medium', 'weekday_text_closed')
        
        # Check for "Open 24 hours"
        if '24 hours' in matching_line or 'Open 24 hours' in matching_line:
            return (True, 'medium', 'weekday_text_24h')
        
        # Try to parse hours (basic parsing, not bullet-proof)
        # This is simplified - production should use regex or proper parsing
        if '–' in matching_line or '-' in matching_line:
            # Likely has hours
            return (True, 'medium', 'weekday_text_likely_open')
        
        return (None, 'low', 'weekday_text_unparseable')
        
    except Exception as e:
        logger.error(f"Error parsing weekday_text: {e}", exc_info=True)
        return (None, 'low', f'weekday_text_error:{str(e)[:50]}')


def daypart_category_modifier(daypart, category, mode, theme):
    """
    Calculate category score modifier based on time of day
    
    Args:
        daypart: 'morning' | 'midday' | 'afternoon' | 'evening' | 'late'
        category: internal category name
        mode: 'today' | 'travel' | 'date'
        theme: theme string or None
        
    Returns:
        float: modifier to add to score (-3.0 to +2.0)
    """
    # Get category metadata
    metadata = get_category_metadata(category)
    
    # Base modifiers by daypart and category
    modifiers = {
        'morning': {
            'cafe': 1.5,
            'bakery': 1.3,
            'park': 1.2,
            'fitness': 1.0,
            'bar': -2.5,
            'nightclub': -3.0,
            'nightlife': -2.0,
        },
        'midday': {
            'restaurant': 1.2,
            'casual_dining': 1.3,
            'cafe': 1.0,
            'museum': 1.1,
            'shopping': 1.0,
            'bar': -1.5,
            'nightclub': -3.0,
        },
        'afternoon': {
            'cafe': 1.2,
            'park': 1.1,
            'gallery': 1.0,
            'shopping': 1.0,
            'nightclub': -2.5,
        },
        'evening': {
            'restaurant': 1.5,
            'bar': 1.2,
            'viewpoint': 1.1,
            'performance': 1.3,
            'nightclub': -0.5,  # Still early for clubs
        },
        'late': {
            'bar': 1.0,
            'nightclub': 0.5,
            'nightlife': 1.0,
            'restaurant': -1.0,
            'cafe': -2.0,
            'museum': -3.0,
            'park': -2.0,
        },
    }
    
    base_modifier = modifiers.get(daypart, {}).get(category, 0.0)
    
    # Theme-specific overrides
    if theme == 'night_vibe' and mode == 'date':
        # Night Vibe allows bars/clubs earlier
        if daypart in ['evening', 'late'] and category in ['bar', 'nightclub', 'nightlife']:
            base_modifier = min(base_modifier + 1.5, 2.0)
    
    if theme in ['sport_move', 'sport_stadiums', 'active_date']:
        # Sport themes penalize late-night
        if daypart == 'late' and category in ['sport_venue', 'fitness', 'pool']:
            base_modifier -= 2.0
    
    if theme == 'conversation_first' and mode == 'date':
        # Extra penalty for loud venues at all times
        if metadata.get('noise_level') in ['high', 'very_high']:
            base_modifier -= 1.0
    
    # Metadata-based adjustments
    if metadata.get('evening_only') and daypart in ['morning', 'midday']:
        base_modifier -= 2.0
    
    if metadata.get('late_night_only') and daypart not in ['late']:
        base_modifier -= 2.5
    
    return base_modifier


def calculate_slot_time(plan, slot_index, previous_stops=None):
    """
    Calculate when a slot will start based on previous stops and travel times
    
    Args:
        plan: Plan object
        slot_index: int, index of the slot (0-based)
        previous_stops: list of already-scheduled Stop objects
        
    Returns:
        datetime: estimated start time in local timezone
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Get plan start time
    start_time = plan.start_time_utc
    timezone_str = plan.inputs_json.get('timezone', 'UTC')
    
    try:
        tz = pytz.timezone(timezone_str)
        dt_local = start_time.astimezone(tz)
    except Exception:
        dt_local = start_time
    
    if slot_index == 0 or not previous_stops:
        return dt_local
    
    # Add up durations and travel times from previous stops
    cumulative_minutes = 0
    
    for stop in previous_stops[:slot_index]:
        # Add stop duration
        cumulative_minutes += stop.duration_min or 60
        
        # Add travel time from leg (if exists)
        # This would require querying Legs, simplified here
        cumulative_minutes += 15  # Assume 15min average travel
    
    return dt_local + timedelta(minutes=cumulative_minutes)