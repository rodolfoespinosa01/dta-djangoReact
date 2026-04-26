from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("client_area", "0016_delete_discountcode"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientFoodOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("canonical_category", models.CharField(db_index=True, max_length=120)),
                (
                    "source_type",
                    models.CharField(
                        choices=[("usda", "USDA FoodData Central")],
                        db_index=True,
                        default="usda",
                        max_length=32,
                    ),
                ),
                ("external_provider", models.CharField(db_index=True, default="usda", max_length=40)),
                ("external_food_id", models.CharField(db_index=True, max_length=120)),
                ("display_name", models.CharField(max_length=220)),
                ("brand_name", models.CharField(blank=True, default="", max_length=160)),
                ("serving_size", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("serving_unit", models.CharField(blank=True, default="", max_length=40)),
                ("serving_weight_grams", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("protein", models.DecimalField(decimal_places=5, default=0, max_digits=12)),
                ("carbs", models.DecimalField(decimal_places=5, default=0, max_digits=12)),
                ("fats", models.DecimalField(decimal_places=5, default=0, max_digits=12)),
                ("calories", models.DecimalField(decimal_places=5, default=0, max_digits=12)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="food_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Client Food Override",
                "verbose_name_plural": "Client Food Overrides",
                "ordering": ("user_id", "canonical_category", "-updated_at"),
            },
        ),
        migrations.AddIndex(
            model_name="clientfoodoverride",
            index=models.Index(fields=["user", "canonical_category", "active"], name="client_food_ovr_lkp_idx"),
        ),
        migrations.AddConstraint(
            model_name="clientfoodoverride",
            constraint=models.UniqueConstraint(
                condition=Q(active=True),
                fields=("user", "canonical_category"),
                name="client_unique_active_food_override_per_category",
            ),
        ),
    ]
