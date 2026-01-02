import uuid
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferences_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Plan(models.Model):
    MODE_CHOICES = [
        ('today', 'Today'),        # READY NUEVO
        ('travel', 'Travel'),      # READY Actualizado
        ('date', 'Date'),          # READY Actualizado
        # Eliminados: friends, solo, occasion
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('building', 'Building'),
        ('ready', 'Ready'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('swapping', 'Swapping'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='building')
    
    inputs_json = models.JSONField(default=dict)
    
    start_time_utc = models.DateTimeField()
    end_time_utc = models.DateTimeField()
    
    weather_snapshot_json = models.JSONField(default=dict, blank=True)
    
    route_quality_score = models.FloatField(default=0)
    total_walking_distance_m = models.IntegerField(default=0)
    clusters_visited = models.IntegerField(default=0)
    optimization_metadata = models.JSONField(default=dict, blank=True)
    swap_count = models.IntegerField(default=0)
    confidence_locked = models.BooleanField(default=False)
    confidence_locked_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

        # ========== NEW FIELDS (THEME ENGINE V2) ==========
    theme = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Optional theme for plan generation (e.g., 'chill_scenic', 'food_tour')"
    )
    budget_feeling = models.CharField(
        max_length=20,
        choices=[
            ('cheap', 'Cheap'),
            ('normal', 'Normal'),
            ('treat_myself', 'Treat Myself')
        ],
        null=True,
        blank=True,
        help_text="Budget preference from user"
    )
    last_error_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Error code if plan generation failed"
    )
    last_error_context = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional context about error"
    )
    GENERATION_METHOD_CHOICES = (
        ('llm', 'LLM (OpenAI)'),
        ('fallback', 'Greedy Fallback'),
        ('today_deterministic', 'TODAY Deterministic'),
    )
    
    generation_method = models.CharField(
        max_length=30,
        choices=GENERATION_METHOD_CHOICES,
        default='llm',
        help_text="Method used to generate this plan"
    )
    
    diversity_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Diversity score (0-1, higher is more diverse)"
    )
    
    llm_attempts = models.IntegerField(
        default=0,
        help_text="Number of LLM attempts (for debugging)"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Plan {self.id} - {self.status}"



class Stop(models.Model):
    PRIORITY_CHOICES = [
        ('must', 'Must See'),
        ('nice', 'Nice to Have'),
        ('optional', 'Optional'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='stops')
    
    order_index = models.IntegerField()
    
    place_provider = models.CharField(max_length=50, default='google')
    place_id = models.CharField(max_length=255)
    
    name = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    

    photo_reference = models.CharField(max_length=500, blank=True, null=True)  # READY NUEVO

    category = models.CharField(max_length=100)
    tags = models.JSONField(default=list, blank=True)
    
    cluster_id = models.IntegerField(null=True, blank=True)
    cluster_name = models.CharField(max_length=200, blank=True)
    
    start_time_utc = models.DateTimeField()
    duration_min = models.IntegerField()
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='nice')
    reason_short = models.TextField(blank=True)
    
    is_indoor = models.BooleanField(null=True, blank=True)
    price_level = models.IntegerField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    
    queue_score = models.IntegerField(default=1)
    crowd_score = models.IntegerField(default=1)
    noise_level = models.IntegerField(default=1)
    
    is_tourist_trap = models.BooleanField(default=False)
    local_favorite = models.BooleanField(default=False)
    
    closing_time = models.DateTimeField(null=True, blank=True)
    peak_hours = models.JSONField(default=list, blank=True)
    
    ai_reasoning = models.TextField(blank=True)
    rank_in_cluster = models.IntegerField(default=0)
    
    open_status_json = models.JSONField(default=dict, blank=True)
    previous_stop_data = models.JSONField(null=True, blank=True)
    swapped_at = models.DateTimeField(null=True, blank=True)
    swap_reason = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    # ========== NEW FIELDS (THEME ENGINE V2) ==========
    planned_daypart = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Morning (6am-11am)'),
            ('midday', 'Midday (11am-3:30pm)'),
            ('afternoon', 'Afternoon (3:30pm-6:30pm)'),
            ('evening', 'Evening (6:30pm-10:30pm)'),
            ('late', 'Late Night (10:30pm-2am)')
        ],
        null=True,
        blank=True,
        help_text="Time of day this stop is planned for"
    )

    business_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Business status from Google Places"
    )
    opening_hours_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Opening hours data from Google Places"
    )
    open_status_at_planned_time = models.BooleanField(
        null=True,
        blank=True,
        help_text="True if open at planned time, False if closed, None if unknown"
    )
    OPEN_CONFIDENCE_CHOICES = (  # ← Tupla ()
    ('high', 'High'),
    ('medium', 'Medium'),
    ('low', 'Low'),
)

    open_confidence = models.CharField(
        choices=OPEN_CONFIDENCE_CHOICES,  # ← Usa la constante
        blank=True,
        default='',
        max_length = 500
    )
    open_status_reason = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Reason for open_status (e.g., 'periods_check', 'missing_hours')"
    )
    place_types = models.JSONField(
        null=True,
        blank=True,
        help_text="Google Places types array"
    )
    popularity = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of user ratings (user_ratings_total)"
    )


    why_now = models.CharField(
    max_length=50,
    blank=True,
    null=True,
    help_text="Short reason why this stop works right now (max 5 words)"
)

    score_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Breakdown of scoring factors"
)
    when_selection = models.CharField(
        max_length=20,
        choices=[
            ('now', 'Now'),
            ('later_today', 'Later today'),
            ('tonight', 'Tonight'),
            ('tomorrow', 'Tomorrow'),
        ],
        default='now',
        help_text="User's timing preference (UI only, maps to start_time)"
    )
    slot_role = models.CharField(
        max_length=20,
        choices=[
            ('anchor', 'Anchor - Confidence builder'),
            ('reward', 'Reward - Main attraction'),
            ('optional', 'Optional - Nice to have'),
        ],
        null=True,
        blank=True,
        help_text="Slot role in plan structure"
    )
    
    closed_warning = models.BooleanField(
        default=False,
        help_text="True if place may be closed"
    )
    
    closed_reason = models.CharField(
    max_length=200,
    blank=True,
    default='', 
    help_text="Reason why place is closed"
)
    
    hours_unknown = models.BooleanField(
        default=False,
        help_text="True if hours unknown"
    )
    

    class Meta:
        ordering = ['plan', 'order_index']
        unique_together = ['plan', 'order_index']

    def __str__(self):
        return f"Stop {self.order_index}: {self.name}"




