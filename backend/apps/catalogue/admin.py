from django.contrib import admin
from .models import Subject, Topic, TopicVersion


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "icon")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class TopicVersionInline(admin.TabularInline):
    model = TopicVersion
    extra = 0
    readonly_fields = ("version_no", "author", "state", "created_at")
    fields = ("version_no", "state", "author", "review_note", "created_at")
    can_delete = False
    show_change_link = True


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "slug", "difficulty", "access_level", "status", "order")
    list_filter = ("status", "difficulty", "access_level", "subject")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("subject", "order")
    inlines = [TopicVersionInline]


@admin.register(TopicVersion)
class TopicVersionAdmin(admin.ModelAdmin):
    list_display = ("topic", "version_no", "state", "author", "created_at")
    list_filter = ("state",)
    search_fields = ("topic__title",)
    readonly_fields = ("created_at", "version_no")
    raw_id_fields = ("topic", "author")
