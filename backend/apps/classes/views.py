import csv
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, views
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import SessionAuthentication
from .models import Classroom, Enrollment, Assignment
from .serializers import (
    ClassroomSerializer, ClassroomDetailSerializer,
    EnrollmentSerializer, AssignmentSerializer
)
from apps.content.models import UserProgress
from apps.identity.views import set_auth_cookies
from apps.identity.permissions import (
    RequireClassAnalyticsPermission,
    RequireClassCreatePermission,
    RequireClassManagePermission,
)
from academiadub.throttles import LoginRateThrottle


class ClassroomViewSet(viewsets.ModelViewSet):
    """
    Instructor CRUD for classrooms.
    Students can only list/retrieve classes they are enrolled in.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_permission_scope(self, permission_key):
        classroom_id = self.kwargs.get("pk")
        return ("class", classroom_id) if classroom_id else (None, None)

    def user_has_permission(self, user, permission_key, scope_type, scope_id):
        if permission_key == "class:create":
            return user.is_superuser or user.has_permission(permission_key)
        if user.is_superuser:
            return True
        classroom = Classroom.objects.filter(pk=scope_id).first()
        if not classroom:
            return False
        if classroom.instructor_id == user.id:
            return permission_key in ("class:manage", "class:view_analytics")
        return user.has_permission(permission_key, scope_type, scope_id)

    def get_permissions(self):
        if self.action in ("create",):
            required = RequireClassCreatePermission
        elif self.action in ("analytics", "export_csv"):
            required = RequireClassAnalyticsPermission
        elif self.action in ("update", "partial_update", "destroy"):
            required = RequireClassManagePermission
        else:
            required = None
        checks = [permissions.IsAuthenticated()]
        if required:
            checks.append(required())
        return checks

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClassroomDetailSerializer
        return ClassroomSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.has_permission("class:manage"):
            return Classroom.objects.all()
        # Instructors see their own classes; students see classes they're in
        taught = Classroom.objects.filter(instructor=user)
        enrolled = Classroom.objects.filter(enrollments__student=user, enrollments__status="active")
        scoped_ids = list(user.roles.filter(
            scope_type="class",
            role__permissions__key__in=["class:manage", "class:view_analytics"],
        ).values_list("scope_id", flat=True))
        scoped = Classroom.objects.filter(pk__in=scoped_ids)
        return (taught | enrolled | scoped).distinct()

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        """Student joins via join code."""
        classroom = self.get_object()
        if classroom.instructor == request.user:
            return Response({"error": "Instructors cannot enroll in their own class."}, status=400)

        enrollment, created = Enrollment.objects.get_or_create(
            classroom=classroom, student=request.user,
            defaults={"status": "active"}
        )
        if not created and enrollment.status == "active":
            return Response({"detail": "Already enrolled."}, status=200)

        enrollment.status = "active"
        enrollment.save()
        return Response({"detail": "Joined successfully."}, status=201)

    @action(detail=True, methods=["get"], url_path="analytics")
    def analytics(self, request, pk=None):
        """Instructor view: completion rates per assignment."""
        classroom = self.get_object()
        if not self.user_has_permission(
            request.user, "class:view_analytics", "class", classroom.pk
        ):
            return Response({"error": "Not authorised."}, status=403)

        active_students = classroom.enrollments.filter(status="active").values_list("student_id", flat=True)
        total_students = len(active_students)

        data = []
        for assignment in classroom.assignments.select_related("topic"):
            completed = UserProgress.objects.filter(
                topic=assignment.topic,
                user_id__in=active_students,
                state="completed"
            ).count()
            data.append({
                "topic_id": str(assignment.topic.id),
                "topic_title": assignment.topic.title,
                "due_at": assignment.due_at,
                "total_students": total_students,
                "completed": completed,
                "completion_rate": round((completed / total_students * 100) if total_students else 0, 1),
            })

        return Response({
            "classroom": classroom.name,
            "total_students": total_students,
            "assignments": data
        })

    @action(detail=True, methods=["get"], url_path="export")
    def export_csv(self, request, pk=None):
        """Export student progress as CSV."""
        classroom = self.get_object()
        if not self.user_has_permission(
            request.user, "class:view_analytics", "class", classroom.pk
        ):
            return Response({"error": "Not authorised."}, status=403)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="class_{classroom.join_code}_report.csv"'

        writer = csv.writer(response)
        writer.writerow(["Student Email", "Topic", "Status", "Last Read"])

        enrollments = classroom.enrollments.filter(status="active").select_related("student")
        assignments = classroom.assignments.select_related("topic")

        for enrollment in enrollments:
            for assignment in assignments:
                progress = UserProgress.objects.filter(
                    user=enrollment.student, topic=assignment.topic
                ).first()
                writer.writerow([
                    enrollment.student.email,
                    assignment.topic.title,
                    progress.state if progress else "not_started",
                    progress.read_at.strftime("%Y-%m-%d %H:%M") if progress else "—",
                ])

        return response


class JoinByCodeView(views.APIView):
    """Join a class by entering the join code directly."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("join_code", "").strip().upper()
        try:
            classroom = Classroom.objects.get(join_code=code, is_active=True)
        except Classroom.DoesNotExist:
            return Response({"error": "Invalid or inactive class code."}, status=404)

        if classroom.instructor == request.user:
            return Response({"error": "You are the instructor of this class."}, status=400)

        enrollment, created = Enrollment.objects.get_or_create(
            classroom=classroom, student=request.user,
            defaults={"status": "active"}
        )
        if not created:
            enrollment.status = "active"
            enrollment.save()

        serializer = ClassroomSerializer(classroom, context={"request": request})
        return Response({"detail": "Joined!" if created else "Re-enrolled.", "classroom": serializer.data}, status=201)


