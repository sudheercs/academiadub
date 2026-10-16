from django.contrib import admin
from .models import CodeFolder, CodeSnippet, CodeFile


@admin.register(CodeFolder)
class CodeFolderAdmin(admin.ModelAdmin):
    list_display  = ["name", "user", "created_at"]
    list_filter   = ["created_at"]
    search_fields = ["name", "user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CodeSnippet)
class CodeSnippetAdmin(admin.ModelAdmin):
    list_display   = ["title", "user", "language", "folder", "size_bytes", "updated_at"]
    list_filter    = ["language", "folder"]
    search_fields  = ["title", "user__email"]
    readonly_fields = ["size_bytes", "created_at", "updated_at"]

@admin.register(CodeFile)
class CodeFileAdmin(admin.ModelAdmin):
    list_display   = ["filename", "user", "mime_type", "folder", "size_bytes", "updated_at"]
    list_filter    = ["mime_type", "folder"]
    search_fields  = ["filename", "user__email"]
    readonly_fields = ["size_bytes", "created_at", "updated_at"]
