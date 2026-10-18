"""
Phase 7 — Security & API tests for the identity app.
Covers: registration, login throttle, JWT tokens, current-user endpoint.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("register")

    def test_register_with_valid_data(self):
        res = self.client.post(
            self.url,
            {
                "email": "new@test.com",
                "password": "SecurePass123!",
                "profile": {"name": "New User"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("email", res.data)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@test.com", password="pass")
        res = self.client.post(self.url, {"email": "dup@test.com", "password": "pass"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        res = self.client.post(self.url, {"email": "nopw@test.com"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        res = self.client.post(self.url, {"email": "not-an-email", "password": "pass"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("token_obtain_pair")
        self.user = User.objects.create_user(
            email="login@test.com", password="Password123!"
        )

    def test_login_valid_credentials(self):
        res = self.client.post(
            self.url, {"email": "login@test.com", "password": "Password123!"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", res.data)
        self.assertNotIn("refresh", res.data)
        self.assertTrue(res.cookies["access_token"]["httponly"])
        self.assertTrue(res.cookies["refresh_token"]["httponly"])

    def test_cookie_authentication_and_refresh(self):
        login = self.client.post(
            self.url,
            {"email": "login@test.com", "password": "Password123!"},
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        me = self.client.get(reverse("current_user"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], self.user.email)

        old_refresh = self.client.cookies["refresh_token"].value
        refreshed = self.client.post(reverse("token_refresh"))
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", refreshed.data)
        self.assertNotEqual(self.client.cookies["refresh_token"].value, old_refresh)

    def test_logout_clears_and_blacklists_refresh_cookie(self):
        self.client.post(
            self.url,
            {"email": "login@test.com", "password": "Password123!"},
        )
        old_refresh = self.client.cookies["refresh_token"].value
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies["access_token"]["max-age"], 0)
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)

        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        serializer = TokenRefreshSerializer(data={"refresh": old_refresh})
        with self.assertRaises(TokenError):
            serializer.is_valid(raise_exception=True)

    def test_login_wrong_password(self):
        res = self.client.post(
            self.url, {"email": "login@test.com", "password": "wrongpassword"}
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        res = self.client.post(
            self.url, {"email": "ghost@test.com", "password": "anything"}
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class CookieCsrfTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            email="csrf@test.com",
            password="Password123!",
        )

    def test_cookie_login_and_logout_require_csrf_token(self):
        login_url = reverse("token_obtain_pair")
        credentials = {"email": "csrf@test.com", "password": "Password123!"}

        rejected = self.client.post(login_url, credentials)
        self.assertEqual(rejected.status_code, 403)

        self.client.get(reverse("csrf-token"))
        csrf_token = self.client.cookies["csrftoken"].value
        headers = {"HTTP_X_CSRFTOKEN": csrf_token}
        login = self.client.post(login_url, credentials, **headers)
        self.assertEqual(login.status_code, 200)

        rejected_logout = Client(enforce_csrf_checks=True).post(reverse("logout"))
        self.assertEqual(rejected_logout.status_code, 403)
        logout = self.client.post(reverse("logout"), **headers)
        self.assertEqual(logout.status_code, 200)


class CurrentUserTests(APITestCase):
    def setUp(self):
        self.url = reverse("current_user")
        self.user = User.objects.create_user(email="me@test.com", password="pass")

    def test_get_current_user_authenticated(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "me@test.com")

    def test_get_current_user_unauthenticated(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
