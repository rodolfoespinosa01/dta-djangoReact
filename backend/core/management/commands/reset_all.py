from pathlib import Path
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import DatabaseError, ProgrammingError
from django.db import connection, transaction

from users.admin_area.models import (
    AdminDiscountCode,
    AdminIdentity,
    EventTracker,
    PasswordResetToken,
    PendingSignup,
    PreCheckout,
    Profile,
    TransactionLog,
)
from users.client_area.models import (
    ClientMacroAccessLink,
    ClientPendingSignup,
    DiscountCode as ClientDiscountCode,
)

SUPERADMIN_USERNAME = "dta_user"
TEST_ADMIN_EMAIL = "admin@dta.com"
TEST_ADMIN_PASSWORD = "test1234"


class Command(BaseCommand):
    help = "Fully resets admin/client local data and clears uploaded media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-media",
            action="store_true",
            help="Skip deleting files in MEDIA_ROOT.",
        )

    def _table_exists(self, model):
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            return table_name in connection.introspection.table_names(cursor)

    def _safe_delete_all(self, queryset, label):
        model = queryset.model
        if not self._table_exists(model):
            self.stdout.write(self.style.WARNING(f"Skipping {label} (table not migrated yet)."))
            return
        try:
            with transaction.atomic():
                queryset.delete()
            self.stdout.write(self.style.WARNING(label))
        except (ProgrammingError, DatabaseError) as exc:
            self.stdout.write(
                self.style.WARNING(f"Skipping {label} (table unavailable: {exc.__class__.__name__}).")
            )

    def _clear_media_root(self):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        backend_root = Path(settings.BASE_DIR).resolve()
        expected_media_root = (backend_root / "media").resolve()

        if media_root != expected_media_root:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping media wipe because MEDIA_ROOT is unexpected: {media_root}"
                )
            )
            return

        if not media_root.exists():
            media_root.mkdir(parents=True, exist_ok=True)
            self.stdout.write(self.style.WARNING("Media folder did not exist; created empty MEDIA_ROOT."))
            return

        for child in media_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

        self.stdout.write(self.style.WARNING(f"Uploaded media deleted from {media_root}"))

    def _ensure_test_admin(self, user_model):
        admin_user, created = user_model.objects.get_or_create(
            username=TEST_ADMIN_EMAIL,
            defaults={
                "email": TEST_ADMIN_EMAIL,
                "role": "admin",
                "is_staff": True,
                "is_active": True,
                "subscription_status": "admin_inactive",
            },
        )

        changed_fields = []
        if admin_user.email != TEST_ADMIN_EMAIL:
            admin_user.email = TEST_ADMIN_EMAIL
            changed_fields.append("email")
        if getattr(admin_user, "role", None) != "admin":
            admin_user.role = "admin"
            changed_fields.append("role")
        if not admin_user.is_staff:
            admin_user.is_staff = True
            changed_fields.append("is_staff")
        if not admin_user.is_active:
            admin_user.is_active = True
            changed_fields.append("is_active")
        if getattr(admin_user, "subscription_status", None) != "admin_inactive":
            admin_user.subscription_status = "admin_inactive"
            changed_fields.append("subscription_status")

        admin_user.set_password(TEST_ADMIN_PASSWORD)
        changed_fields.append("password")
        admin_user.save(update_fields=changed_fields)

        AdminIdentity.objects.get_or_create(admin_email=TEST_ADMIN_EMAIL)

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Test admin {action}: {TEST_ADMIN_EMAIL}"))

    def handle(self, *args, **kwargs):
        keep_media = kwargs.get("keep_media", False)
        user_model = get_user_model()

        with transaction.atomic():
            superadmin = user_model.objects.filter(username=SUPERADMIN_USERNAME).first()

            user_model.objects.exclude(username=SUPERADMIN_USERNAME).delete()

            self._safe_delete_all(PasswordResetToken.objects.all(), "Password reset tokens deleted.")
            self._safe_delete_all(PreCheckout.objects.all(), "Pre-checkout rows deleted.")

            if superadmin:
                Profile.objects.exclude(user=superadmin).delete()
            else:
                Profile.objects.all().delete()
            self.stdout.write(self.style.WARNING("Admin profiles deleted."))

            self._safe_delete_all(PendingSignup.objects.all(), "Pending signup rows deleted.")
            self._safe_delete_all(EventTracker.objects.all(), "Event tracker rows deleted.")
            self._safe_delete_all(ClientDiscountCode.objects.all(), "Client discount codes deleted.")
            self._safe_delete_all(ClientPendingSignup.objects.all(), "Client pending signups deleted.")
            self._safe_delete_all(ClientMacroAccessLink.objects.all(), "Client macro access links deleted.")
            self._safe_delete_all(AdminDiscountCode.objects.all(), "Admin discount codes deleted.")
            self._safe_delete_all(AdminIdentity.objects.all(), "Admin identities deleted.")
            self._safe_delete_all(TransactionLog.objects.all(), "Transaction logs deleted.")

            models_to_reset = [
                user_model,
                PasswordResetToken,
                PreCheckout,
                PendingSignup,
                EventTracker,
                ClientDiscountCode,
                ClientPendingSignup,
                ClientMacroAccessLink,
                AdminDiscountCode,
                AdminIdentity,
                TransactionLog,
                Profile,
            ]
            resettable_models = [m for m in models_to_reset if self._table_exists(m)]
            sql_list = connection.ops.sequence_reset_sql(no_style(), resettable_models)
            with connection.cursor() as cursor:
                for sql in sql_list:
                    cursor.execute(sql)

            if superadmin:
                prof = Profile.objects.filter(user=superadmin).first()
                if prof:
                    dirty = False
                    for field in ("stripe_customer_id", "stripe_subscription_id", "current_price_id"):
                        if hasattr(prof, field):
                            setattr(prof, field, None)
                            dirty = True
                    if hasattr(prof, "is_canceled"):
                        prof.is_canceled = False
                        dirty = True
                    if hasattr(prof, "subscription_active"):
                        prof.subscription_active = False
                        dirty = True
                    if hasattr(prof, "is_active"):
                        prof.is_active = False
                        dirty = True
                    if dirty:
                        prof.save(
                            update_fields=[
                                f
                                for f in [
                                    "stripe_customer_id",
                                    "stripe_subscription_id",
                                    "current_price_id",
                                    "is_canceled",
                                    "subscription_active",
                                    "is_active",
                                ]
                                if hasattr(prof, f)
                            ]
                        )

            self._ensure_test_admin(user_model)

        if not keep_media:
            self._clear_media_root()
        else:
            self.stdout.write(self.style.WARNING("Skipping media wipe due to --keep-media."))

        self.stdout.write(self.style.SUCCESS("All local reset operations completed."))
