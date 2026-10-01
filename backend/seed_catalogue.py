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
    
    print("Creating Web Design subject...")
    design = Subject.objects.create(
        slug="design",
        name="UI/UX Design",
        description="Design beautiful, accessible, and engaging user interfaces.",
        icon="🎨",
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
        subject=python, slug="variables", title="Variables & Data Types",
        difficulty="beginner", access_level="free", status="published", order=1
    )
    TopicVersion.objects.create(
        topic=intro, version_no=1, author=admin, state="published",
        blocks=[
            {"type": "markdown", "content": "Welcome to Python! A **variable** is a named container for data. Python is dynamically typed — you do not declare types."},
            {"type": "callout", "content": "Python uses indentation instead of braces. Keep your code clean!"},
            {"type": "code", "language": "python", "content": "name = 'Alice'\nage = 30\nheight = 5.6\nprint(f'{name} is {age} years old')"},
            {"type": "markdown", "content": "Python has **four** core data types:\n- `str` — text\n- `int` — whole numbers\n- `float` — decimals\n- `bool` — True / False"},
            {"type": "code_lab", "language": "python", "content": "x = 10       # int\nprice = 4.99  # float\nlabel = 'hi' # str\nactive = True # bool\nprint(type(x))  # <class int>\n\n# Try changing x to a float and run it!"},
            {"type": "youtube_video", "url": "https://www.youtube.com/watch?v=kqtD5dpn9C8", "caption": "Python for Beginners - Full Course"}
        ]
    )
    intro.current_version_id = 1
    intro.save()
    
    lists = Topic.objects.create(
        subject=python, slug="lists", title="Lists and Loops",
        difficulty="beginner", access_level="login", status="published", order=2
    )
    TopicVersion.objects.create(
        topic=lists, version_no=1, author=admin, state="published",
        blocks=[
            {"type": "markdown", "content": "A **list** is a collection of items in a particular order."},
            {"type": "code", "language": "python", "content": "fruits = ['apple', 'banana', 'cherry']\nfor fruit in fruits:\n    print(fruit)"}
        ]
    )
    lists.current_version_id = 1
    lists.save()

    print("Creating Topics for React...")
    hooks = Topic.objects.create(
        subject=react, slug="hooks", title="React Hooks Deep Dive",
        difficulty="intermediate", access_level="paid", status="published", order=1
    )
    TopicVersion.objects.create(
        topic=hooks, version_no=1, author=admin, state="published",
        blocks=[
            {"type": "markdown", "content": "Hooks are a new addition in React 16.8. They let you use state and other React features without writing a class."},
            {"type": "code", "language": "javascript", "content": "import React, { useState, useEffect } from 'react';\n\nfunction Example() {\n  const [count, setCount] = useState(0);\n\n  useEffect(() => {\n    document.title = `You clicked ${count} times`;\n  });\n\n  return (\n    <div>\n      <p>You clicked {count} times</p>\n      <button onClick={() => setCount(count + 1)}>\n        Click me\n      </button>\n    </div>\n  );\n}"},
            {"type": "callout", "content": "Rules of Hooks: Only call Hooks at the top level. Only call Hooks from React function components."}
        ]
    )
    hooks.current_version_id = 1
    hooks.save()

    print("Database seeded with rich Catalogue data.")

if __name__ == "__main__":
    seed()
