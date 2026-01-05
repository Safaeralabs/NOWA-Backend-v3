from rest_framework import serializers
from .models import Plan, Stop, Leg, StopFeedback, Profile, SavedPlace
from datetime import datetime, timedelta
import pytz


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'user', 'preferences_json', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = [
            'id', 'plan', 'order_index', 'place_provider', 'place_id',
            'name', 'lat', 'lng', 'category', 'tags',
            'cluster_id', 'cluster_name',
            'start_time_utc', 'duration_min', 'priority', 'reason_short',
            'is_indoor', 'price_level', 'rating',
            'queue_score', 'crowd_score', 'noise_level',
            'is_tourist_trap', 'local_favorite', 'photo_reference',
            'closing_time', 'peak_hours',
            'ai_reasoning', 'rank_in_cluster',
            'open_status_json', 'created_at', 'updated_at',
            # ========== NEW FIELDS (THEME ENGINE V2) ==========
            'planned_daypart',
            'business_status',
            'opening_hours_json',
            'open_status_at_planned_time',
            'open_confidence',
            'open_status_reason',
            'place_types',
            'popularity',
            'why_now',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'open_label']

    def get_open_label(self, obj):
        if obj.open_status_at_planned_time is True:
            return "Open"
        elif obj.open_status_at_planned_time is False:
            return "Closed"
        return "Hours unknown"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['open_label'] = self.get_open_label(instance)
        return data


class LegSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leg
        fields = [
            'id', 'plan', 'from_stop', 'to_stop',
            'modes_json', 'recommended_mode',
            'recommended_duration_sec', 'recommended_distance_m',
            'recommended_reason', 'ai_pick_reason', 'travel_warning',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PlanListSerializer(serializers.ModelSerializer):
    stop_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id', 'user', 'status',
            'start_time_utc', 'end_time_utc',
            'route_quality_score', 'clusters_visited',
            'stop_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_stop_count(self, obj):
        return obj.stops.count()


class PlanDetailSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    legs = LegSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id', 'user', 'status',
            'inputs_json', 'start_time_utc', 'end_time_utc',
            'weather_snapshot_json',
            'route_quality_score', 'total_walking_distance_m',
            'clusters_visited', 'optimization_metadata',
            'stops', 'legs',
            'created_at', 'updated_at',
            # ========== NEW FIELDS (THEME ENGINE V2) ==========
            'theme',
            'budget_feeling',
            'last_error_code',
            'last_error_context',
        ]
        read_only_fields = [
            'id', 'user', 'route_quality_score',
            'total_walking_distance_m', 'clusters_visited',
            'optimization_metadata', 'created_at', 'updated_at'
        ]


