import csv
import io

from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Quiz, Question, Choice, Attempt

# ── Sample CSV rows (question-scoped — no quiz metadata) ────────────────────
SAMPLE_ROWS = [
    [
        "question_text", "question_type",
        "choice_1", "choice_2", "choice_3", "choice_4",
        "correct_choices", "explanation",
    ],
    [
        "What is the output of print(type([]))?",
        "mcq",
        "<class 'list'>", "<class 'array'>", "<class 'tuple'>", "<class 'set'>",
        "1",
        "The built-in list type in Python is represented as <class 'list'>.",
    ],
    [
        "Which of the following are mutable in Python?",
        "multi",
        "list", "tuple", "dict", "str",
        "1,3",
        "Lists and dicts are mutable; tuples and strings are immutable.",
    ],
    [
        "What keyword is used to define a function in Python?",
        "mcq",
        "func", "define", "def", "function",
        "3",
        "Python uses the 'def' keyword to define functions.",
    ],
    [
        "Which of these is NOT a Python built-in data type?",
        "mcq",
        "list", "dict", "array", "tuple",
        "3",
        "array is not a built-in type — it lives in the array module.",
    ],
]

REQUIRED_HEADERS = {"question_text", "choice_1", "correct_choices"}


def _parse_and_import(quiz: Quiz, file_bytes: bytes) -> dict:
    """Parse CSV bytes and create Question + Choice objects for the given quiz."""
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"error": "File must be UTF-8 encoded."}

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    missing = REQUIRED_HEADERS - headers
    if missing:
        return {"error": f"Missing required columns: {', '.join(sorted(missing))}"}

    rows = list(reader)
    if not rows:
        return {"error": "CSV has no data rows."}

    questions_created = 0
    choices_created = 0
    row_errors = []
    next_order = quiz.questions.count()

    for idx, row in enumerate(rows, start=2):
        q_text = (row.get("question_text") or "").strip()
        if not q_text:
            row_errors.append(f"Row {idx}: question_text is empty — skipped.")
            continue

        raw_choices = [
            (row.get(f"choice_{i}") or "").strip() for i in range(1, 5)
        ]
        choice_texts = [c for c in raw_choices if c]
        if len(choice_texts) < 2:
            row_errors.append(f"Row {idx}: need at least 2 choices — skipped.")
            continue

        correct_raw = (row.get("correct_choices") or "").strip()
        correct_indices: set[int] = set()
        for part in correct_raw.split(","):
            part = part.strip()
            if part.isdigit():
                ci = int(part)
                if 1 <= ci <= len(choice_texts):
                    correct_indices.add(ci)

        if not correct_indices:
            row_errors.append(
                f"Row {idx}: correct_choices='{correct_raw}' is invalid — "
                f"must be 1-based index(es) ≤ {len(choice_texts)} — skipped."
            )
            continue

        q_type = (row.get("question_type") or "mcq").strip().lower()
        if q_type not in ("mcq", "multi"):
            q_type = "mcq"

        question = Question.objects.create(
            quiz=quiz,
            text=q_text,
            question_type=q_type,
            explanation=(row.get("explanation") or "").strip(),
            order=next_order,
        )
        next_order += 1
        questions_created += 1

        for order_i, text in enumerate(choice_texts, start=1):
            Choice.objects.create(
                question=question,
                text=text,
                is_correct=(order_i in correct_indices),
                order=order_i,
            )
            choices_created += 1

    return {
        "questions_created": questions_created,
        "choices_created": choices_created,
        "row_errors": row_errors,
        "note": (
            f"{questions_created} question(s) added to '{quiz.title}'. "
            "Review the quiz and activate it when ready."
        ) if questions_created else "No questions were imported.",
    }


# ── Inlines ─────────────────────────────────────────────────────────────────

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ["text", "is_correct", "order"]


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ["text", "question_type", "explanation", "order"]
    show_change_link = True


# ── QuizAdmin ────────────────────────────────────────────────────────────────

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display  = ["title", "topic", "pass_mark", "time_limit_minutes", "is_active",
                     "question_count", "created_at", "import_link"]
    list_filter   = ["is_active", "topic__course__subject"]
    search_fields = ["title", "topic__title"]
    inlines       = [QuestionInline]
    autocomplete_fields = ["topic"]

    # ── Custom column: question count ────────────────────────────────────
    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count()

    # ── Custom column: import button ─────────────────────────────────────
    @admin.display(description="Import CSV")
    def import_link(self, obj):
        url = reverse("admin:practice_quiz_import_questions", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="'
            'padding:3px 10px;background:#3182ce;color:#fff;'
            'border-radius:4px;font-size:.8rem;text-decoration:none;">'
            '📥 Import CSV</a>',
            url,
        )

    # ── "Import Questions" button on the change page ─────────────────────
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_questions_url"] = reverse(
            "admin:practice_quiz_import_questions", args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def render_change_form(self, request, context, *args, **kwargs):
        # Inject the Import button into the submit row
        import_url = context.get("import_questions_url", "")
        if import_url:
            context.setdefault("adminform", context.get("adminform"))
            context["import_questions_url"] = import_url
        return super().render_change_form(request, context, *args, **kwargs)

    # ── Extra admin URLs ─────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<uuid:quiz_pk>/import-questions/",
                self.admin_site.admin_view(self.import_questions_view),
                name="practice_quiz_import_questions",
            ),
        ]
        return custom + urls

    def import_questions_view(self, request, quiz_pk):
        quiz = get_object_or_404(Quiz, pk=quiz_pk)

        # ── GET ?sample=1  →  download sample CSV ────────────────────────
        if request.method == "GET" and request.GET.get("sample") == "1":
            output = io.StringIO()
            csv.writer(output).writerows(SAMPLE_ROWS)
            resp = HttpResponse(output.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="quiz_questions_sample.csv"'
            return resp

        # ── POST  →  AJAX import ─────────────────────────────────────────
        if request.method == "POST":
            uploaded = request.FILES.get("file")
            if not uploaded:
                return JsonResponse({"error": "No file uploaded."}, status=400)
            if not uploaded.name.lower().endswith(".csv"):
                return JsonResponse({"error": "Only .csv files are accepted."}, status=400)

            result = _parse_and_import(quiz, uploaded.read())
            if "error" in result:
                return JsonResponse(result, status=400)
            return JsonResponse(result, status=201)

        # ── GET  →  render upload page ───────────────────────────────────
        context = {
            **self.admin_site.each_context(request),
            "quiz": quiz,
            "title": f"Import Questions — {quiz.title}",
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request,
            "admin/practice/quiz/import_questions.html",
            context,
        )


# ── Other admin registrations ────────────────────────────────────────────────

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display  = ["text", "quiz", "question_type", "order"]
    list_filter   = ["question_type", "quiz"]
    search_fields = ["text"]
    inlines       = [ChoiceInline]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display     = ["user", "quiz", "status", "score_percent", "passed", "started_at", "submitted_at"]
    list_filter      = ["status", "passed", "quiz"]
    search_fields    = ["user__email", "quiz__title"]
    readonly_fields  = ["status", "answers", "score_percent", "passed", "started_at", "submitted_at"]
