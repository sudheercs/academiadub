from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.login_url = reverse("token_obtain_pair")

    def test_user_registration(self):
        payload = {
            "email": "student@example.com",
            "password": "securepassword123",
            "profile": {
                "name": "Test Student",
                "institution": "Test High",
                "grade_or_year": "10",
                "locale": "en",
                "guardian_consent": True
            }
        }
        
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, "student@example.com")

    def test_user_login(self):
        # Create a user first
        user = User.objects.create_user(email="login@example.com", password="mypassword")
        
        payload = {
            "email": "login@example.com",
            "password": "mypassword"
        }
        
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])
