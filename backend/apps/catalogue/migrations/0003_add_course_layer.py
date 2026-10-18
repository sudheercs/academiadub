import django.db.models.deletion
from django.db import migrations, models


def migrate_existing_topics_to_default_courses(apps, schema_editor):
    Subject = apps.get_model("catalogue", "Subject")
    Course = apps.get_model("catalogue", "Course")
    Topic = apps.get_model("catalogue", "Topic")

    for subject in Subject.objects.all():
        course, _ = Course.objects.get_or_create(
            subject=subject,
            slug="general",
            defaults={
                "title": f"{subject.name} - General Course",
                "status": "published",
                "description": f"Core topics for {subject.name}",
            },
        )
        Topic.objects.filter(subject=subject, course__isnull=True).update(course=course)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogue", "0002_alter_subject_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(max_length=100)),
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                (
                    "difficulty",
                    models.CharField(
                        choices=[
                            ("beginner", "Beginner"),
                            ("intermediate", "Intermediate"),
                            ("advanced", "Advanced"),
                        ],
                        default="beginner",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses",
                        to="catalogue.subject",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "created_at"],
                "unique_together": {("subject", "slug")},
            },
        ),
        migrations.AddField(
            model_name="topic",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topics",
                to="catalogue.course",
            ),
        ),
        migrations.RunPython(
            migrate_existing_topics_to_default_courses,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="topic",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topics",
                to="catalogue.course",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="topic",
            unique_together={("course", "slug")},
        ),
        migrations.RemoveField(
            model_name="topic",
            name="subject",
        ),
    ]
