import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academiadub.settings.local")
django.setup()

import random
import string
from datetime import UTC

from apps.catalogue.models import Topic
from apps.classes.models import Assignment, Classroom, Enrollment
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_code(length=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def seed():
    Classroom.objects.all().delete()

    admin = User.objects.filter(is_superuser=True).first()

    # Create a student user
    student, _ = User.objects.get_or_create(
        email="student@academiadub.in",
        defaults={"is_staff": False, "is_superuser": False, "status": "active"},
    )
    student.set_password("student123")
    student.save()
    print(f"Student: {student.email} / student123")

    # Create two classrooms
    topics = list(Topic.objects.filter(status="published"))
    if not topics:
        print("No published topics found. Run seed_catalogue.py first.")
        return

    print("Creating Python Bootcamp class...")
    bootcamp = Classroom.objects.create(
        name="Python Bootcamp — Oct 2026",
        description="A 4-week intensive Python course for complete beginners.",
        instructor=admin,
        join_code=generate_code(),
        is_active=True,
    )

    print("Creating React Masterclass...")
    masterclass = Classroom.objects.create(
        name="React Masterclass — Oct 2026",
        description="Deep-dive into React hooks, context, and Next.js for intermediate developers.",
        instructor=admin,
        join_code=generate_code(),
        is_active=True,
    )

    # Enroll student in bootcamp
    Enrollment.objects.create(classroom=bootcamp, student=student, status="active")
    print(f"  Enrolled {student.email} in {bootcamp.name}")

    # Assign all published topics
    from datetime import datetime, timedelta

    now = datetime.now(UTC)

    for i, topic in enumerate(topics[:3]):
        Assignment.objects.create(
            classroom=bootcamp,
            topic=topic,
            due_at=now + timedelta(days=(i + 1) * 7),
        )
        print(f"  Assigned '{topic.title}' to {bootcamp.name}")

    print(f"\nBootcamp join code: {bootcamp.join_code}")
    print(f"Masterclass join code: {masterclass.join_code}")
    print("\nSeeding complete.")


if __name__ == "__main__":
    seed()
