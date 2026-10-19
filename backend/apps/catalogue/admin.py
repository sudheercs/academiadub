import json

from django import forms
from django.contrib import admin

from .models import Course, Subject, Topic, TopicVersion, TopicVersionEvent


def next_topic_version_no(topic):
    latest_version_no = topic.versions.order_by("-version_no").values_list(
        "version_no", flat=True
    ).first()
    return (latest_version_no or 0) + 1


def record_topic_version_event(version, actor, action):
    TopicVersionEvent.objects.create(
        topic=version.topic,
        version=version,
        version_no=version.version_no,
        actor=actor,
        action=action,
    )

BLOCKS_PLACEHOLDER = json.dumps(
    [
        {
            "type": "paragraph",
            "content": "Write your introduction here. **Bold** and *italic* supported.",
        },
        {"type": "heading", "content": "Section Title"},
        {
            "type": "code_snippet",
            "language": "python",
            "content": "print('Hello, World!')",
        },
        {
            "type": "callout",
            "variant": "info",
            "content": "Tip: use callout blocks for important notes.",
        },
        {
            "type": "youtube",
            "url": "https://youtu.be/VIDEO_ID",
            "caption": "Optional caption",
        },
        {
            "type": "code_lab",
            "language": "python",
            "starter_code": "# Try it yourself!\nprint('edit me')",
        },
    ],
    indent=2,
)


class TopicVersionAdminForm(forms.ModelForm):
    blocks = forms.JSONField(
        widget=forms.Textarea(
            attrs={
                "rows": 30,
                "style": "font-family: monospace; font-size: 13px; width: 100%;",
            }
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.state != "draft":
            self.fields["blocks"].disabled = True


class TopicVersionInline(admin.StackedInline):
    model = TopicVersion
    form = TopicVersionAdminForm
    extra = 1
    readonly_fields = (
        "version_no",
        "state",
        "author",
        "review_note",
        "created_at",
        "updated_at",
    )
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
    list_display = (
        "title",
        "course",
        "get_subject",
        "slug",
        "difficulty",
        "access_level",
        "status",
        "current_version_id",
        "order",
    )
    list_filter = ("status", "difficulty", "access_level", "course__subject", "course")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("course", "order")
    readonly_fields = ("created_at", "updated_at", "current_version_id")
    inlines = [TopicVersionInline]

    @admin.display(description="Subject", ordering="course__subject")
    def get_subject(self, obj):
        return obj.course.subject if obj.course else "-"

    def save_formset(self, request, form, formset, change):
        if formset.model is not TopicVersion:
            return super().save_formset(request, form, formset, change)

        versions = formset.save(commit=False)
        for version in formset.deleted_objects:
            version.delete()
        for version in versions:
            is_new = version._state.adding
            if is_new:
                version.version_no = next_topic_version_no(version.topic)
                version.author = request.user
                version.state = "draft"
            version.save()
            record_topic_version_event(
                version, request.user, "created" if is_new else "updated"
            )
        formset.save_m2m()


@admin.register(TopicVersion)
class TopicVersionAdmin(admin.ModelAdmin):
    list_display = ("topic", "version_no", "state", "author", "created_at")
    list_filter = ("state",)
    search_fields = ("topic__title",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "version_no",
        "author",
        "state",
        "review_note",
    )
    raw_id_fields = ("topic",)

    fieldsets = (
        (None, {"fields": ("topic", "version_no", "state", "author")}),
        ("Content Blocks (JSON)", {"fields": ("blocks",)}),
        ("Review", {"fields": ("review_note",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.state != "draft":
            return False
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None:
            readonly_fields = (*readonly_fields, "topic")
            if obj.state != "draft":
                readonly_fields = (*readonly_fields, "blocks")
        return readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            obj.version_no = next_topic_version_no(obj.topic)
            obj.author = request.user
            obj.state = "draft"
        super().save_model(request, obj, form, change)
        record_topic_version_event(
            obj, request.user, "updated" if change else "created"
        )


@admin.register(TopicVersionEvent)
class TopicVersionEventAdmin(admin.ModelAdmin):
    list_display = ("topic", "version_no", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("topic__title", "actor__email", "note")
    readonly_fields = (
        "topic",
        "version",
        "version_no",
        "actor",
        "action",
        "note",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj) and super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
