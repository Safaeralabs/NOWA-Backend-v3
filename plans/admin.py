from django.contrib import admin
from .models import Profile, Plan, Stop, Leg, StopFeedback, StopHistory


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'start_time_utc', 'clusters_visited', 'route_quality_score', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'route_quality_score', 'total_walking_distance_m', 'clusters_visited']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'user', 'status')
        }),
        ('Time', {
            'fields': ('start_time_utc', 'end_time_utc')
        }),
        ('Route Quality', {
            'fields': ('route_quality_score', 'total_walking_distance_m', 'clusters_visited', 'optimization_metadata')
        }),
        ('Data', {
            'fields': ('inputs_json', 'weather_snapshot_json'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan', 'order_index', 'cluster_id', 'category', 'priority', 'start_time_utc', 'rating']
    list_filter = ['priority', 'category', 'is_indoor', 'cluster_id']
    search_fields = ['name', 'place_id', 'cluster_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'plan', 'order_index', 'name', 'category')
        }),
        ('Location', {
            'fields': ('lat', 'lng', 'cluster_id', 'cluster_name')
        }),
        ('Timing', {
            'fields': ('start_time_utc', 'duration_min', 'closing_time', 'peak_hours')
        }),
        ('Quality', {
            'fields': ('priority', 'rating', 'price_level', 'queue_score', 'crowd_score', 'noise_level')
        }),
        ('Flags', {
            'fields': ('is_indoor', 'is_tourist_trap', 'local_favorite')
        }),
        ('AI', {
            'fields': ('reason_short', 'ai_reasoning', 'rank_in_cluster', 'tags'),
            'classes': ('collapse',)
        }),
        ('Provider', {
            'fields': ('place_provider', 'place_id', 'open_status_json'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Leg)
class LegAdmin(admin.ModelAdmin):
    list_display = ['plan', 'from_stop', 'to_stop', 'recommended_mode', 'recommended_distance_m', 'recommended_duration_sec']
    list_filter = ['recommended_mode']
    search_fields = ['from_stop__name', 'to_stop__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'plan', 'from_stop', 'to_stop')
        }),
        ('Recommended Route', {
            'fields': ('recommended_mode', 'recommended_duration_sec', 'recommended_distance_m', 'recommended_reason', 'ai_pick_reason')
        }),
        ('All Modes', {
            'fields': ('modes_json',),
            'classes': ('collapse',)
        }),
        ('Warnings', {
            'fields': ('travel_warning',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(StopFeedback)
class StopFeedbackAdmin(admin.ModelAdmin):
    list_display = ['stop', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['stop__name', 'user__username', 'notes']
    readonly_fields = ['id', 'created_at']


@admin.register(StopHistory)
class StopHistoryAdmin(admin.ModelAdmin):
    list_display = ['stop', 'previous_name', 'change_reason', 'was_user_initiated', 'created_at']
    list_filter = ['change_reason', 'was_user_initiated', 'created_at']
    search_fields = ['stop__name', 'previous_name', 'previous_place_id']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'stop', 'change_reason', 'was_user_initiated')
        }),
        ('Previous Data', {
            'fields': ('previous_place_id', 'previous_name', 'previous_lat', 'previous_lng', 'previous_data_json')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )