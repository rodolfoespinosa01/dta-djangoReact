from django.db import migrations, models


def seed_obvious_measurement_basis(apps, schema_editor):
    FoodLibraryItem = apps.get_model("core", "FoodLibraryItem")
    dry_terms = ("rice", "oats", "pasta", "cereal")
    cooked_terms = ("sweet potato", "white potato", "yam")

    for row in FoodLibraryItem.objects.all().iterator():
        text = " ".join(
            [
                str(row.name or ""),
                str(row.display_name or ""),
                str(row.category or ""),
                str(row.canonical_category or ""),
            ]
        ).lower()
        state = "unknown"
        label = "Measurement basis not specified"
        if any(term in text for term in dry_terms):
            state = "dry_uncooked"
            label = "Measure dry/uncooked"
        elif any(term in text for term in cooked_terms):
            state = "unknown"
            label = "Measurement basis not specified"
        row.preparation_state = state
        row.measurement_basis_label = label
        row.save(update_fields=["preparation_state", "measurement_basis_label"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_foodlibraryitem_canonical_standard_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="foodlibraryitem",
            name="preparation_state",
            field=models.CharField(
                choices=[
                    ("raw", "Raw / uncooked"),
                    ("cooked", "Cooked"),
                    ("boiled", "Boiled"),
                    ("grilled", "Grilled"),
                    ("baked", "Baked"),
                    ("drained", "Drained / cooked"),
                    ("dry_uncooked", "Dry / uncooked"),
                    ("as_packaged", "As packaged"),
                    ("unknown", "Unknown"),
                ],
                db_index=True,
                default="unknown",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="measurement_basis_label",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="raw_to_cooked_yield_factor",
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="cooked_to_raw_yield_factor",
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True),
        ),
        migrations.RunPython(seed_obvious_measurement_basis, migrations.RunPython.noop),
    ]