class Leg(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='legs')
    
    from_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='legs_from')
    to_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='legs_to')
    
    modes_json = models.JSONField(default=dict)
    
    recommended_mode = models.CharField(max_length=50)
    recommended_duration_sec = models.IntegerField(default=0)
    recommended_distance_m = models.IntegerField(default=0)
    recommended_reason = models.TextField(blank=True)
    
    ai_pick_reason = models.TextField(blank=True)
    travel_warning = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['plan', 'from_stop__order_index']


class StopFeedback(models.Model):
    RATING_CHOICES = [
        ('love', 'Love'),
        ('ok', 'OK'),
        ('no', 'Not for me'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    rating = models.CharField(max_length=10, choices=RATING_CHOICES)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)


class StopHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='history')
    
    previous_place_id = models.CharField(max_length=255)
    previous_name = models.CharField(max_length=255)
    previous_lat = models.DecimalField(max_digits=9, decimal_places=6)
    previous_lng = models.DecimalField(max_digits=9, decimal_places=6)
    
    previous_data_json = models.JSONField(default=dict)
    
    change_reason = models.CharField(max_length=100)
    was_user_initiated = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)




class SavedPlace(models.Model):
    """
    User's saved/favorite places
    
    These are places from plans that users want to remember.
    They appear in:
    - Saved places list
    - Map view (as different markers)
    """
    
    # User who saved this place
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_places'
    )
    
    # ========================================
    # PLACE DATA (from Google Places)
    # ========================================
    
    place_id = models.CharField(
        max_length=255,
        help_text="Google Place ID"
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Place name"
    )
    
    lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Latitude"
    )
    
    lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Longitude"
    )
    
    # ========================================
    # OPTIONAL METADATA
    # ========================================
    
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Category (cafe, restaurant, etc.)"
    )
    
    photo_reference = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Google photo reference"
    )
    
    rating = models.FloatField(
        null=True,
        blank=True,
        help_text="Google rating"
    )
    
    price_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Price level (1-4)"
    )
    
    vicinity = models.CharField(
        max_length=500,
        blank=True,
        help_text="Address/vicinity"
    )
    
    # ========================================
    # USER METADATA
    # ========================================
    
    notes = models.TextField(
        blank=True,
        help_text="User's personal notes about this place"
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="User's custom tags"
    )
    
    # ========================================
    # TRACKING
    # ========================================
    
    saved_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When user saved this place"
    )
    
    saved_from_plan = models.ForeignKey(
        'Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saved_places_from_here',
        help_text="Plan where user discovered this place"
    )
    
    visited = models.BooleanField(
        default=False,
        help_text="Has user visited this place?"
    )
    
    visited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user visited"
    )
    
    class Meta:
        ordering = ['-saved_at']
        unique_together = ['user', 'place_id']
        indexes = [
            models.Index(fields=['user', '-saved_at']),
            models.Index(fields=['user', 'place_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    @property
    def coordinates(self):
        """Return as tuple for easy use"""
        return (float(self.lat), float(self.lng))