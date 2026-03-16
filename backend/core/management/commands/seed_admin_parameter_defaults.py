from django.core.management.base import BaseCommand

from users.admin_area.services.admin_parameter_tables import seed_core_admin_parameter_defaults


class Command(BaseCommand):
    help = (
        "Seeds the core TDEE/Standard/Keto/Carb Cycling default tables with "
        "v1 defaults loaded from the core seed_data resources."
    )

    def handle(self, *args, **kwargs):
        defaults_data = seed_core_admin_parameter_defaults(version="v1")
        version = defaults_data.get("version", "v1")
        self.stdout.write(
            self.style.SUCCESS(
                f"Core admin parameter defaults seeded for version={version}."
            )
        )
