from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Classroom, Enrollment, Assignment


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    readonly_fields = ("student", "enrolled_at", "student_secret_display", "status")
    can_delete = False
    fields = ("student", "status", "student_secret_display", "enrolled_at")

    @admin.display(description="Student Secret (PIN)")
    def student_secret_display(self, obj):
        if obj.pk:
            return format_html(
                '<code style="font-size:1.1em;letter-spacing:2px;background:#1e293b;padding:2px 8px;border-radius:4px;">{}</code>',
                obj.student_secret or "—"
            )
        return "—"


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1
    fields = ("topic", "title", "due_at")
    autocomplete_fields = ("topic",)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "instructor", "join_code", "is_active", "student_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "instructor__email", "join_code")
    # join_code is editable — leave blank to auto-generate, or set a custom value
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "name", "description", "instructor", "join_code", "is_active", "created_at", "updated_at")
    inlines = [AssignmentInline, EnrollmentInline]
    actions = ["regenerate_join_code"]

    def student_count(self, obj):
        return obj.enrollments.filter(status="active").count()
    student_count.short_description = "Students"

    @admin.action(description="🔄 Regenerate join code for selected classrooms")
    def regenerate_join_code(self, request, queryset):
        count = 0
        for classroom in queryset:
            classroom.join_code = ""  # blank triggers auto-gen in save()
            classroom.save()
            count += 1
        self.message_user(request, f"Regenerated join codes for {count} classroom(s).", messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        # If admin cleared the join_code field, auto-generate it
        if not obj.join_code:
            obj.join_code = ""  # save() will generate
        super().save_model(request, obj, form, change)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "classroom", "status", "student_secret_display", "enrolled_at")
    list_filter = ("status", "classroom")
    search_fields = ("student__email", "classroom__name")
    readonly_fields = ("enrolled_at", "student_secret")
    actions = ["regenerate_student_secrets"]

    @admin.display(description="Secret PIN")
    def student_secret_display(self, obj):
        return format_html(
            '<code style="font-size:1.1em;letter-spacing:2px;background:#1e293b;padding:2px 6px;border-radius:4px;">{}</code>',
            obj.student_secret or "—"
        )

    @admin.action(description="🔑 Regenerate student secret PINs")
    def regenerate_student_secrets(self, request, queryset):
        count = 0
        for enrollment in queryset:
            enrollment.regenerate_secret()
            count += 1
        self.message_user(request, f"Regenerated secret PINs for {count} enrollment(s).", messages.SUCCESS)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("classroom", "topic", "due_at", "created_at")
    list_filter = ("classroom",)
    search_fields = ("classroom__name", "topic__title")
    readonly_fields = ("created_at",)
