from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import psycopg2


class Command(BaseCommand):
    help = "⚠️ Drops the entire database and recreates it with fresh migrations (dev use only)."

    def handle(self, *args, **options):
        db_name = settings.DATABASES['default']['NAME']
        db_user = settings.DATABASES['default']['USER']
        db_password = settings.DATABASES['default']['PASSWORD']
        db_host = settings.DATABASES['default']['HOST']
        db_port = settings.DATABASES['default']['PORT']

        print(f"\n🚨 Full DB reset: Dropping and recreating `{db_name}`...\n")

        try:
            # Connect to 'postgres' to drop and recreate target DB
            conn = psycopg2.connect(
                dbname='postgres',
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")
            cursor.close()
            conn.close()

            print("✅ Database recreated.")

            # Run migrations fresh
            call_command('makemigrations')
            call_command('migrate')

            print("\n✅ Migrations applied. Fresh DB ready.\n")

        except Exception as e:
            self.stderr.write(f"❌ Error during full DB reset: {e}")
