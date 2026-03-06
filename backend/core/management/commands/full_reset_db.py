import psycopg2

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Drops and recreates the dev database, reapplies migrations, and runs reset_all."

    def handle(self, *args, **options):
        db_name = settings.DATABASES["default"]["NAME"]
        db_user = settings.DATABASES["default"]["USER"]
        db_password = settings.DATABASES["default"]["PASSWORD"]
        db_host = settings.DATABASES["default"]["HOST"]
        db_port = settings.DATABASES["default"]["PORT"]

        self.stdout.write(f"Dropping and recreating database `{db_name}`...")

        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")
            cursor.close()
            conn.close()

            self.stdout.write(self.style.SUCCESS("Database recreated."))

            call_command("makemigrations")
            call_command("migrate")
            call_command("reset_all")

            self.stdout.write(self.style.SUCCESS("Fresh DB ready with reset data/media state."))
        except Exception as exc:
            self.stderr.write(f"Error during full DB reset: {exc}")
