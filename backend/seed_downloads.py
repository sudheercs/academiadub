import os
import django
from django.core.files.base import ContentFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academiadub.settings.local")
django.setup()

from apps.catalogue.models import Topic
from apps.downloads.models import Download
from django.contrib.auth import get_user_model

User = get_user_model()

def seed():
    admin = User.objects.filter(is_superuser=True).first()
    
    # Clear existing
    Download.objects.all().delete()

    topic = Topic.objects.filter(slug="variables").first()
    if not topic:
        print("Topic 'variables' not found. Seed catalogue first.")
        return

    print(f"Creating dummy download for topic '{topic.title}'...")
    
    download = Download.objects.create(
        topic=topic,
        title="Python Cheatsheet",
        description="A handy PDF guide for Python variables and data types.",
        access_level="free",
        uploaded_by=admin
    )
    
    # Create a dummy text file to act as the attachment
    dummy_content = b"This is a dummy PDF file content... (cheatsheet inside)"
    download.file.save("python_cheatsheet.pdf", ContentFile(dummy_content))
    download.file_size_bytes = len(dummy_content)
    download.mime_type = "application/pdf"
    download.save()
    
    print("Database seeded with dummy Download data.")

if __name__ == "__main__":
    seed()
