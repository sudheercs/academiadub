import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academiadub.settings.local")
django.setup()

from apps.catalogue.models import Subject, Topic, TopicVersion
from django.contrib.auth import get_user_model

User = get_user_model()

def seed():
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser(email="admin2@academiadub.in", password="admin")

    # Clear existing
    Subject.objects.all().delete()

    print("Creating Python subject...")
    python = Subject.objects.create(
        slug="python",
        name="Python Programming",
        description="Learn Python from scratch. Ideal for beginners and data science enthusiasts.",
        icon="🐍",
        status="published"
    )

    print("Creating React subject...")
    react = Subject.objects.create(
        slug="react",
        name="Advanced React",
        description="Master React hooks, server components, and Next.js.",
        icon="⚛️",
        status="published"
    )
    
    print("Creating Machine Learning subject (Draft)...")
    ml = Subject.objects.create(
        slug="machine-learning",
        name="Machine Learning Fundamentals",
        description="Coming soon: Neural networks and deep learning.",
        icon="🤖",
        status="draft"
    )

    print("Creating Topics for Python...")
    intro = Topic.objects.create(
        subject=python,
        slug="variables",
        title="Variables & Data Types",
        difficulty="beginner",
        access_level="free",
        status="published",
        order=1
    )
    
    TopicVersion.objects.create(
        topic=intro,
        version_no=1,
        author=admin,
        state="published",
        blocks=[
            {"type": "markdown", "content": "Welcome to Python! A **variable** is like a box where you store data."},
            {"type": "code", "language": "python", "content": "x = 5\nname = 'Alice'\nprint(name)"}
        ]
    )
    intro.current_version_id = 1
    intro.save()
    
    lists = Topic.objects.create(
        subject=python,
        slug="lists",
        title="Lists and Loops",
        difficulty="beginner",
        access_level="login",
        status="published",
        order=2
    )

    print("Database seeded with dummy Catalogue data.")

if __name__ == "__main__":
    seed()
