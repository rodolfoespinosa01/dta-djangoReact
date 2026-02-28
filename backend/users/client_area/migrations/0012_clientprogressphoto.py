from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0011_alter_clientpendingsignup_offer_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientProgressPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="client_progress_photos/%Y/%m/")),
                ("captured_for_date", models.DateField(db_index=True)),
                ("same_position", models.BooleanField(default=True)),
                ("same_lighting", models.BooleanField(default=True)),
                ("same_time_of_day", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_photos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Client Progress Photo",
                "verbose_name_plural": "Client Progress Photos",
                "ordering": ("-captured_for_date", "-created_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="clientprogressphoto",
            constraint=models.UniqueConstraint(fields=("user", "captured_for_date"), name="client_unique_progress_photo_per_day"),
        ),
        migrations.AddConstraint(
            model_name="clientprogressphoto",
            constraint=models.CheckConstraint(
                condition=models.Q(("notes__isnull", False)),
                name="client_progress_photo_notes_not_null",
            ),
        ),
    ]
