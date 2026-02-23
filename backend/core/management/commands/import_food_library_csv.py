import csv
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import ComboMacroErrorLookup, FoodLibraryItem, MealComboTemplate


def _str_or_default(value, default=""):
    return (value or "").strip() if value is not None else default


def _decimal_or_none(value):
    text = _str_or_default(value)
    if text == "":
        return None
    return Decimal(text)


def _decimal_or_zero(value):
    return _decimal_or_none(value) or Decimal("0")


def _read_csv_rows(path):
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
            return reader.fieldnames or [], rows
    except OSError as exc:
        raise CommandError(f"Unable to read CSV file {path}: {exc}") from exc


class Command(BaseCommand):
    help = (
        "Import global food library and combo templates from CSV exports "
        "(formerly wp_food_macros/wp_combos/wp_error_453030)."
    )

    def add_arguments(self, parser):
        parser.add_argument("food_macros_csv", type=str, help="Path to food_macros.csv (old wp_food_macros.csv)")
        parser.add_argument("combos_csv", type=str, help="Path to combos.csv (old wp_combos.csv)")
        parser.add_argument(
            "--combo-errors-csv",
            dest="combo_errors_csv",
            type=str,
            default=None,
            help="Optional path to combo_error_453030.csv (old wp_error_453030.csv)",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing global food library/combo rows before import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        food_csv = options["food_macros_csv"]
        combos_csv = options["combos_csv"]
        combo_errors_csv = options.get("combo_errors_csv")
        truncate = bool(options["truncate"])

        food_headers, food_rows = _read_csv_rows(food_csv)
        combo_headers, combo_rows = _read_csv_rows(combos_csv)
        error_rows = []
        error_headers = []
        if combo_errors_csv:
            error_headers, error_rows = _read_csv_rows(combo_errors_csv)

        required_food = {"food_id", "macro", "name", "measurement", "protein", "carbs", "fats"}
        required_combos = {
            "c1_id",
            "c1_protein_1",
            "c1_protein_2",
            "c1_carbs_1",
            "c1_carbs_2",
            "c1_fats_1",
            "c1_fats_2",
            "p1",
            "p2",
            "c1",
            "c2",
            "f1",
            "f2",
        }

        if not required_food.issubset(set(food_headers)):
            raise CommandError(f"food_macros CSV missing columns: {sorted(required_food - set(food_headers))}")
        if not required_combos.issubset(set(combo_headers)):
            raise CommandError(f"combos CSV missing columns: {sorted(required_combos - set(combo_headers))}")
        if combo_errors_csv:
            required_errors = {"error_id", "e_protein", "e_carbs", "e_fats"}
            if not required_errors.issubset(set(error_headers)):
                raise CommandError(f"combo_error CSV missing columns: {sorted(required_errors - set(error_headers))}")

        if truncate:
            self.stdout.write("Deleting existing global food library data...")
            MealComboTemplate.objects.all().delete()
            FoodLibraryItem.objects.all().delete()
            ComboMacroErrorLookup.objects.all().delete()

        food_objects = []
        for row in food_rows:
            category = _str_or_default(row.get("macro"), "-")
            name = _str_or_default(row.get("name"), "-")
            food_objects.append(
                FoodLibraryItem(
                    source_food_id=int(_str_or_default(row.get("food_id"), "0")),
                    category=category,
                    name=name,
                    measurement_unit=_str_or_default(row.get("measurement"), "oz"),
                    protein=_decimal_or_zero(row.get("protein")),
                    carbs=_decimal_or_zero(row.get("carbs")),
                    fats=_decimal_or_zero(row.get("fats")),
                    is_placeholder=(category == "-" or name == "-"),
                )
            )

        FoodLibraryItem.objects.bulk_create(
            food_objects,
            batch_size=1000,
            update_conflicts=True,
            unique_fields=["source_food_id"],
            update_fields=[
                "category",
                "name",
                "measurement_unit",
                "protein",
                "carbs",
                "fats",
                "is_placeholder",
            ],
        )

        combo_objects = []
        for row in combo_rows:
            combo_id = _str_or_default(row.get("c1_id"))
            if not combo_id:
                continue
            combo_objects.append(
                MealComboTemplate(
                    combo_id=int(combo_id),
                    protein_slot_1=_str_or_default(row.get("c1_protein_1"), "-"),
                    protein_slot_2=_str_or_default(row.get("c1_protein_2"), "-"),
                    carb_slot_1=_str_or_default(row.get("c1_carbs_1"), "-"),
                    carb_slot_2=_str_or_default(row.get("c1_carbs_2"), "-"),
                    fat_slot_1=_str_or_default(row.get("c1_fats_1"), "-"),
                    fat_slot_2=_str_or_default(row.get("c1_fats_2"), "-"),
                    protein_split_1=_decimal_or_none(row.get("p1")),
                    protein_split_2=_decimal_or_none(row.get("p2")),
                    carb_split_1=_decimal_or_none(row.get("c1")),
                    carb_split_2=_decimal_or_none(row.get("c2")),
                    fat_split_1=_decimal_or_none(row.get("f1")),
                    fat_split_2=_decimal_or_none(row.get("f2")),
                )
            )

        MealComboTemplate.objects.bulk_create(
            combo_objects,
            batch_size=1000,
            update_conflicts=True,
            unique_fields=["combo_id"],
            update_fields=[
                "protein_slot_1",
                "protein_slot_2",
                "carb_slot_1",
                "carb_slot_2",
                "fat_slot_1",
                "fat_slot_2",
                "protein_split_1",
                "protein_split_2",
                "carb_split_1",
                "carb_split_2",
                "fat_split_1",
                "fat_split_2",
            ],
        )

        error_objects = []
        for row in error_rows:
            error_code = _str_or_default(row.get("error_id"))
            if not error_code:
                continue
            error_objects.append(
                ComboMacroErrorLookup(
                    error_code=int(error_code),
                    protein_error=_decimal_or_zero(row.get("e_protein")),
                    carbs_error=_decimal_or_zero(row.get("e_carbs")),
                    fats_error=_decimal_or_zero(row.get("e_fats")),
                )
            )

        if error_objects:
            ComboMacroErrorLookup.objects.bulk_create(
                error_objects,
                batch_size=1000,
                update_conflicts=True,
                unique_fields=["error_code"],
                update_fields=["protein_error", "carbs_error", "fats_error"],
            )

        self.stdout.write(self.style.SUCCESS(f"Imported {len(food_objects)} food library rows."))
        self.stdout.write(self.style.SUCCESS(f"Imported {len(combo_objects)} meal combo template rows."))
        if combo_errors_csv:
            self.stdout.write(self.style.SUCCESS(f"Imported {len(error_objects)} combo error lookup rows."))