class ClassCodeLoginView(views.APIView):
    """
    Passwordless login for students enrolled in a class.
    POST { class_code, student_secret } → { access, refresh, classroom_name }
    The student must be actively enrolled and their PIN must match.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        class_code = request.data.get("class_code", "").strip().upper()
        student_secret = request.data.get("student_secret", "").strip()

        if not class_code or not student_secret:
            return Response(
                {"error": "Both class_code and student_secret are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            classroom = Classroom.objects.get(join_code=class_code, is_active=True)
        except Classroom.DoesNotExist:
            return Response(
                {"error": "Invalid or inactive class code."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            enrollment = Enrollment.objects.get(
                classroom=classroom,
                student_secret=student_secret,
                status="active",
            )
        except Enrollment.DoesNotExist:
            return Response(
                {"error": "Invalid secret code. Please contact your instructor."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = enrollment.student
        refresh = RefreshToken.for_user(user)
        # Embed the same custom claims as CustomTokenObtainPairSerializer
        refresh["email"] = user.email
        refresh["status"] = user.status
        refresh["roles"] = list(user.roles.values_list("role__key", flat=True))

        response = Response({
            "detail": "Logged in successfully.",
            "classroom_name": classroom.name,
            "student_email": user.email,
        }, status=status.HTTP_200_OK)
        return set_auth_cookies(
            response,
            str(refresh.access_token),
            str(refresh),
        )


class AssignmentViewSet(viewsets.ModelViewSet):
    """Instructor manages topic assignments for a classroom."""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permission_scope(self, permission_key):
        return "class", self.kwargs.get("classroom_pk")

    def user_has_permission(self, user, permission_key, scope_type, scope_id):
        if user.is_superuser:
            return True
        classroom = Classroom.objects.filter(pk=scope_id).first()
        if not classroom:
            return False
        return classroom.instructor_id == user.id or user.has_permission(
            permission_key, scope_type, scope_id
        )

    def get_permissions(self):
        checks = [permissions.IsAuthenticated()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            checks.append(RequireClassManagePermission())
        return checks

    def get_queryset(self):
        classroom_id = self.kwargs.get("classroom_pk")
        if self.request.user.is_superuser:
            return Assignment.objects.filter(classroom_id=classroom_id)
        scoped_ids = list(
            self.request.user.roles.filter(
                scope_type="class",
                role__permissions__key="class:manage",
            ).values_list("scope_id", flat=True)
        )
        return Assignment.objects.filter(classroom_id=classroom_id).filter(
            Q(classroom__instructor=self.request.user)
            | Q(classroom_id__in=scoped_ids)
        )

    def perform_create(self, serializer):
        classroom_id = self.kwargs.get("classroom_pk")
        classroom = Classroom.objects.get(pk=classroom_id)
        if classroom.instructor != self.request.user and not self.request.user.is_superuser:
            if not self.request.user.has_permission("class:manage", "class", classroom.pk):
                raise PermissionDenied("Only an instructor with class management access can add assignments.")
        serializer.save(classroom=classroom)
