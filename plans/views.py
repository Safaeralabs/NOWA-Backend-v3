from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_timezone

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Plan, Stop, StopFeedback, Profile, SavedPlace
from .serializers import (
    PlanListSerializer,
    PlanDetailSerializer,
    PlanCreateSerializer,
    SwapStopInputSerializer,
    DelayInputSerializer,
    StopFeedbackSerializer,
    ProfileSerializer,
    SavedPlaceSerializer,
    SavedPlaceCreateSerializer,
    SavedPlaceListSerializer,
)

# Celery tasks (V3 pipeline)
from .tasks import generate_plan_task, swap_stop_task, delay_replan_task



class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlanViewSet(viewsets.ModelViewSet):
    """
    Endpoints (según tu urls.py):
      - GET    /api/plans/
      - POST   /api/plans/generate/
      - GET    /api/plans/{id}/
      - POST   /api/plans/{id}/swap-stop/
      - POST   /api/plans/{id}/delay/
      - POST   /api/plans/{id}/start/
      - POST   /api/plans/{id}/pause/
      - POST   /api/plans/{id}/resume/
      - POST   /api/plans/{id}/complete/
      - POST   /api/plans/{id}/archive/
      - POST   /api/plans/{id}/undo_swap/
      - POST   /api/plans/{id}/remove_stop/
      - POST   /api/plans/{id}/adjust_duration/
      - POST   /api/plans/{id}/lock_confidence/
      - POST   /api/plans/{id}/unlock_confidence/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Plan.objects.filter(user=self.request.user)
            .prefetch_related("stops", "legs", "legs__from_stop", "legs__to_stop")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PlanListSerializer
        return PlanDetailSerializer

    def retrieve(self, request, pk=None):
        plan = self.get_object()
        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """
        Generate a new plan (V3 wired)

        Required:
          - city_name
          - lat, lng  (V3 needs real coords for Places)

        Optional (V3):
          - engine_version: v3
          - intent: "chill" | "shopping" | "museum" ...
          - discovery_mode: local|tourist
          - constraints: ["indoor_only", "no_alcohol", ...]
          - use_llm: true/false
          - llm_model
          - timezone
          - companions
          - weather (manual override for QA)
        """

        serializer = PlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # --- HARD REQUIREMENT for V3: location must be present ---
        lat = data.get("lat")
        lng = data.get("lng")
        if lat is None or lng is None:
            return Response(
                {
                    "error": "lat/lng required",
                    "hint": "V3 needs current_location coordinates to query Google Places.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_dt = data.get("start_time")
        end_dt = data.get("end_time")

        # --- Build V3-first inputs_json (and keep V2 fields for compatibility) ---
        constraints = list(data.get("constraints") or [])

        # Back-compat: if user used 'avoid', merge into constraints
        avoid = list(data.get("avoid") or [])
        for a in avoid:
            if a and a not in constraints:
                constraints.append(a)

        # Back-compat: indoor/outdoor toggles become constraints if strict
        indoor_ok = bool(data.get("indoor_ok", True))
        outdoor_ok = bool(data.get("outdoor_ok", True))
        if indoor_ok and not outdoor_ok:
            if "indoor_only" not in constraints:
                constraints.append("indoor_only")
        if outdoor_ok and not indoor_ok:
            if "outdoor_only" not in constraints:
                constraints.append("outdoor_only")

        duration_hours = 4.0
        if start_dt and end_dt:
            try:
                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
            except Exception:
                duration_hours = 4.0

        inputs_json = {
            # ========== V3 CORE ==========
            "engine_version": data.get("engine_version", "v3"),
            "city_name": data.get("city_name"),
            "timezone": data.get("timezone", "Europe/Berlin"),
            "when_selection": data.get("when_selection", "now"),
            "intent": data.get("intent", "chill"),
            "discovery_mode": data.get("discovery_mode", "local"),
            "constraints": constraints,
            "use_llm": bool(data.get("use_llm", False)),
            "llm_model": data.get("llm_model", "gpt-4o-mini"),
            "companions": data.get("companions"),
            "current_location": {"lat": float(lat), "lng": float(lng)},
            "start_time": start_dt.isoformat() if start_dt else None,
            "end_time": end_dt.isoformat() if end_dt else None,
            "duration_hours": duration_hours,
            # optional manual override for QA
            "weather": data.get("weather"),

            # ========== V2 BACK-COMPAT (keep your existing knobs) ==========
            "mode": data.get("mode", "travel"),
            "mood": data.get("mood", "curious"),
            "energy": data.get("energy", 2),
            "social": data.get("social", 2),
            "friction_tolerance": data.get("friction_tolerance", 2),
            "budget": data.get("budget", "normal"),
            "avoid": avoid,
            "indoor_ok": indoor_ok,
            "outdoor_ok": outdoor_ok,

            # Theme Engine V2 (optional)
            "theme": data.get("theme"),
            "budget_feeling": data.get("budget_feeling"),
        }

        # Create Plan model row
        plan = Plan.objects.create(
            user=request.user,
            status="building",
            start_time_utc=start_dt,
            end_time_utc=end_dt,
            inputs_json=inputs_json,
            # Keep these model fields in sync if you want
            theme=data.get("theme"),
            budget_feeling=data.get("budget_feeling") or data.get("budget"),
        )

        # Trigger async build
        generate_plan_task.delay(str(plan.id))

        return Response(
            {
                "plan_id": str(plan.id),
                "status": "building",
                "engine_version": inputs_json["engine_version"],
                "when": inputs_json["when_selection"],
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        plan = self.get_object()

        if plan.status != "ready":
            return Response(
                {"error": "Plan must be ready to start"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.status = "active"
        plan.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="swap-stop")
    def swap_stop(self, request, pk=None):
        plan = self.get_object()
        serializer = SwapStopInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stop_id = serializer.validated_data["stop_id"]
        reason = serializer.validated_data["reason"]

        _stop = get_object_or_404(Stop, id=stop_id, plan=plan)

        plan.status = "swapping"
        plan.save()

        swap_stop_task.delay(str(plan.id), str(stop_id), reason)

        return Response(
            {
                "plan_id": str(plan.id),
                "status": "swapping",
                "message": "Swapping stop. Poll /plans/{id} for updates.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def delay(self, request, pk=None):
        plan = self.get_object()
        serializer = DelayInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stop_id = serializer.validated_data["stop_id"]
        delta_min = serializer.validated_data["delta_min"]

        _stop = get_object_or_404(Stop, id=stop_id, plan=plan)

        plan.status = "building"
        plan.save()

        delay_replan_task.delay(str(plan.id), str(stop_id), int(delta_min))

        return Response(
            {
                "plan_id": str(plan.id),
                "status": "building",
                "message": "Replanning schedule. Poll /plans/{id} for updates.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """
        NOTE: Model Plan.STATUS_CHOICES does NOT include 'paused'.
        We keep status valid and store paused flag in optimization_metadata.
        """
        plan = self.get_object()

        if plan.status != "active":
            return Response(
                {"error": "Can only pause active plans"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meta = plan.optimization_metadata or {}
        meta["paused"] = True
        meta["paused_at"] = dj_timezone.now().isoformat()
        plan.optimization_metadata = meta
        plan.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        plan = self.get_object()

        meta = plan.optimization_metadata or {}
        meta["paused"] = False
        meta["resumed_at"] = dj_timezone.now().isoformat()
        plan.optimization_metadata = meta
        plan.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        plan = self.get_object()
        plan.status = "completed"
        plan.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """
        NOTE: Model Plan.STATUS_CHOICES does NOT include 'archived'.
        We keep status valid and store archived flag in optimization_metadata.
        """
        plan = self.get_object()

        meta = plan.optimization_metadata or {}
        meta["archived"] = True
        meta["archived_at"] = dj_timezone.now().isoformat()
        plan.optimization_metadata = meta

        # keep a valid status
        if plan.status not in ["completed", "failed"]:
            plan.status = "completed"

        plan.save()

        return Response({"status": "archived", "plan_id": str(plan.id)})

    @action(detail=True, methods=["post"])
    def remove_stop(self, request, pk=None):
        plan = self.get_object()
        stop_id = request.data.get("stop_id")

        stop = get_object_or_404(Stop, id=stop_id, plan=plan)
        stop.delete()

        # Reorder remaining stops
        remaining = plan.stops.all().order_by("order_index")
        for i, s in enumerate(remaining):
            s.order_index = i
            s.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def adjust_duration(self, request, pk=None):
        plan = self.get_object()
        stop_id = request.data.get("stop_id")
        new_duration = request.data.get("duration_min")

        stop = get_object_or_404(Stop, id=stop_id, plan=plan)
        stop.duration_min = int(new_duration)
        stop.save()

        serializer = PlanDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def lock_confidence(self, request, pk=None):
        plan = self.get_object()

        if plan.status not in ["active", "ready"]:
            return Response(
                {"error": "Plan must be active or ready to lock"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.confidence_locked = True
        plan.confidence_locked_at = dj_timezone.now()
        plan.save()

        return Response(
            {"message": "Plan locked - no more suggestions", "confidence_locked": True}
        )

    @action(detail=True, methods=["post"])
    def unlock_confidence(self, request, pk=None):
        plan = self.get_object()

        plan.confidence_locked = False
        plan.confidence_locked_at = None
        plan.save()

        return Response({"message": "Plan unlocked", "confidence_locked": False})

    @action(detail=True, methods=["post"])
    def undo_swap(self, request, pk=None):
        """
        Undo swap (kept as-is, triggers task).
        """
        plan = self.get_object()
        stop_id = request.data.get("stop_id")

        if not stop_id:
            return Response(
                {"error": "stop_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stop = Stop.objects.get(id=stop_id, plan=plan)
        except Stop.DoesNotExist:
            return Response({"error": "Stop not found"}, status=status.HTTP_404_NOT_FOUND)

        if not stop.previous_stop_data:
            return Response(
                {"error": "No previous state to restore"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.status = "swapping"
        plan.save()

        from .tasks import undo_swap_task
        undo_swap_task.delay(str(plan.id), str(stop_id))

        return Response({"message": "Undoing swap.", "status": "swapping"})


class StopFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = StopFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StopFeedback.objects.filter(stop__plan__user=self.request.user)

    def perform_create(self, serializer):
        stop_id = self.request.data.get("stop")
        _stop = get_object_or_404(Stop, id=stop_id, plan__user=self.request.user)
        serializer.save(user=self.request.user)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")

    if not username or not email or not password:
        return Response(
            {"error": "Username, email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already exists"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "message": "User created successfully",
            "user": {"id": user.id, "username": user.username, "email": user.email},
            "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def feature_flags(request):
    mode = request.GET.get("mode", "today")
    return Response(
        {
            "theme_engine_v2": is_theme_engine_v2_enabled(),
            "available_themes": get_available_themes(mode)
            if is_theme_engine_v2_enabled()
            else [],
            "features": {
                "themes": is_theme_engine_v2_enabled(),
                "budget_matching": is_theme_engine_v2_enabled(),
                "opening_hours": is_theme_engine_v2_enabled(),
                "daypart_awareness": is_theme_engine_v2_enabled(),
            },
        }
    )


class SavedPlaceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedPlace.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return SavedPlaceListSerializer
        elif self.action == "create":
            return SavedPlaceCreateSerializer
        return SavedPlaceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            saved_place = serializer.save()
            output_serializer = SavedPlaceSerializer(saved_place)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Place removed from saved"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def check(self, request):
        place_id = request.data.get("place_id")
        if not place_id:
            return Response(
                {"error": "place_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            saved_place = SavedPlace.objects.get(user=request.user, place_id=place_id)
            return Response({"is_saved": True, "saved_place_id": saved_place.id})
        except SavedPlace.DoesNotExist:
            return Response({"is_saved": False, "saved_place_id": None})

    @action(detail=False, methods=["post"])
    def toggle(self, request):
        place_id = request.data.get("place_id")
        if not place_id:
            return Response(
                {"error": "place_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            saved_place = SavedPlace.objects.get(user=request.user, place_id=place_id)
            saved_place.delete()
            return Response(
                {"is_saved": False, "saved_place": None, "message": "Place removed from saved"}
            )
        except SavedPlace.DoesNotExist:
            serializer = SavedPlaceCreateSerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                saved_place = serializer.save()
                output_serializer = SavedPlaceSerializer(saved_place)
                return Response(
                    {
                        "is_saved": True,
                        "saved_place": output_serializer.data,
                        "message": "Place saved",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def mark_visited(self, request, pk=None):
        saved_place = self.get_object()
        saved_place.visited = True
        saved_place.visited_at = dj_timezone.now()
        saved_place.save()
        serializer = SavedPlaceSerializer(saved_place)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def for_map(self, request):
        saved_places = self.get_queryset()
        serializer = SavedPlaceListSerializer(saved_places, many=True)
        return Response(serializer.data)
