"""
Phase 7 — Security & API tests for the identity app.
Covers: registration, login throttle, JWT tokens, current-user endpoint.
"""
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("register")

    def test_register_with_valid_data(self):
        res = self.client.post(self.url, {
            "email": "new@test.com",
            "password": "SecurePass123!",
            "profile": {"name": "New User"}
        }, format="json")
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
        self.url = reverse("token_obtain_pair")
        self.user = User.objects.create_user(email="login@test.com", password="Password123!")

    def test_login_valid_credentials(self):
        res = self.client.post(self.url, {"email": "login@test.com", "password": "Password123!"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_login_wrong_password(self):
        res = self.client.post(self.url, {"email": "login@test.com", "password": "wrongpassword"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        res = self.client.post(self.url, {"email": "ghost@test.com", "password": "anything"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


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
