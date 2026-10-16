import json
from django import forms
from django.contrib import admin
from .models import Subject, Course, Topic, TopicVersion, TopicVersionEvent


BLOCKS_PLACEHOLDER = json.dumps([
    {"type": "paragraph", "content": "Write your introduction here. **Bold** and *italic* supported."},
    {"type": "heading", "content": "Section Title"},
    {"type": "code_snippet", "language": "python", "content": "print('Hello, World!')"},
    {"type": "callout", "variant": "info", "content": "Tip: use callout blocks for important notes."},
    {"type": "youtube", "url": "https://youtu.be/VIDEO_ID", "caption": "Optional caption"},
    {"type": "code_lab", "language": "python", "starter_code": "# Try it yourself!\nprint('edit me')"},
], indent=2)


class TopicVersionAdminForm(forms.ModelForm):
    blocks = forms.JSONField(
        widget=forms.Textarea(attrs={
            "rows": 30,
            "style": "font-family: monospace; font-size: 13px; width: 100%;",
        }),
        help_text=(
            "JSON array of content blocks. Supported types: "
            "<code>paragraph</code>, <code>heading</code>, <code>code_snippet</code>, "
            "<code>callout</code>, <code>youtube</code>, <code>image</code>, <code>code_lab</code>. "
            "<br><br>See the placeholder in a new version for the exact schema."
        ),
        initial=json.loads(BLOCKS_PLACEHOLDER),
    )

    class Meta:
        model = TopicVersion
        fields = "__all__"


class TopicVersionInline(admin.StackedInline):
    model = TopicVersion
    form = TopicVersionAdminForm
    extra = 0
    readonly_fields = ("version_no", "state", "author", "review_note", "blocks", "created_at", "updated_at")
    fields = ("version_no", "state", "author", "review_note", "blocks", "created_at")
    show_change_link = True
    can_delete = False


class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    show_change_link = True
    fields = ("title", "slug", "difficulty", "status", "order")
    prepopulated_fields = {"slug": ("title",)}


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    show_change_link = True
    fields = ("title", "slug", "difficulty", "access_level", "status", "order")
    readonly_fields = ("status",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "icon")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CourseInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "slug", "difficulty", "status", "order")
    list_filter = ("status", "difficulty", "subject")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("subject", "order")
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "get_subject", "slug", "difficulty", "access_level", "status", "current_version_id", "order")
    list_filter = ("status", "difficulty", "access_level", "course__subject", "course")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("course", "order")
    readonly_fields = ("created_at", "updated_at", "status", "current_version_id")
    inlines = [TopicVersionInline]

    @admin.display(description="Subject", ordering="course__subject")
    def get_subject(self, obj):
        return obj.course.subject if obj.course else "-"


@admin.register(TopicVersion)
class TopicVersionAdmin(admin.ModelAdmin):
    list_display = ("topic", "version_no", "state", "author", "created_at")
    list_filter = ("state",)
    search_fields = ("topic__title",)
    readonly_fields = (
        "topic", "created_at", "updated_at", "version_no", "author",
        "state", "review_note", "blocks",
    )
    raw_id_fields = ("topic",)

    fieldsets = (
        (None, {"fields": ("topic", "version_no", "state", "author")}),
        ("Content Blocks (JSON)", {"fields": ("blocks",)}),
        ("Review", {"fields": ("review_note",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj) and super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TopicVersionEvent)
class TopicVersionEventAdmin(admin.ModelAdmin):
    list_display = ("topic", "version_no", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("topic__title", "actor__email", "note")
    readonly_fields = (
        "topic", "version", "version_no", "actor", "action", "note", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj) and super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
