from django.contrib import admin
from .models import Classroom, Enrollment, Assignment


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    readonly_fields = ("student", "enrolled_at", "status")
    can_delete = False


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
    readonly_fields = ("id", "join_code", "created_at", "updated_at")
    inlines = [AssignmentInline, EnrollmentInline]

    def student_count(self, obj):
        return obj.enrollments.filter(status="active").count()
    student_count.short_description = "Students"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "classroom", "status", "enrolled_at")
    list_filter = ("status",)
    search_fields = ("student__email", "classroom__name")
    readonly_fields = ("enrolled_at",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("classroom", "topic", "due_at", "created_at")
    list_filter = ("classroom",)
    search_fields = ("classroom__name", "topic__title")
    readonly_fields = ("created_at",)
