from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.catalogue.models import Subject, Topic
from django.contrib.auth import get_user_model

User = get_user_model()


class CatalogueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.subject = Subject.objects.create(
            slug="python",
            name="Python Programming",
            status="published"
        )
        self.topic = Topic.objects.create(
            subject=self.subject,
            slug="intro",
            title="Introduction to Python",
            status="published",
            access_level="free"
        )
        self.admin = User.objects.create_superuser(email="admin@example.com", password="password")
        self.student = User.objects.create_user(email="student@example.com", password="password")

    def test_list_subjects(self):
        url = reverse("subject-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "python")

    def test_list_topics(self):
        url = reverse("topic-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "intro")

    def test_draft_subject_hidden_from_public(self):
        Subject.objects.create(slug="draft-subj", name="Draft", status="draft")
        url = reverse("subject-list")
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1) # Only published

    def test_draft_subject_visible_to_admin(self):
        Subject.objects.create(slug="draft-subj", name="Draft", status="draft")
        url = reverse("subject-list")
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 2) # Both published and draft

    def test_create_topic_version(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("topic-versions-list", kwargs={"topic_pk": self.topic.id})
        payload = {
            "blocks": [{"type": "text", "content": "Hello World"}],
            "state": "draft"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["version_no"], 1)
        self.assertEqual(self.topic.versions.count(), 1)
