from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from plans.views import (
    feature_flags, 
    PlanViewSet, 
    StopFeedbackViewSet, 
    ProfileViewSet, 
    SavedPlaceViewSet,  
    register
)

router = routers.DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'feedback', StopFeedbackViewSet, basename='feedback')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'saved-places', SavedPlaceViewSet, basename='saved-places')  

def health_check(request):
    return JsonResponse({'status': 'ok', 'version': '1.0'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', register, name='register'),
    path('api/feature-flags/', feature_flags, name='feature-flags'),

    path('api/', include(router.urls)),   
]


# ============================================
# ENDPOINTS CREADOS (saved-places):
# ============================================

"""
GET    /api/saved-places/
       Lista todos los sitios guardados del usuario

POST   /api/saved-places/
       Guardar un nuevo sitio
       Body: {
           "place_id": "ChIJ...",
           "name": "Cafe Name",
           "lat": 52.520008,
           "lng": 13.404954,
           "category": "cafe",  // opcional
           "photo_reference": "...",  // opcional
           "rating": 4.5,  // opcional
           "price_level": 2,  // opcional
           "vicinity": "Address",  // opcional
           "plan_id": "uuid",  // opcional
           "notes": "Personal notes"  // opcional
       }

GET    /api/saved-places/{id}/
       Obtener un sitio guardado específico

PUT    /api/saved-places/{id}/
       Actualizar un sitio guardado (ej. añadir notas)

DELETE /api/saved-places/{id}/
       Eliminar de guardados

POST   /api/saved-places/check/
       Verificar si un sitio está guardado
       Body: {"place_id": "ChIJ..."}
       Returns: {"is_saved": true/false, "saved_place_id": 123}

POST   /api/saved-places/toggle/
       Toggle saved status (más fácil de usar)
       Body: {
           "place_id": "ChIJ...",
           "name": "Place Name",  // requerido si no está guardado
           "lat": 52.520008,  // requerido si no está guardado
           "lng": 13.404954,  // requerido si no está guardado
           ...otros campos opcionales
       }
       Returns: {"is_saved": true/false, "saved_place": {...}}

POST   /api/saved-places/{id}/mark_visited/
       Marcar sitio como visitado

GET    /api/saved-places/for_map/
       Obtener sitios guardados optimizados para mostrar en mapa
       Returns: [{id, place_id, name, lat, lng, category, rating, visited}, ...]
"""