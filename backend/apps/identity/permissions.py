from rest_framework.permissions import BasePermission


class RequirePermission(BasePermission):
    permission_key = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if self.permission_key is None:
            return True
        get_scope = getattr(view, "get_permission_scope", None)
        scope_type, scope_id = (
            get_scope(self.permission_key) if get_scope else (None, None)
        )
        permission_check = getattr(view, "user_has_permission", None)
        if permission_check:
            return permission_check(
                request.user,
                self.permission_key,
                scope_type,
                scope_id,
            )
        return request.user.has_permission(self.permission_key, scope_type, scope_id)


class RequireTopicManagePermission(RequirePermission):
    permission_key = "topic:manage"


class RequireTopicPublishPermission(RequirePermission):
    permission_key = "topic:publish"


class RequireClassManagePermission(RequirePermission):
    permission_key = "class:manage"


class RequireClassAnalyticsPermission(RequirePermission):
    permission_key = "class:view_analytics"


class RequireClassCreatePermission(RequirePermission):
    permission_key = "class:create"


def subject_scope_ids(user, permission_key):
    if not user.is_authenticated:
        return []
    return user.roles.filter(
        scope_type="subject",
        role__permissions__key=permission_key,
    ).values_list("scope_id", flat=True)
