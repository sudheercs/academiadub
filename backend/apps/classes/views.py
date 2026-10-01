import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Classroom, Enrollment, Assignment
from .serializers import (
    ClassroomSerializer, ClassroomDetailSerializer,
    EnrollmentSerializer, AssignmentSerializer
)
from apps.content.models import UserProgress


class ClassroomViewSet(viewsets.ModelViewSet):
    """
    Instructor CRUD for classrooms.
    Students can only list/retrieve classes they are enrolled in.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClassroomDetailSerializer
        return ClassroomSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Classroom.objects.all()
        # Instructors see their own classes; students see classes they're in
        taught = Classroom.objects.filter(instructor=user)
        enrolled = Classroom.objects.filter(enrollments__student=user, enrollments__status="active")
        return (taught | enrolled).distinct()

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
        if classroom.instructor != request.user and not request.user.is_staff:
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
        if classroom.instructor != request.user and not request.user.is_staff:
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


class AssignmentViewSet(viewsets.ModelViewSet):
    """Instructor manages topic assignments for a classroom."""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        classroom_id = self.kwargs.get("classroom_pk")
        return Assignment.objects.filter(classroom_id=classroom_id)

    def perform_create(self, serializer):
        classroom_id = self.kwargs.get("classroom_pk")
        classroom = Classroom.objects.get(pk=classroom_id)
        if classroom.instructor != self.request.user and not self.request.user.is_staff:
            raise PermissionError("Only the instructor can add assignments.")
        serializer.save(classroom=classroom)
