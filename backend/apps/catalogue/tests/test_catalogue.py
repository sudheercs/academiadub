from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalogue.models import Course, Subject, Topic, TopicVersionEvent
from apps.identity.models import Permission, Role, UserRole

User = get_user_model()


class CatalogueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.subject = Subject.objects.create(
            slug="python",
            name="Python Programming",
            status="published"
        )
        self.course = Course.objects.create(
            subject=self.subject,
            slug="python-basics",
            title="Python Basics",
            difficulty="beginner",
            status="published"
        )
        self.topic = Topic.objects.create(
            course=self.course,
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

    def test_list_courses(self):
        url = reverse("course-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "python-basics")
        self.assertEqual(response.data["results"][0]["subject"]["slug"], "python")

    def test_filter_courses_by_subject(self):
        other_subject = Subject.objects.create(slug="js", name="JavaScript", status="published")
        Course.objects.create(subject=other_subject, slug="js-basics", title="JS Basics", status="published")

        url = f"{reverse('course-list')}?subject=python"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "python-basics")

    def test_course_detail_includes_topics(self):
        url = reverse("course-detail", kwargs={"pk": self.course.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "python-basics")
        self.assertEqual(len(response.data["topics"]), 1)
        self.assertEqual(response.data["topics"][0]["slug"], "intro")

    def test_list_topics(self):
        url = reverse("topic-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "intro")
        self.assertEqual(response.data["results"][0]["course"]["slug"], "python-basics")
        self.assertEqual(response.data["results"][0]["subject"]["slug"], "python")

    def test_filter_topics_by_course(self):
        course2 = Course.objects.create(subject=self.subject, slug="python-adv", title="Advanced", status="published")
        Topic.objects.create(course=course2, slug="metaclasses", title="Metaclasses", status="published")

        url = f"{reverse('topic-list')}?course=python-basics"
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "intro")

    def test_filter_topics_by_subject(self):
        other_subject = Subject.objects.create(slug="rust", name="Rust", status="published")
        other_course = Course.objects.create(subject=other_subject, slug="rust-basics", title="Rust 101", status="published")
        Topic.objects.create(course=other_course, slug="ownership", title="Ownership", status="published")

        url = f"{reverse('topic-list')}?subject=python"
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "intro")

    def test_draft_course_hidden_from_public(self):
        Course.objects.create(subject=self.subject, slug="draft-course", title="Draft Course", status="draft")
        url = reverse("course-list")
        response = self.client.get(url)
        slugs = [c["slug"] for c in response.data["results"]]
        self.assertNotIn("draft-course", slugs)

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

    def assign_role(self, user, role_key, permission_keys, scope_id):
        role, _ = Role.objects.get_or_create(key=role_key, defaults={"name": role_key.title()})
        for key in permission_keys:
            permission, _ = Permission.objects.get_or_create(key=key, defaults={"description": key})
            role.permissions.add(permission)
        UserRole.objects.create(
            user=user,
            role=role,
            scope_type="subject",
            scope_id=str(scope_id),
        )

    def test_editor_permission_is_limited_to_assigned_subject(self):
        editor = User.objects.create_user(email="editor@example.com", password="EditorPass123!")
        other_subject = Subject.objects.create(
            slug="javascript",
            name="JavaScript",
            status="published",
        )
        other_course = Course.objects.create(
            subject=other_subject,
            slug="javascript-basics",
            title="JavaScript Basics",
            status="published",
        )
        other_topic = Topic.objects.create(
            course=other_course,
            slug="intro",
            title="Introduction",
            status="published",
        )
        self.assign_role(editor, "editor", ["topic:manage"], self.subject.id)
        self.client.force_authenticate(user=editor)

        allowed = self.client.post(
            f"/api/catalogue/topics/{self.topic.id}/versions/",
            {"blocks": [{"type": "text", "content": "Scoped draft"}]},
            format="json",
        )
        denied = self.client.post(
            f"/api/catalogue/topics/{other_topic.id}/versions/",
            {"blocks": [{"type": "text", "content": "Out of scope"}]},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_editorial_review_publish_lifecycle(self):
        editor = User.objects.create_user(email="writer@example.com", password="WriterPass123!")
        reviewer = User.objects.create_user(email="reviewer@example.com", password="ReviewerPass123!")
        self.assign_role(editor, "editor", ["topic:manage"], self.subject.id)
        self.assign_role(reviewer, "reviewer", ["topic:publish"], self.subject.id)

        self.client.force_authenticate(user=editor)
        response = self.client.post(
            f"/api/catalogue/topics/{self.topic.id}/versions/",
            {"blocks": [{"type": "markdown", "content": "Reviewed text"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        version_id = response.data["id"]
        base_url = f"/api/catalogue/topics/{self.topic.id}/versions/{version_id}"

        submitted = self.client.post(f"{base_url}/submit/")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        self.assertEqual(submitted.data["state"], "in_review")

        self.client.force_authenticate(user=reviewer)
        approved = self.client.post(
            f"{base_url}/review/",
            {"approved": True, "review_note": "Looks good."},
            format="json",
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["state"], "approved")

        published = self.client.post(f"{base_url}/publish/")
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.status, "published")
        self.assertEqual(self.topic.current_version_id, response.data["version_no"])
        self.assertEqual(
            list(
                TopicVersionEvent.objects.filter(topic=self.topic)
                .order_by("created_at", "id")
                .values_list("action", flat=True)
            ),
            ["created", "submitted", "approved", "published"],
        )

        self.client.force_authenticate(user=editor)
        blocked_edit = self.client.patch(
            f"{base_url}/",
            {"blocks": [{"type": "markdown", "content": "Changed after publish"}]},
            format="json",
        )
        self.assertEqual(blocked_edit.status_code, status.HTTP_400_BAD_REQUEST)
