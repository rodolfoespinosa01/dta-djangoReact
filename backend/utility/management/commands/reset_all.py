# backend/users/admin_area/management/commands/reset_all.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management.color import no_style
from django.db import DatabaseError, ProgrammingError
from django.db import connection, transaction

from users.admin_area.models import (
    Profile,
    PendingSignup,
    PasswordResetToken,
    PreCheckout,
    TransactionLog,
    AdminIdentity,
    EventTracker,
    AdminDiscountCode,
    # Plan,  # uncomment if you want optional seeding at the end
)
from users.client_area.models import DiscountCode as ClientDiscountCode

SUPERADMIN_USERNAME = "dta_user"

class Command(BaseCommand):
    help = "Fully resets admin data (users, tokens, profiles, identities, logs) for local testing."

    def _table_exists(self, model):
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            return table_name in connection.introspection.table_names(cursor)

    def _safe_delete_all(self, queryset, label):
        model = queryset.model
        if not self._table_exists(model):
            self.stdout.write(self.style.WARNING(f"⏭️ Skipping {label} (table not migrated yet)."))
            return
        try:
            # Use a savepoint so a missing related table (from unapplied migrations)
            # does not break the outer reset transaction.
            with transaction.atomic():
                queryset.delete()
            self.stdout.write(self.style.WARNING(label))
        except (ProgrammingError, DatabaseError) as exc:
            self.stdout.write(self.style.WARNING(f"⏭️ Skipping {label} (table unavailable: {exc.__class__.__name__})."))

    def handle(self, *args, **kwargs):
        User = get_user_model()

        with transaction.atomic():
            # Keep the superadmin if present
            superadmin = User.objects.filter(username=SUPERADMIN_USERNAME).first()

            # 1) Delete users except superadmin
            User.objects.exclude(username=SUPERADMIN_USERNAME).delete()

            # 2) App data wipes
            self._safe_delete_all(PasswordResetToken.objects.all(), "🔒 Password reset tokens deleted.")
            self._safe_delete_all(PreCheckout.objects.all(), "📬 Pre-checkout emails deleted.")

            # Delete all profiles except superadmin's (if it exists)
            if superadmin:
                Profile.objects.exclude(user=superadmin).delete()
            else:
                Profile.objects.all().delete()
            self.stdout.write(self.style.WARNING("👤 Admin profiles deleted."))

            self._safe_delete_all(PendingSignup.objects.all(), "⏳ Pending signup entries deleted.")
            self._safe_delete_all(EventTracker.objects.all(), "📚 Event tracker entries deleted.")
            self._safe_delete_all(ClientDiscountCode.objects.all(), "🏷️ Client discount codes deleted.")
            self._safe_delete_all(AdminDiscountCode.objects.all(), "🏷️ Admin discount codes deleted.")
            self._safe_delete_all(AdminIdentity.objects.all(), "🆔 Admin identities deleted.")
            self._safe_delete_all(TransactionLog.objects.all(), "🗒️ Transaction log entries deleted.")

            # 3) Reset sequences (include auth user and your app models)
            models_to_reset = [
                User,  # ✅ reset auth_user sequence too
                PasswordResetToken,
                PreCheckout,
                PendingSignup,
                EventTracker,
                ClientDiscountCode,
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

            # 4) Clean up superadmin's profile Stripe links (avoid dangling test IDs)
            if superadmin:
                prof = Profile.objects.filter(user=superadmin).first()
                if prof:
                    dirty = False
                    for field in ("stripe_customer_id", "stripe_subscription_id", "current_price_id"):
                        if hasattr(prof, field):
                            setattr(prof, field, None)
                            dirty = True
                    if hasattr(prof, "is_canceled"):
                        prof.is_canceled = False; dirty = True
                    if hasattr(prof, "subscription_active"):
                        prof.subscription_active = False; dirty = True
                    if hasattr(prof, "is_active"):
                        prof.is_active = False  # keep superadmin clean; app can create a fresh active profile
                        dirty = True
                    if dirty:
                        prof.save(update_fields=[f for f in ["stripe_customer_id","stripe_subscription_id","current_price_id","is_canceled","subscription_active","is_active"] if hasattr(prof, f)])

        self.stdout.write(self.style.SUCCESS("🎯 All admin-related test data reset and sequences restarted!"))

        # --- Optional: quick seeding so reactivation page shows plans ---
        # from django.conf import settings
        # import os
        # Plan.objects.update_or_create(name="adminMonthly",   defaults={"description":"Monthly Admin Plan",   "stripe_price_id": os.getenv("PRICE_ADMIN_MONTHLY", "price_month_test")})
        # Plan.objects.update_or_create(name="adminQuarterly", defaults={"description":"Quarterly Admin Plan","stripe_price_id": os.getenv("PRICE_ADMIN_QUARTERLY","price_quarter_test")})
        # Plan.objects.update_or_create(name="adminAnnual",    defaults={"description":"Annual Admin Plan",   "stripe_price_id": os.getenv("PRICE_ADMIN_ANNUAL",   "price_year_test")})
        # self.stdout.write(self.style.SUCCESS("✅ Plans upserted."))
