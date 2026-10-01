import json
from django import forms
from django.contrib import admin, messages
from .models import Subject, Topic, TopicVersion


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
    readonly_fields = ("version_no", "author", "created_at", "updated_at")
    fields = ("version_no", "state", "author", "review_note", "blocks", "created_at")
    show_change_link = True
    can_delete = False


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "icon")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "slug", "difficulty", "access_level", "status", "current_version_id", "order")
    list_filter = ("status", "difficulty", "access_level", "subject")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("subject", "order")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TopicVersionInline]


@admin.register(TopicVersion)
class TopicVersionAdmin(admin.ModelAdmin):
    form = TopicVersionAdminForm
    list_display = ("topic", "version_no", "state", "author", "created_at")
    list_filter = ("state",)
    search_fields = ("topic__title",)
    readonly_fields = ("created_at", "updated_at", "version_no", "author")
    raw_id_fields = ("topic",)
    actions = ["publish_version"]

    fieldsets = (
        (None, {"fields": ("topic", "version_no", "state", "author")}),
        ("Content Blocks (JSON)", {
            "fields": ("blocks",),
            "description": (
                "<strong>Block types reference:</strong><br>"
                "<code>paragraph</code> — rich text (Markdown-style)<br>"
                "<code>heading</code> — section heading<br>"
                "<code>code_snippet</code> — syntax-highlighted code (add <code>language</code> field)<br>"
                "<code>callout</code> — info/warning/tip box (add <code>variant</code>: info|warning|tip)<br>"
                "<code>youtube</code> — embed video (add <code>url</code> + optional <code>caption</code>)<br>"
                "<code>image</code> — image block (add <code>url</code> + optional <code>caption</code>)<br>"
                "<code>code_lab</code> — interactive code runner (add <code>language</code> + <code>starter_code</code>)"
            ),
        }),
        ("Review", {"fields": ("review_note",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
            latest = TopicVersion.objects.filter(topic=obj.topic).order_by("-version_no").first()
            obj.version_no = (latest.version_no + 1) if latest else 1
        super().save_model(request, obj, form, change)

    @admin.action(description="✅ Publish selected versions (sets topic.current_version_id)")
    def publish_version(self, request, queryset):
        for version in queryset:
            version.state = "published"
            version.save()
            version.topic.status = "published"
            version.topic.current_version_id = version.version_no
            version.topic.save()
        self.message_user(request, f"Published {queryset.count()} version(s).", messages.SUCCESS)

