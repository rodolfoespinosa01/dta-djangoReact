from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0012_clientprogressphoto"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientWeightEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("measured_at", models.DateTimeField(db_index=True)),
                ("weight_value", models.DecimalField(decimal_places=2, max_digits=6)),
                ("unit", models.CharField(choices=[("lbs", "LBS"), ("kg", "KG")], default="lbs", max_length=8)),
                ("notes", models.CharField(blank=True, default="", max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weight_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Client Weight Entry",
                "verbose_name_plural": "Client Weight Entries",
                "ordering": ("-measured_at", "-created_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="clientweightentry",
            constraint=models.CheckConstraint(
                condition=models.Q(("weight_value__gt", 0)),
                name="client_weight_entry_value_positive",
            ),
        ),
    ]
