from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Refresh the global food library from CSV files in backend/algorithmtables. "
        "This deletes current food library/combo data and reloads from CSVs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tables-dir",
            type=str,
            default=None,
            help="Optional override for algorithm tables directory (defaults to backend/algorithmtables).",
        )
        parser.add_argument(
            "--skip-error-table",
            action="store_true",
            help="Skip importing combo error lookup CSV if not needed.",
        )

    def handle(self, *args, **options):
        tables_dir = (
            Path(options["tables_dir"]).resolve()
            if options.get("tables_dir")
            else Path(settings.BASE_DIR).resolve() / "algorithmtables"
        )

        food_csv = tables_dir / "food_macros.csv"
        combos_csv = tables_dir / "meal_combo_templates.csv"
        errors_csv = tables_dir / "combo_macro_error_lookup.csv"

        missing = []
        if not food_csv.exists():
            missing.append(str(food_csv))
        if not combos_csv.exists():
            missing.append(str(combos_csv))
        if not options["skip_error_table"] and not errors_csv.exists():
            missing.append(str(errors_csv))

        if missing:
            raise CommandError(
                "Missing required CSV file(s) in project root:\n- "
                + "\n- ".join(missing)
                + "\n\nExpected files in backend/algorithmtables (or --tables-dir):\n"
                + "- food_macros.csv\n"
                + "- meal_combo_templates.csv\n"
                + "- combo_macro_error_lookup.csv (optional with --skip-error-table)"
            )

        self.stdout.write(f"Refreshing global food library from: {tables_dir}")
        kwargs = {
            "truncate": True,
        }
        if not options["skip_error_table"]:
            kwargs["combo_errors_csv"] = str(errors_csv)

        call_command("import_food_library_csv", str(food_csv), str(combos_csv), **kwargs)
        self.stdout.write(self.style.SUCCESS("Global food library refresh complete."))
