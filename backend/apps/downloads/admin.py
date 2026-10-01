from django.contrib import admin
from .models import Download, DownloadLog


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "access_level", "mime_type", "file_size_bytes", "uploaded_by")
    list_filter = ("access_level", "mime_type")
    search_fields = ("title", "topic__title")
    readonly_fields = ("file_size_bytes", "mime_type")
    raw_id_fields = ("topic", "uploaded_by")


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ("download", "user", "ip_address", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("user__email", "download__title")
    readonly_fields = ("download", "user", "ip_address", "user_agent", "timestamp")

    def has_add_permission(self, request):
        return False  # Audit log — no manual entries

    def has_change_permission(self, request, obj=None):
        return False  # Read-only
