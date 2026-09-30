from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Profile, Role, UserRole

User = get_user_model()


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
        profile_data = validated_data.pop('profile')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, **profile_data)
        
        # Assign default 'student' role
        student_role, _ = Role.objects.get_or_create(key="student", defaults={"name": "Student"})
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
