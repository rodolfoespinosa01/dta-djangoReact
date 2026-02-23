from django.db import models


class FoodLibraryItem(models.Model):
    class Category(models.TextChoices):
        PROTEIN = "Protein", "Protein"
        CARBS = "Carbs", "Carbs"
        FATS = "Fats", "Fats"
        NONE = "-", "-"

    source_food_id = models.IntegerField(unique=True, db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    name = models.CharField(max_length=120, db_index=True)
    measurement_unit = models.CharField(max_length=16, blank=True, default="oz")
    protein = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    carbs = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    fats = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    is_placeholder = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("source_food_id",)
        verbose_name = "Food Library Item"
        verbose_name_plural = "Food Library Items"

    def __str__(self):
        return f"{self.name} [{self.category}]"


class MealComboTemplate(models.Model):
    combo_id = models.IntegerField(unique=True, db_index=True)

    protein_slot_1 = models.CharField(max_length=120, default="-")
    protein_slot_2 = models.CharField(max_length=120, default="-")
    carb_slot_1 = models.CharField(max_length=120, default="-")
    carb_slot_2 = models.CharField(max_length=120, default="-")
    fat_slot_1 = models.CharField(max_length=120, default="-")
    fat_slot_2 = models.CharField(max_length=120, default="-")

    protein_split_1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    protein_split_2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    carb_split_1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    carb_split_2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fat_split_1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fat_split_2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("combo_id",)
        verbose_name = "Meal Combo Template"
        verbose_name_plural = "Meal Combo Templates"
        indexes = [
            models.Index(
                fields=[
                    "protein_slot_1",
                    "protein_slot_2",
                    "carb_slot_1",
                    "carb_slot_2",
                    "fat_slot_1",
                    "fat_slot_2",
                ],
                name="core_combo_slot_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"Combo #{self.combo_id}"


class ComboMacroErrorLookup(models.Model):
    error_code = models.IntegerField(unique=True, db_index=True)
    protein_error = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    carbs_error = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fats_error = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("error_code",)
        verbose_name = "Combo Macro Error Lookup"
        verbose_name_plural = "Combo Macro Error Lookups"

    def __str__(self):
        return f"Error #{self.error_code}"
