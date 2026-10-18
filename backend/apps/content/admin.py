from django.contrib import admin

from .models import Bookmark, UserProgress


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "state", "read_at", "completed_at")
    list_filter = ("state",)
    search_fields = ("user__email", "topic__title")
    readonly_fields = ("read_at",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "created_at")
    search_fields = ("user__email", "topic__title")
    readonly_fields = ("created_at",)
