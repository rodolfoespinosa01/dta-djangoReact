from django.db import migrations, models
import django.db.models.deletion


def _canonical_standard_name(value):
    normalized = str(value or "").strip()
    if not normalized:
        return "-"
    if normalized == "-":
        return "-"
    if normalized.upper().endswith(" STANDARD"):
        return normalized
    return f"{normalized} STANDARD"


def _forward_fill_food_canonical_fields(apps, schema_editor):
    FoodLibraryItem = apps.get_model("core", "FoodLibraryItem")
    for row in FoodLibraryItem.objects.all().iterator(chunk_size=1000):
        category = _canonical_standard_name(row.category)
        display_name = (row.name or "").strip() or category
        row.category = category
        row.name = category
        row.display_name = display_name
        row.canonical_name = category
        row.canonical_category = category
        row.source_type = "standard"
        row.approval_status = "approved"
        row.is_standard = True
        row.is_active = True
        row.save(
            update_fields=[
                "category",
                "name",
                "display_name",
                "canonical_name",
                "canonical_category",
                "source_type",
                "approval_status",
                "is_standard",
                "is_active",
            ]
        )

    MealComboTemplate = apps.get_model("core", "MealComboTemplate")
    slot_fields = [
        "protein_slot_1",
        "protein_slot_2",
        "carb_slot_1",
        "carb_slot_2",
        "fat_slot_1",
        "fat_slot_2",
    ]
    for combo in MealComboTemplate.objects.all().iterator(chunk_size=1000):
        changed = False
        for field in slot_fields:
            current = getattr(combo, field)
            normalized = _canonical_standard_name(current)
            if current != normalized:
                setattr(combo, field, normalized)
                changed = True
        if changed:
            combo.save(update_fields=slot_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_foodlibraryitem_macro_and_category_bridge"),
    ]

    operations = [
        migrations.AddField(
            model_name="foodlibraryitem",
            name="approval_status",
            field=models.CharField(
                choices=[("approved", "Approved"), ("pending", "Pending"), ("rejected", "Rejected")],
                db_index=True,
                default="approved",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="brand_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="canonical_category",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="canonical_name",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="created_by_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submitted_food_library_items",
                to="core.customuser",
            ),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="display_name",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="is_standard",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="parent_standard_food",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="specific_food_variants",
                to="core.foodlibraryitem",
            ),
        ),
        migrations.AddField(
            model_name="foodlibraryitem",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("branded", "Branded"),
                    ("user_submitted", "User Submitted"),
                    ("admin_approved", "Admin Approved"),
                ],
                db_index=True,
                default="standard",
                max_length=32,
            ),
        ),
        migrations.RunPython(_forward_fill_food_canonical_fields, migrations.RunPython.noop),
    ]
