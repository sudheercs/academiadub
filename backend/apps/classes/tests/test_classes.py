"""
Phase 7 — Tests for the classes app.
Covers: classroom CRUD, join by code, enrollment, analytics endpoint.
"""
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.classes.models import Classroom, Enrollment, Assignment
from apps.catalogue.models import Subject, Topic
import random, string

User = get_user_model()


def gen_code():
    return "".join(random.choices(string.ascii_uppercase, k=8))


class ClassroomTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(email="instructor@test.com", password="pass", is_staff=True)
        self.student = User.objects.create_user(email="student@test.com", password="pass")
        self.classroom = Classroom.objects.create(
            name="Test Class", instructor=self.instructor, join_code=gen_code()
        )

    def test_instructor_can_list_own_class(self):
        self.client.force_authenticate(user=self.instructor)
        res = self.client.get("/api/classes/classrooms/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [c["name"] for c in (res.data.get("results") or res.data)]
        self.assertIn("Test Class", names)

    def test_unauthenticated_cannot_list_classes(self):
        res = self.client.get("/api/classes/classrooms/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_joins_by_code(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post("/api/classes/join/", {"join_code": self.classroom.join_code})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(classroom=self.classroom, student=self.student).exists()
        )

    def test_join_invalid_code_returns_404(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post("/api/classes/join/", {"join_code": "BADCODE1"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_instructor_cannot_join_own_class(self):
        self.client.force_authenticate(user=self.instructor)
        res = self.client.post("/api/classes/join/", {"join_code": self.classroom.join_code})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analytics_requires_instructor(self):
        # Enroll student so they can see the class, then check analytics is still forbidden
        Enrollment.objects.create(classroom=self.classroom, student=self.student, status="active")
        self.client.force_authenticate(user=self.student)
        url = f"/api/classes/classrooms/{self.classroom.id}/analytics/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_analytics_returns_data_for_instructor(self):
        self.client.force_authenticate(user=self.instructor)
        url = f"/api/classes/classrooms/{self.classroom.id}/analytics/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("assignments", res.data)
        self.assertIn("total_students", res.data)

    def test_export_csv_for_instructor(self):
        self.client.force_authenticate(user=self.instructor)
        url = f"/api/classes/classrooms/{self.classroom.id}/export/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
