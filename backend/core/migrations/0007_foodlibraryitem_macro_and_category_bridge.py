from django.db import migrations, models


MACRO_MAP = {
    "protein": "Protein",
    "carbs": "Carbs",
    "fats": "Fats",
    "-": "-",
    "": "-",
}


def _forward_fill_macro(apps, schema_editor):
    FoodLibraryItem = apps.get_model("core", "FoodLibraryItem")
    for row in FoodLibraryItem.objects.all().only("id", "category", "macro").iterator(chunk_size=1000):
        raw_category = (row.category or "").strip().lower()
        row.macro = MACRO_MAP.get(raw_category, "-")
        row.save(update_fields=["macro"])


def _reverse_clear_macro(apps, schema_editor):
    FoodLibraryItem = apps.get_model("core", "FoodLibraryItem")
    FoodLibraryItem.objects.all().update(macro="-")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_carbcyclingdefault_ketodefault_standarddefault_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="foodlibraryitem",
            name="macro",
            field=models.CharField(
                choices=[("Protein", "Protein"), ("Carbs", "Carbs"), ("Fats", "Fats"), ("-", "-")],
                db_index=True,
                default="-",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="foodlibraryitem",
            name="category",
            field=models.CharField(db_index=True, default="-", max_length=120),
        ),
        migrations.RunPython(_forward_fill_macro, _reverse_clear_macro),
    ]
