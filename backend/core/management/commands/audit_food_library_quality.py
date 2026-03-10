from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import FoodLibraryItem
from users.client_area.services.meal_plan_generation.solver.adapters import _unit_to_gram_factor


class Command(BaseCommand):
    help = "Audit FoodLibraryItem data quality for solver normalization safety."

    def handle(self, *args, **options):
        rows = list(FoodLibraryItem.objects.all().order_by("source_food_id"))
        unit_values = sorted({str(row.measurement_unit or "").strip().lower() for row in rows})

        blank_units = [row for row in rows if str(row.measurement_unit or "").strip() == ""]
        zero_or_negative_macros = [
            row
            for row in rows
            if float(row.protein or 0) <= 0 or float(row.carbs or 0) <= 0 or float(row.fats or 0) <= 0
        ]
        cannot_normalize = []
        un_without_mapping = []

        for row in rows:
            factor, warning = _unit_to_gram_factor(unit=row.measurement_unit, source_food_id=row.source_food_id)
            if not factor:
                cannot_normalize.append((row, warning))
            unit = str(row.measurement_unit or "").strip().lower()
            if unit in {"un", "unit", "units"} and not factor:
                un_without_mapping.append((row, warning))

        self.stdout.write("Food Library Quality Audit")
        self.stdout.write("=" * 28)
        self.stdout.write(f"total_rows: {len(rows)}")
        self.stdout.write(f"distinct_measurement_units: {unit_values}")
        self.stdout.write(f"blank_or_null_units: {len(blank_units)}")
        self.stdout.write(f"zero_or_negative_macro_rows(any macro <= 0): {len(zero_or_negative_macros)}")
        self.stdout.write(f"cannot_normalize_safely: {len(cannot_normalize)}")
        self.stdout.write(f"'un' rows without grams mapping: {len(un_without_mapping)}")

        if blank_units:
            self.stdout.write("\nRows with blank/null units:")
            for row in blank_units[:50]:
                self.stdout.write(f"- {row.source_food_id} | {row.name}")

        if cannot_normalize:
            self.stdout.write("\nRows that cannot normalize safely:")
            for row, warning in cannot_normalize[:100]:
                self.stdout.write(
                    f"- {row.source_food_id} | {row.name} | unit={row.measurement_unit!r} | warning={warning}"
                )

        if un_without_mapping:
            self.stdout.write("\nRows using `un` without grams mapping:")
            for row, warning in un_without_mapping[:100]:
                self.stdout.write(f"- {row.source_food_id} | {row.name} | warning={warning}")
