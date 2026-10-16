from django.db import migrations


ROLE_PERMISSIONS = {
    "student": ["topic:read"],
    "editor": ["topic:read", "topic:manage"],
    "reviewer": ["topic:read", "topic:manage", "topic:publish"],
    "instructor": ["class:create", "class:manage", "class:view_analytics"],
    "admin": [
        "user:manage",
        "topic:manage",
        "topic:publish",
        "class:create",
        "class:manage",
        "class:view_analytics",
    ],
}


def seed_roles(apps, schema_editor):
    Permission = apps.get_model("identity", "Permission")
    Role = apps.get_model("identity", "Role")
    database = schema_editor.connection.alias

    for role_key, permission_keys in ROLE_PERMISSIONS.items():
        role, _ = Role.objects.using(database).get_or_create(
            key=role_key,
            defaults={"name": role_key.replace("_", " ").title()},
        )
        for permission_key in permission_keys:
            permission, _ = Permission.objects.using(database).get_or_create(
                key=permission_key,
                defaults={
                    "description": permission_key.replace(":", " ").replace("_", " ").title()
                },
            )
            role.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("identity", "0002_alter_userrole_scope_id")]

    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
