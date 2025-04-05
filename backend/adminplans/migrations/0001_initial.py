# Generated by Django 5.2 on 2025-04-05 04:34

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
                ("price_display", models.CharField(max_length=50)),
                ("stripe_price_id", models.CharField(max_length=100)),
            ],
        ),
    ]
