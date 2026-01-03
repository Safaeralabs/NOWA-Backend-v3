"""
NOWA V3 URL Configuration

Endpoints:
- /api/auth/register/
- /api/auth/token/ (JWT)
- /api/auth/token/refresh/
- /api/feature-flags/
- /api/plans/ (CRUD)
- /api/plans/generate/
- /api/plans/{id}/presentation/  ← NEW V3
- /api/plans/{id}/start/
- /api/plans/{id}/swap-stop/
- /api/plans/{id}/delay/
- /api/plans/{id}/pause/
- /api/plans/{id}/resume/
- /api/plans/{id}/complete/
- /api/plans/{id}/archive/
- /api/plans/{id}/undo_swap/
- /api/plans/{id}/remove_stop/
- /api/plans/{id}/adjust_duration/
- /api/plans/{id}/lock_confidence/
- /api/plans/{id}/unlock_confidence/
- /api/saved-places/
- /api/saved-places/check/
- /api/saved-places/toggle/
- /api/saved-places/{id}/mark_visited/
- /api/saved-places/for_map/
- /api/profiles/
- /api/stop-feedback/
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from plans import views

# ========== Router for ViewSets ==========
router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plan')
router.register(r'profiles', views.ProfileViewSet, basename='profile')
router.register(r'saved-places', views.SavedPlaceViewSet, basename='savedplace')
router.register(r'stop-feedback', views.StopFeedbackViewSet, basename='stopfeedback')

# ========== URL Patterns ==========
urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # ===== AUTH =====
    path('api/auth/register/', views.register, name='register'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # ===== FEATURE FLAGS =====
    path('api/feature-flags/', views.feature_flags, name='feature_flags'),
    
    # ===== API ROUTER (Plans, Profiles, SavedPlaces, StopFeedback) =====
    path('api/', include(router.urls)),
    
    # ===== API BROWSABLE AUTH (for development) =====
    path('api-auth/', include('rest_framework.urls')),
]

# ========== Custom Plan Actions (explicit documentation) ==========
# These are handled by DRF's @action decorator in PlanViewSet:
#
# POST   /api/plans/generate/                    → Create new plan
# GET    /api/plans/{id}/                        → Get plan details
# GET    /api/plans/{id}/presentation/           → UI-friendly format (V3)
# POST   /api/plans/{id}/start/                  → Activate plan
# POST   /api/plans/{id}/swap-stop/              → Replace a stop
# POST   /api/plans/{id}/delay/                  → Delay start time
# POST   /api/plans/{id}/pause/                  → Pause active plan
# POST   /api/plans/{id}/resume/                 → Resume paused plan
# POST   /api/plans/{id}/complete/               → Mark complete
# POST   /api/plans/{id}/archive/                → Archive plan
# POST   /api/plans/{id}/undo_swap/              → Undo last swap
# POST   /api/plans/{id}/remove_stop/            → Remove stop
# POST   /api/plans/{id}/adjust_duration/        → Change stop duration
# POST   /api/plans/{id}/lock_confidence/        → Lock plan (no suggestions)
# POST   /api/plans/{id}/unlock_confidence/      → Unlock plan

# ========== Custom SavedPlace Actions ==========
# POST   /api/saved-places/check/                → Check if place is saved
# POST   /api/saved-places/toggle/               → Toggle saved status
# POST   /api/saved-places/{id}/mark_visited/    → Mark as visited
# GET    /api/saved-places/for_map/              → Optimized for map

# ========== Development Notes ==========
# For production:
# 1. Set DEBUG=False
# 2. Configure ALLOWED_HOSTS
# 3. Use HTTPS for JWT tokens
# 4. Enable CORS for frontend domain only
# 5. Rate limit auth endpoints
# 6. Add API versioning if needed (e.g., /api/v3/)