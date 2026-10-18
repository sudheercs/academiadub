from rest_framework import serializers

from .models import Attempt, Choice, Question, Quiz


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "order"]
        # NOTE: is_correct is intentionally excluded — sent only in submit response


class ChoiceWithAnswerSerializer(serializers.ModelSerializer):
    """Includes the correct flag — used only in post-submit feedback."""

    class Meta:
        model = Choice
        fields = ["id", "text", "order", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "order", "choices"]


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """Includes explanation and correct answers — used in post-submit feedback."""

    choices = ChoiceWithAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "order", "choices", "explanation"]


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "pass_mark",
            "time_limit_minutes",
            "question_count",
        ]

    def get_question_count(self, obj):
        return obj.questions.count()


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "pass_mark",
            "time_limit_minutes",
            "questions",
        ]


class AttemptSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for in-progress attempts.
    Exposes status, saved answers, and timestamps — no grading info.
    Used for start / save / resume responses.
    """

    class Meta:
        model = Attempt
        fields = ["id", "quiz", "status", "answers", "started_at", "submitted_at"]
        read_only_fields = ["id", "quiz", "started_at", "submitted_at", "status"]


class AttemptSaveSerializer(serializers.Serializer):
    """Validates a save-progress payload (partial answers are fine)."""

    answers = serializers.DictField(
        child=serializers.ListField(child=serializers.UUIDField()),
        help_text="Map of question_id (str) → list of chosen choice_ids (str). Partial is OK.",
    )


class AttemptResultSerializer(serializers.ModelSerializer):
    """Full graded result — returned only after submission."""

    questions = QuestionWithAnswerSerializer(
        source="quiz.questions", many=True, read_only=True
    )

    class Meta:
        model = Attempt
        fields = [
            "id",
            "status",
            "score_percent",
            "passed",
            "answers",
            "started_at",
            "submitted_at",
            "questions",
        ]