class PlanInputSerializer(serializers.Serializer):
    """
    Input serializer for plan generation (LEGACY NAME)
    Now extended to support V3 inputs while keeping V2 compatibility.
    """

    # ---------------------------
    # Location & Time
    # ---------------------------
    city_name = serializers.CharField(max_length=200)

    # NOTE: In current API you pass lat/lng at top level.
    # We'll still accept them, and Views will always build current_location.
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)

    # IMPORTANT: validate() uses timezone; it previously didn't exist.
    timezone = serializers.CharField(required=False, default='Europe/Berlin')

    # start/end are accepted, but validate() may override based on when_selection.
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)

    # ---------------------------
    # V2 Mode & Mood (kept)
    # ---------------------------
    mode = serializers.ChoiceField(choices=['today', 'travel', 'date'], default='today')
    mood = serializers.ChoiceField(
        choices=['cozy', 'curious', 'fun', 'memorable', 'surprise'],
        default='curious'
    )

    # Vibe Sliders (kept)
    energy = serializers.IntegerField(min_value=0, max_value=3, default=2)
    social = serializers.IntegerField(min_value=0, max_value=3, default=2)
    friction_tolerance = serializers.IntegerField(min_value=0, max_value=3, default=2)

    # Budget (kept)
    budget = serializers.ChoiceField(
        choices=['cheap', 'normal', 'treat_myself'],
        default='normal'
    )

    # Toggles (kept)
    avoid = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    indoor_ok = serializers.BooleanField(default=True)
    outdoor_ok = serializers.BooleanField(default=True)

    # ---------------------------
    # Theme Engine V2 (kept)
    # ---------------------------
    theme = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    budget_feeling = serializers.ChoiceField(
        choices=['cheap', 'normal', 'treat_myself'],
        required=False,
        allow_null=True
    )
    when_selection = serializers.ChoiceField(
        choices=['now', 'later_today', 'tonight', 'tomorrow'],
        required=False,
        default='now'
    )

    # =====================================================
    # V3 INPUTS (NEW) - the ones the V3 engine actually uses
    # =====================================================

    # Versioning / toggles
    engine_version = serializers.ChoiceField(choices=['v2', 'v3'], required=False, default='v3')

    # Core V3 intent
    intent = serializers.CharField(required=False, default='chill')
    
    # ========== FIX: Aceptar "mixed" en discovery_mode ==========
    discovery_mode = serializers.ChoiceField(
        choices=['local', 'tourist', 'mixed'],  # ← FIXED: agregar "mixed"
        required=False, 
        default='local'
    )

    # Constraints (V3)
    constraints = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

    # LLM controls (V3)
    use_llm = serializers.BooleanField(required=False, default=True)
    llm_model = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='gpt-4o-mini')

    # Optional "copy-only" inputs
    companions = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Optional manual weather override (for QA/testing)
    weather = serializers.DictField(required=False)

    def validate(self, attrs):
        """
        Map when_selection to actual start_time & end_time.
        
        ========== FIX: Respetar start_time explícito ==========
        """
        when = attrs.get('when_selection', 'now')
        timezone_str = attrs.get('timezone', 'Europe/Berlin')
        mode = attrs.get('mode', 'today')

        # timezone-aware current time
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)

        # ========== FIX: Priorizar start_time explícito si se proporciona ==========
        user_start = attrs.get("start_time")
        
        if user_start:
            # Usuario dio un start_time explícito - RESPETARLO
            if user_start.tzinfo is None:
                user_start = tz.localize(user_start)
            else:
                user_start = user_start.astimezone(tz)
            
            # Validar que no esté en el pasado
            if user_start < now:
                # Si está en el pasado, usar "now" pero advertir
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"start_time in the past ({user_start}), using now ({now})")
                start_time = now
                attrs['when_selection'] = 'now'
            else:
                start_time = user_start
        else:
            # No hay start_time explícito - mapear desde when_selection
            start_time = self._map_when_to_time(when, mode, now, tz)

        attrs['start_time'] = start_time

        # If user provided end_time explicitly, respect it (but ensure tz-aware)
        user_end = attrs.get("end_time")
        if user_end:
            if user_end.tzinfo is None:
                user_end = tz.localize(user_end)
            else:
                user_end = user_end.astimezone(tz)
            attrs["end_time"] = user_end
        else:
            # default durations by mode (existing)
            if mode == 'today':
                attrs['end_time'] = start_time + timedelta(hours=4)
            elif mode == 'date':
                attrs['end_time'] = start_time + timedelta(hours=5)
            else:  # travel
                attrs['end_time'] = start_time + timedelta(hours=8)

        # Basic sanity: end after start
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("end_time must be after start_time")

        return attrs

    def _map_when_to_time(self, when, mode, now, tz):
        """
        Map user-friendly selection to heuristic start_time

        Rules:
        - Now: current time
        - Later today: 17:00 (5 PM)
        - Tonight: 19:30 (7:30 PM)
        - Tomorrow: 11:00 (11 AM)

        Adjustments by mode:
        - TODAY: prefer earlier times
        - DATE: prefer evening times
        - TRAVEL: more flexible
        """
        if when == 'now':
            return now

        elif when == 'later_today':
            if mode == 'today':
                target_hour = 16
            else:
                target_hour = 17
            target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            return target if target > now else now

        elif when == 'tonight':
            if mode == 'date':
                target_hour = 19
                target_minute = 30
            else:
                target_hour = 19
                target_minute = 0
            target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            return target if target > now else now

        elif when == 'tomorrow':
            if mode == 'today':
                target_hour = 10
            else:
                target_hour = 11
            tomorrow = now + timedelta(days=1)
            target = tomorrow.replace(hour=target_hour, minute=0, second=0, microsecond=0)

            # Edge case: near midnight
            if now.hour >= 23:
                return target
            return target

        return now


# Alias for compatibility
PlanCreateSerializer = PlanInputSerializer

class SwapStopInputSerializer(serializers.Serializer):
    stop_id = serializers.UUIDField()
    reason = serializers.ChoiceField(
        choices=['dont_like', 'too_expensive', 'weather', 'closed', 'other'],
        default='dont_like'
    )


SwapStopSerializer = SwapStopInputSerializer


class DelayInputSerializer(serializers.Serializer):
    stop_id = serializers.UUIDField()
    delta_min = serializers.IntegerField(min_value=1)


DelayReplanSerializer = DelayInputSerializer


class StopFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopFeedback
        fields = ['id', 'stop', 'user', 'rating', 'notes', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class SavedPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPlace
        fields = [
            'id',
            'place_id',
            'name',
            'lat',
            'lng',
            'category',
            'photo_reference',
            'rating',
            'price_level',
            'vicinity',
            'notes',
            'tags',
            'saved_at',
            'saved_from_plan',
            'visited',
            'visited_at',
        ]
        read_only_fields = ['id', 'saved_at']

    def validate(self, data):
        user = self.context['request'].user
        place_id = data.get('place_id')

        if not self.instance:
            if SavedPlace.objects.filter(user=user, place_id=place_id).exists():
                raise serializers.ValidationError("You've already saved this place")

        return data


class SavedPlaceCreateSerializer(serializers.Serializer):
    place_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    lat = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)
    lng = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)
    category = serializers.CharField(required=False, allow_blank=True)
    photo_reference = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.FloatField(required=False, allow_null=True)
    price_level = serializers.IntegerField(required=False, allow_null=True)
    vicinity = serializers.CharField(required=False, allow_blank=True)
    plan_id = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        user = self.context['request'].user
        plan_id = validated_data.pop('plan_id', None)

        from .models import Plan
        plan = None
        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id, user=user)
            except Plan.DoesNotExist:
                plan = None

        saved_place = SavedPlace.objects.create(
            user=user,
            saved_from_plan=plan,
            **validated_data
        )
        return saved_place


class SavedPlaceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPlace
        fields = [
            'id',
            'place_id',
            'name',
            'lat',
            'lng',
            'category',
            'photo_reference',
            'rating',
            'visited',
            'saved_at',
        ]
