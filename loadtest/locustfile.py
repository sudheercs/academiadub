"""
Phase 7 — Load test using Locust.
Simulates concurrent students browsing the catalogue and running code.

Usage:
  pip install locust
  locust -f locustfile.py --host=http://localhost:8000
  Open http://localhost:8089 to control the test.

Targets (from plan.md §8):
  500 concurrent users, p95 API response < 400ms
"""

import random

from locust import HttpUser, between, task

SUBJECT_SLUGS = ["python", "react"]

FREE_TOPICS = [
    {"subject": "python", "id": 1},
]


class StudentUser(HttpUser):
    """Simulates a logged-in student browsing and reading content."""

    wait_time = between(1, 4)  # Realistic think-time between requests
    token = None

    def on_start(self):
        """Log in and store JWT token."""
        res = self.client.post(
            "/api/auth/login/",
            json={"email": "student@academiadub.in", "password": "student123"},
            name="/api/auth/login/",
        )
        if res.status_code == 200:
            self.token = res.json().get("access")

    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def browse_subjects(self):
        self.client.get(
            "/api/catalogue/subjects/",
            headers=self.auth_headers(),
            name="/api/catalogue/subjects/",
        )

    @task(5)
    def list_topics(self):
        slug = random.choice(SUBJECT_SLUGS)
        self.client.get(
            f"/api/catalogue/topics/?subject={slug}",
            headers=self.auth_headers(),
            name="/api/catalogue/topics/?subject=[slug]",
        )

    @task(3)
    def health_check(self):
        self.client.get("/api/health/", name="/api/health/")

    @task(2)
    def run_code(self):
        self.client.post(
            "/api/codelab/run/",
            json={"language": "python", "code": "print('hello')"},
            headers=self.auth_headers(),
            name="/api/codelab/run/",
        )


class AnonUser(HttpUser):
    """Simulates an anonymous visitor browsing public content."""

    wait_time = between(2, 6)

    @task(3)
    def browse_subjects(self):
        self.client.get("/api/catalogue/subjects/", name="/api/catalogue/subjects/")

    @task(2)
    def list_topics(self):
        slug = random.choice(SUBJECT_SLUGS)
        self.client.get(
            f"/api/catalogue/topics/?subject={slug}",
            headers={},
            name="/api/catalogue/topics/?subject=[slug]",
        )

    @task(1)
    def health_check(self):
        self.client.get("/api/health/", name="/api/health/")
