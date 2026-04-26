import csv
from decimal import Decimal
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import ComboMacroErrorLookup, FoodLibraryItem, MealComboTemplate
from core.services.food_canonical import canonical_standard_name


def _str_or_default(value, default=""):
    return (value or "").strip() if value is not None else default


def _clean_header(value):
    text = (value or "").strip().lower()
    # Some spreadsheet exports include embedded newlines/spaces in header names.
    return re.sub(r"\s+", "", text)


def _normalize_row_keys(row):
    normalized = {}
    for key, value in (row or {}).items():
        clean_key = _clean_header(key)
        if not clean_key:
            continue
        normalized[clean_key] = value
    return normalized


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
            reader = csv.reader(fh)
            raw_rows = list(reader)
            if not raw_rows:
                return set(), []

            header = [_clean_header(col) for col in (raw_rows[0] or [])]
            data_start_index = 1

            # Some exported combo CSVs split the header across two physical lines
            # (for example: ...,p2, then next line starts with c1,c2,f1,f2).
            if len(raw_rows) > 1:
                second_row = [_clean_header(col) for col in (raw_rows[1] or [])]
                if second_row:
                    looks_like_header_tail = all(
                        value and not any(ch.isdigit() for ch in value)
                        for value in second_row
                    )
                    if looks_like_header_tail and any(value not in header for value in second_row):
                        header = [value for value in header if value] + [value for value in second_row if value]
                        data_start_index = 2

            cleaned_header = [value for value in header if value]
            rows = []
            for raw_row in raw_rows[data_start_index:]:
                if not any(str(cell or "").strip() for cell in raw_row):
                    continue
                values = list(raw_row or [])
                if len(values) < len(cleaned_header):
                    values.extend([""] * (len(cleaned_header) - len(values)))
                row = {
                    cleaned_header[idx]: values[idx] if idx < len(values) else ""
                    for idx in range(len(cleaned_header))
                }
                rows.append(_normalize_row_keys(row))

            return set(cleaned_header), rows
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

        required_food = {"food_id", "name", "measurement", "protein", "carbs", "fats"}
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
            macro = _str_or_default(row.get("macro"), "-")
            raw_name = _str_or_default(row.get("name"), "-")
            raw_category = _str_or_default(row.get("category"), "")
            category = canonical_standard_name(raw_category or raw_name or "-")
            display_name = raw_name or category
            is_category_reference_row = bool(raw_category) and display_name.lower() == raw_category.lower()
            food_objects.append(
                FoodLibraryItem(
                    source_food_id=int(_str_or_default(row.get("food_id"), "0")),
                    macro=macro,
                    category=category,
                    name=category,
                    display_name=display_name,
                    canonical_name=category,
                    canonical_category=category,
                    source_type=FoodLibraryItem.SourceType.STANDARD,
                    approval_status=FoodLibraryItem.ApprovalStatus.APPROVED,
                    is_standard=True,
                    is_active=True,
                    measurement_unit=_str_or_default(row.get("measurement"), "oz"),
                    protein=_decimal_or_zero(row.get("protein")),
                    carbs=_decimal_or_zero(row.get("carbs")),
                    fats=_decimal_or_zero(row.get("fats")),
                    is_placeholder=(display_name == "-" or category == "-" or is_category_reference_row),
                )
            )

        FoodLibraryItem.objects.bulk_create(
            food_objects,
            batch_size=1000,
            update_conflicts=True,
            unique_fields=["source_food_id"],
            update_fields=[
                "macro",
                "category",
                "name",
                "display_name",
                "canonical_name",
                "canonical_category",
                "source_type",
                "approval_status",
                "is_standard",
                "is_active",
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
                    protein_slot_1=canonical_standard_name(row.get("c1_protein_1")),
                    protein_slot_2=canonical_standard_name(row.get("c1_protein_2")),
                    carb_slot_1=canonical_standard_name(row.get("c1_carbs_1")),
                    carb_slot_2=canonical_standard_name(row.get("c1_carbs_2")),
                    fat_slot_1=canonical_standard_name(row.get("c1_fats_1")),
                    fat_slot_2=canonical_standard_name(row.get("c1_fats_2")),
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
