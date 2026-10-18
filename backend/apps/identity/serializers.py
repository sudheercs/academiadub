from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Permission, Profile, Role, UserRole

User = get_user_model()

DEFAULT_ROLE_PERMISSIONS = {
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


def ensure_role_permissions(role):
    for permission_key in DEFAULT_ROLE_PERMISSIONS.get(role.key, []):
        permission, _ = Permission.objects.get_or_create(
            key=permission_key,
            defaults={"description": permission_key.replace(":", " ").title()},
        )
        role.permissions.add(permission)
    return role


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("name", "institution", "grade_or_year", "locale", "guardian_consent")


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "email", "status", "is_staff", "profile", "created_at")
        read_only_fields = ("id", "status", "is_staff", "created_at")


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ("email", "password", "profile")

    def create(self, validated_data):
        profile_data = validated_data.pop("profile")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        Profile.objects.create(user=user, **profile_data)

        student_role, _ = Role.objects.get_or_create(key="student", defaults={"name": "Student"})
        ensure_role_permissions(student_role)
        UserRole.objects.create(user=user, role=student_role, scope_type="global")

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['status'] = user.status
        token['roles'] = list(user.roles.values_list('role__key', flat=True))

        return token
