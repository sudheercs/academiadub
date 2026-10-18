from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classes", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="classroom",
            name="join_code",
            field=models.CharField(
                blank=True, db_index=True, max_length=12, unique=True
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="student_secret",
            field=models.CharField(blank=True, max_length=8),
        ),
    ]
