from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Refresh the global food library from CSV files in table_defaults (preferred) "
        "or backend/algorithmtables (legacy fallback). "
        "This deletes current food library/combo data and reloads from CSVs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tables-dir",
            type=str,
            default=None,
            help="Optional override for CSV directory (defaults to table_defaults, fallback backend/algorithmtables).",
        )
        parser.add_argument(
            "--food-csv",
            type=str,
            default=None,
            help="Optional specific food CSV filename/path.",
        )
        parser.add_argument(
            "--combos-csv",
            type=str,
            default=None,
            help="Optional specific combo CSV filename/path.",
        )
        parser.add_argument(
            "--errors-csv",
            type=str,
            default=None,
            help="Optional specific combo-error CSV filename/path.",
        )
        parser.add_argument(
            "--skip-error-table",
            action="store_true",
            help="Skip importing combo error lookup CSV if not needed.",
        )

    def _first_existing(self, base_dir: Path, candidates: list[str]) -> Path | None:
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if not path.is_absolute():
                path = base_dir / candidate
            if path.exists():
                return path
        return None

    def handle(self, *args, **options):
        if options.get("tables_dir"):
            tables_dir = Path(options["tables_dir"]).resolve()
        else:
            backend_dir = Path(settings.BASE_DIR).resolve()
            project_root = backend_dir.parent
            preferred = project_root / "table_defaults"
            legacy = backend_dir / "algorithmtables"
            tables_dir = preferred if preferred.exists() else legacy

        food_csv = self._first_existing(
            tables_dir,
            [
                options.get("food_csv"),
                "MYSQL_food_lib.csv",
                "food_macros.csv",
            ],
        )
        combos_csv = self._first_existing(
            tables_dir,
            [
                options.get("combos_csv"),
                "c_1_new.csv",
                "meal_combo_templates.csv",
            ],
        )
        errors_csv = self._first_existing(
            tables_dir,
            [
                options.get("errors_csv"),
                "errorid_453030.csv",
                "combo_macro_error_lookup.csv",
            ],
        )

        missing = []
        if not food_csv:
            missing.append("food CSV (tried: MYSQL_food_lib.csv, food_macros.csv)")
        if not combos_csv:
            missing.append("combo CSV (tried: c_1_new.csv, meal_combo_templates.csv)")
        if not options["skip_error_table"] and not errors_csv:
            missing.append("error CSV (tried: errorid_453030.csv, combo_macro_error_lookup.csv)")

        if missing:
            raise CommandError(
                "Missing required CSV file(s) in project root:\n- "
                + "\n- ".join(missing)
                + "\n\nExpected files in table_defaults (or --tables-dir):\n"
                + "- MYSQL_food_lib.csv (or food_macros.csv)\n"
                + "- c_1_new.csv (or meal_combo_templates.csv)\n"
                + "- errorid_453030.csv (or combo_macro_error_lookup.csv, optional with --skip-error-table)"
            )

        self.stdout.write(f"Refreshing global food library from: {tables_dir}")
        kwargs = {
            "truncate": True,
        }
        if not options["skip_error_table"] and errors_csv:
            kwargs["combo_errors_csv"] = str(errors_csv)

        call_command("import_food_library_csv", str(food_csv), str(combos_csv), **kwargs)
        self.stdout.write(self.style.SUCCESS("Global food library refresh complete."))
