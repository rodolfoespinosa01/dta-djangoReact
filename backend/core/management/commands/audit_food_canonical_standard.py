from django.core.management.base import BaseCommand, CommandError

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.food_canonical import canonical_standard_name


class Command(BaseCommand):
    help = "Audit canonical STANDARD food categories and meal combo template slot coverage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help="Exit non-zero when audit issues are found.",
        )

    def handle(self, *args, **options):
        slot_fields = [
            "protein_slot_1",
            "protein_slot_2",
            "carb_slot_1",
            "carb_slot_2",
            "fat_slot_1",
            "fat_slot_2",
        ]
        categories = {
            value
            for value in FoodLibraryItem.objects.values_list("category", flat=True).distinct()
            if value and value != "-"
        }
        canonical_values = {
            value
            for value in FoodLibraryItem.objects.values_list("canonical_category", flat=True).distinct()
            if value and value != "-"
        }
        supported = categories | canonical_values

        slot_values = set()
        for field in slot_fields:
            slot_values.update(
                value
                for value in MealComboTemplate.objects.values_list(field, flat=True).distinct()
                if value and value != "-"
            )

        missing_slots = sorted(slot_values - supported)
        nonstandard_food_categories = sorted(
            value for value in categories if canonical_standard_name(value) != value
        )
        nonstandard_combo_slots = sorted(
            value for value in slot_values if canonical_standard_name(value) != value
        )

        duplicate_standard_categories = []
        for category in sorted(supported):
            rows = FoodLibraryItem.objects.filter(
                category=category,
                is_active=True,
                approval_status=FoodLibraryItem.ApprovalStatus.APPROVED,
                is_standard=True,
            )
            count = rows.count()
            macro_count = rows.values("protein", "carbs", "fats", "measurement_unit").distinct().count()
            if count > 1 and macro_count > 1:
                duplicate_standard_categories.append(
                    {
                        "category": category,
                        "standard_row_count": count,
                        "distinct_macro_profiles": macro_count,
                    }
                )

        issue_count = (
            len(missing_slots)
            + len(nonstandard_food_categories)
            + len(nonstandard_combo_slots)
            + len(duplicate_standard_categories)
        )

        self.stdout.write(f"Food categories: {len(categories)}")
        self.stdout.write(f"Combo slot values: {len(slot_values)}")
        self.stdout.write(f"Missing template slots: {len(missing_slots)}")
        for value in missing_slots[:50]:
            self.stdout.write(f"  missing slot category: {value}")

        self.stdout.write(f"Food categories not ending in STANDARD: {len(nonstandard_food_categories)}")
        for value in nonstandard_food_categories[:50]:
            self.stdout.write(f"  non-standard food category: {value}")

        self.stdout.write(f"Combo slots not ending in STANDARD: {len(nonstandard_combo_slots)}")
        for value in nonstandard_combo_slots[:50]:
            self.stdout.write(f"  non-standard combo slot: {value}")

        self.stdout.write(f"Duplicate/conflicting STANDARD categories: {len(duplicate_standard_categories)}")
        for row in duplicate_standard_categories[:50]:
            self.stdout.write(
                f"  {row['category']}: {row['standard_row_count']} rows, "
                f"{row['distinct_macro_profiles']} macro profiles"
            )

        if issue_count:
            message = f"Food canonical audit completed with {issue_count} issue(s)."
            if options["fail_on_issues"]:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(self.style.SUCCESS("Food canonical audit passed."))
