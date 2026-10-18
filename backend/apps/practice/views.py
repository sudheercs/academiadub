from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Attempt, Quiz
from .serializers import (
    AttemptResultSerializer,
    AttemptSaveSerializer,
    AttemptSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
)


def _grade(quiz: Quiz, answers: dict) -> tuple[float, bool]:
    """Grade a set of answers against the quiz. Returns (score_percent, passed)."""
    questions = quiz.questions.prefetch_related("choices").all()
    total = questions.count()
    if total == 0:
        return 0.0, False

    correct_count = 0
    for question in questions:
        submitted_ids = set(str(cid) for cid in answers.get(str(question.id), []))
        correct_ids = set(str(c.id) for c in question.choices.filter(is_correct=True))
        if submitted_ids == correct_ids:
            correct_count += 1

    score_percent = round((correct_count / total) * 100, 1)
    passed = score_percent >= quiz.pass_mark
    return score_percent, passed


class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public-facing quiz endpoints.

    ┌──────────────────────────────────────────────────────────────────┐
    │  Quiz lifecycle                                                   │
    │  1. GET  /quizzes/<id>/             — view quiz details           │
    │  2. POST /quizzes/<id>/start/       — create in_progress attempt  │
    │  3. POST /quizzes/<id>/save/        — save partial answers        │
    │  4. POST /quizzes/<id>/submit/      — grade & finalise            │
    │  5. GET  /quizzes/<id>/my-attempts/ — list past attempts          │
    └──────────────────────────────────────────────────────────────────┘
    """
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Quiz.objects.filter(is_active=True).prefetch_related("questions__choices")
        topic_id = self.request.query_params.get("topic")
        if topic_id:
            qs = qs.filter(topic_id=topic_id)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuizDetailSerializer
        return QuizListSerializer

    # ── 1. start ─────────────────────────────────────────────────────────
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def start(self, request, pk=None):
        """
        Begin (or resume) a quiz attempt.

        - If the user already has an `in_progress` attempt for this quiz,
          that attempt is returned so they can resume exactly where they left off.
        - Otherwise a fresh attempt is created, recording `started_at = now()`.

        Response: AttemptSerializer (lightweight — no correct-answer data)
        """
        quiz = self.get_object()

        # Resume existing in_progress attempt if one exists
        existing = (
            Attempt.objects
            .filter(quiz=quiz, user=request.user, status="in_progress")
            .order_by("-started_at")
            .first()
        )
        if existing:
            return Response(
                {"attempt": AttemptSerializer(existing).data, "resumed": True},
                status=status.HTTP_200_OK,
            )

        # Create a brand-new attempt — started_at is auto-set to NOW by auto_now_add
        attempt = Attempt.objects.create(
            quiz=quiz,
            user=request.user,
            status="in_progress",
            answers={},
        )
        return Response(
            {"attempt": AttemptSerializer(attempt).data, "resumed": False},
            status=status.HTTP_201_CREATED,
        )

    # ── 2. save ──────────────────────────────────────────────────────────
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated],
        url_path="save/(?P<attempt_id>[0-9a-f-]+)"
    )
    def save(self, request, pk=None, attempt_id=None):
        """
        Persist the student's current answers without grading.

        - Only works on `in_progress` attempts owned by the requesting user.
        - Partial answers (not all questions answered) are perfectly fine.
        - Idempotent — safe to call repeatedly (e.g. autosave every 30 s).

        Payload: { "answers": { "<question_id>": ["<choice_id>"] } }
        Response: AttemptSerializer
        """
        quiz = self.get_object()
        try:
            attempt = Attempt.objects.get(
                pk=attempt_id, quiz=quiz,
                user=request.user, status="in_progress"
            )
        except Attempt.DoesNotExist:
            return Response(
                {"detail": "In-progress attempt not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AttemptSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Merge new answers over existing saved answers
        merged = {**attempt.answers, **{
            str(k): [str(v) for v in vals]
            for k, vals in serializer.validated_data["answers"].items()
        }}
        attempt.answers = merged
        attempt.save(update_fields=["answers"])

        return Response(AttemptSerializer(attempt).data, status=status.HTTP_200_OK)

    # ── 3. submit ─────────────────────────────────────────────────────────
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated],
        url_path="submit/(?P<attempt_id>[0-9a-f-]+)"
    )
    def submit(self, request, pk=None, attempt_id=None):
        """
        Grade and finalise the attempt.

        - Works on `in_progress` attempts owned by the requesting user.
        - Unanswered questions are counted as wrong (score them as 0).
        - Any answers sent in the request payload are merged before grading
          so the client can send the last-edited answers in the same call.
        - Sets submitted_at = now(), which will be measurably later than
          started_at because the attempt was created when the quiz started.

        Payload (optional): { "answers": { "<question_id>": ["<choice_id>"] } }
        Response: AttemptResultSerializer (includes per-question feedback)
        """
        quiz = self.get_object()
        try:
            attempt = Attempt.objects.get(
                pk=attempt_id, quiz=quiz,
                user=request.user, status="in_progress"
            )
        except Attempt.DoesNotExist:
            return Response(
                {"detail": "In-progress attempt not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Merge any last-second answers from the request
        if request.data.get("answers"):
            serializer = AttemptSaveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            merged = {**attempt.answers, **{
                str(k): [str(v) for v in vals]
                for k, vals in serializer.validated_data["answers"].items()
            }}
            attempt.answers = merged

        score_percent, passed = _grade(quiz, attempt.answers)

        attempt.status = "submitted"
        attempt.score_percent = score_percent
        attempt.passed = passed
        attempt.submitted_at = timezone.now()   # ← This is NOW; started_at was earlier
        attempt.save(update_fields=["answers", "status", "score_percent", "passed", "submitted_at"])

        return Response(AttemptResultSerializer(attempt).data, status=status.HTTP_200_OK)

    # ── 4. my-attempts ───────────────────────────────────────────────────
    @action(
        detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated],
        url_path="my-attempts"
    )
    def my_attempts(self, request, pk=None):
        """
        List all attempts (both in_progress and submitted) by the requesting user for this quiz.
        Clients can use this to detect a resumable in_progress attempt.
        """
        quiz = self.get_object()
        attempts = Attempt.objects.filter(quiz=quiz, user=request.user)
        submitted   = [a for a in attempts if a.status == "submitted"]
        in_progress = [a for a in attempts if a.status == "in_progress"]

        return Response({
            "in_progress": AttemptSerializer(in_progress, many=True).data,
            "submitted":   AttemptResultSerializer(submitted, many=True).data,
        })


class QuizAdminViewSet(viewsets.ModelViewSet):
    """Staff-only CRUD for managing quizzes."""
    permission_classes = [permissions.IsAdminUser]
    queryset = Quiz.objects.prefetch_related("questions__choices").all()

    def get_serializer_class(self):
        if self.action in ("list",):
            return QuizListSerializer
        return QuizDetailSerializer
