import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academiadub.settings.local")
django.setup()

from django.contrib.auth import get_user_model

from apps.catalogue.models import Course, Subject, Topic, TopicVersion

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

    print("  Creating Courses for Python...")
    py_fund = Course.objects.create(
        subject=python,
        slug="python-fundamentals",
        title="Python Fundamentals",
        description="Master variables, collections, loops, and control flow in Python.",
        icon="🔰",
        difficulty="beginner",
        status="published",
        order=1
    )
    py_adv = Course.objects.create(
        subject=python,
        slug="python-oop-advanced",
        title="Object-Oriented & Advanced Python",
        description="Explore classes, inheritance, decorators, and advanced Python idioms.",
        icon="⚡",
        difficulty="intermediate",
        status="published",
        order=2
    )

    print("Creating React subject...")
    react = Subject.objects.create(
        slug="react",
        name="Advanced React",
        description="Master React hooks, server components, and Next.js.",
        icon="⚛️",
        status="published"
    )
    
    print("  Creating Courses for React...")
    react_core = Course.objects.create(
        subject=react,
        slug="react-core",
        title="React Core & State Management",
        description="Deep dive into modern hooks, component lifecycle, and state flow.",
        icon="⚛️",
        difficulty="intermediate",
        status="published",
        order=1
    )
    react_next = Course.objects.create(
        subject=react,
        slug="nextjs-fullstack",
        title="Next.js & Server Components",
        description="Build fast full-stack applications with the Next.js App Router.",
        icon="🚀",
        difficulty="advanced",
        status="published",
        order=2
    )

    print("Creating Web Design subject...")
    design = Subject.objects.create(
        slug="design",
        name="UI/UX Design",
        description="Design beautiful, accessible, and engaging user interfaces.",
        icon="🎨",
        status="published"
    )

    print("  Creating Courses for Web Design...")
    design_systems = Course.objects.create(
        subject=design,
        slug="design-systems",
        title="Design Systems & Figma",
        description="Build scalable component libraries and intuitive Figma wireframes.",
        icon="🎨",
        difficulty="beginner",
        status="published",
        order=1
    )

    print("Creating Machine Learning subject (Draft)...")
    ml = Subject.objects.create(
        slug="machine-learning",
        name="Machine Learning Fundamentals",
        description="Coming soon: Neural networks and deep learning.",
        icon="🤖",
        status="draft"
    )
    Course.objects.create(
        subject=ml,
        slug="neural-networks-intro",
        title="Intro to Neural Networks",
        description="Perceptrons, backpropagation, and foundational deep learning.",
        icon="🧠",
        difficulty="advanced",
        status="draft",
        order=1
    )

    print("Creating Topics for Python Fundamentals...")
    intro = Topic.objects.create(
        course=py_fund, slug="variables", title="Variables & Data Types",
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
        course=py_fund, slug="lists", title="Lists and Loops",
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

    print("Creating Topics for Advanced Python...")
    funcs = Topic.objects.create(
        course=py_adv, slug="functions", title="Functions & Scope",
        difficulty="intermediate", access_level="free", status="published", order=1
    )
    TopicVersion.objects.create(
        topic=funcs, version_no=1, author=admin, state="published",
        blocks=[
            {"type": "markdown", "content": "Functions are reusable blocks of code that take inputs and return outputs."},
            {"type": "code", "language": "python", "content": "def greet(name: str) -> str:\n    return f'Hello, {name}!'\n\nprint(greet('Developer'))"}
        ]
    )
    funcs.current_version_id = 1
    funcs.save()

    print("Creating Topics for React Core...")
    hooks = Topic.objects.create(
        course=react_core, slug="hooks", title="React Hooks Deep Dive",
        difficulty="intermediate", access_level="paid", status="published", order=1
    )
    TopicVersion.objects.create(
        topic=hooks, version_no=1, author=admin, state="published",
        blocks=[
            {"type": "markdown", "content": "Hooks are a feature in React that let you use state and lifecycle methods in function components."},
            {"type": "code", "language": "javascript", "content": "import React, { useState, useEffect } from 'react';\n\nfunction Counter() {\n  const [count, setCount] = useState(0);\n  return <button onClick={() => setCount(c => c + 1)}>Count: {count}</button>;\n}"},
            {"type": "callout", "content": "Rules of Hooks: Only call Hooks at the top level. Only call Hooks from React function components."}
        ]
    )
    hooks.current_version_id = 1
    hooks.save()

    print("Database seeded with rich Catalogue data (Subjects -> Courses -> Topics).")

if __name__ == "__main__":
    seed()
