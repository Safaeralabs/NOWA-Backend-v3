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


    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)

    # IMPORTANT: validate() uses timezone; it previously didn't exist.
    timezone = serializers.CharField(required=False, default='Europe/Berlin')

    timing_intent = serializers.ChoiceField(
        choices=['now', 'later', 'plan_ahead'],
        default='now'
    )

    # Budget (kept)
    budget = serializers.ChoiceField(
        choices=['cheap', 'normal', 'treat_myself'],
        default='normal'
    )



    # =====================================================
    # V3 INPUTS (NEW) - the ones the V3 engine actually uses
    # =====================================================

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
    # Optional "copy-only" inputs
    companions = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        """
        Derive start_time and end_time from timing_intent
        ALWAYS relative to plan timezone
        """
        plan_tz = pytz.timezone(attrs.get('timezone', 'Europe/Berlin'))
        
        # ✅ THE KEY: now_local is PLAN timezone, not device
        now_local = datetime.now(plan_tz)
        
        timing = attrs.get('timing_intent', 'now')
        
        # ========== TIMING RULES ==========
        
        if timing == 'now':
            # Now means: start in 5-10 minutes (plan timezone)
            start_time = now_local + timedelta(minutes=5)
        
        elif timing == 'later':
            hour = now_local.hour
            
            # Edge case: very late night (01:00-06:00) → fallback to plan_ahead
            if 1 <= hour < 6:
                # "Later" doesn't make sense at 2am, use tomorrow default
                start_time = (now_local + timedelta(days=1)).replace(hour=11, minute=0, second=0)
            else:
                # Normal case: +60-120 min
                start_time = now_local + timedelta(minutes=90)
        
        elif timing == 'plan_ahead':
            hint = attrs.get('plan_ahead_hint', '')
            
            if hint == 'tomorrow_morning':
                start_time = (now_local + timedelta(days=1)).replace(hour=10, minute=0, second=0)
            elif hint == 'tomorrow_afternoon':
                start_time = (now_local + timedelta(days=1)).replace(hour=16, minute=0, second=0)
            elif hint == 'this_weekend':
                # Next Saturday 11am
                days_ahead = (5 - now_local.weekday()) % 7 or 7
                start_time = (now_local + timedelta(days=days_ahead)).replace(hour=11, minute=0, second=0)
            else:
                # Default: tomorrow 11am
                start_time = (now_local + timedelta(days=1)).replace(hour=11, minute=0, second=0)
        
        # Duration based on intent + energy
        intent = attrs.get('intent', 'chill')
        energy = attrs.get('energy', 2)
        
        duration_hours = self._derive_duration(intent, energy)
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Save derived times
        attrs['start_time'] = start_time
        attrs['end_time'] = end_time
        
        # Build user_location for search
        attrs['user_location'] = {
            'lat': float(attrs['lat']),
            'lng': float(attrs['lng'])
        }
        
        return attrs

    def _derive_duration(self, intent, energy):
        """Smart duration based on intent + energy"""
        base_durations = {
            'chill': 2.0,
            'highlights': 4.0,
            'food_tour': 3.0,
            'nightlife': 5.0,
            'museum': 2.5,
        }
        
        base = base_durations.get(intent, 3.0)
        
        # Energy modifier
        if energy <= 1:
            return base * 0.7  # Low energy: shorter
        elif energy >= 3:
            return base * 1.3  # High energy: longer
        return base

    

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
