from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "active")
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("suspended", "Suspended"), ("pending", "Pending Verification")],
        default="pending",
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    mfa_secret = models.CharField(max_length=255, null=True, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def has_permission(self, permission_key, scope_type=None, scope_id=None):
        if not self.is_authenticated:
            return False
        if self.is_superuser:
            return True
        assignments = self.roles.filter(role__permissions__key=permission_key)
        if scope_type is None:
            return assignments.filter(scope_type="global").exists()
        return assignments.filter(
            models.Q(scope_type="global")
            | models.Q(scope_type=scope_type, scope_id=str(scope_id))
        ).exists()

    def has_role(self, role_key):
        return self.roles.filter(role__key=role_key).exists()

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=150)
    institution = models.CharField(max_length=150, blank=True)
    grade_or_year = models.CharField(max_length=50, blank=True)
    locale = models.CharField(max_length=10, default="en")
    guardian_consent = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Permission(models.Model):
    key = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.key


class Role(models.Model):
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission, related_name="roles")

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    scope_type = models.CharField(
        max_length=50,
        choices=[("global", "Global"), ("subject", "Subject"), ("class", "Class")],
        default="global",
    )
    scope_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        unique_together = ("user", "role", "scope_type", "scope_id")

    def __str__(self):
        return f"{self.user.email} - {self.role.key} ({self.scope_type})"


class Consent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    purpose = models.CharField(max_length=100)
    granted = models.BooleanField(default=True)
    policy_version = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.email} - {self.purpose}"
