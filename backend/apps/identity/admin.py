from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Consent, Permission, Profile, Role, User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for email-based User model."""

    ordering = ("-created_at",)
    list_display = (
        "email",
        "status",
        "is_staff",
        "is_superuser",
        "email_verified_at",
        "created_at",
    )
    list_filter = ("status", "is_staff", "is_superuser", "is_active")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Status"), {"fields": ("status", "email_verified_at", "is_active")}),
        (_("Staff"), {"fields": ("is_staff", "is_superuser")}),
        (_("Security"), {"fields": ("mfa_secret",)}),
        (_("Permissions"), {"fields": ("groups", "user_permissions")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "last_login")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "status",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    # email is the USERNAME_FIELD, not username
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "institution", "locale", "guardian_consent")
    search_fields = ("user__email", "name", "institution")
    list_filter = ("locale", "guardian_consent")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("key", "name")
    search_fields = ("key", "name")
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("key", "description")
    search_fields = ("key",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "scope_type", "scope_id")
    list_filter = ("scope_type", "role")
    search_fields = ("user__email",)
    autocomplete_fields = ("user",)


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "granted", "policy_version", "timestamp")
    list_filter = ("granted", "purpose")
    search_fields = ("user__email",)
    readonly_fields = ("timestamp",)
