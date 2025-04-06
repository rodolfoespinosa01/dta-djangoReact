# Generated by Django 5.2 on 2025-04-06 01:51

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AdminPlan",
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
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("adminTrial", "Free Admin Trial"),
                            ("adminMonthly", "Monthly Admin Plan"),
                            ("adminAnnual", "Annual Admin Plan"),
                        ],
                        max_length=30,
                        unique=True,
                    ),
                ),
                ("description", models.TextField()),
                ("stripe_price_id", models.CharField(max_length=100)),
                ("price_cents", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="PendingAdminSignup",
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
                ("email", models.EmailField(max_length=254)),
                ("session_id", models.CharField(max_length=255, unique=True)),
                (
                    "token",
                    models.CharField(default=uuid.uuid4, max_length=64, unique=True),
                ),
                ("plan", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_used", models.BooleanField(default=False)),
            ],
        ),
    ]
