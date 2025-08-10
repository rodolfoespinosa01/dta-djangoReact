from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management.color import no_style
from django.db import connection, transaction

from users.admin_area.models import (
    Profile,
    PendingSignup,
    PasswordResetToken,
    PreCheckoutEmail,
    TransactionLog,
    AdminIdentity,
    EventTracker
)

class Command(BaseCommand):
    help = 'Fully resets admin data (users, tokens, profiles, scheduled subscriptions, etc.) for local testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        with transaction.atomic():
            # Delete all users except the superadmin
            User.objects.exclude(username='dta_user').delete()

            # Reset Password Tokens & Pre-Checkout Emails
            PasswordResetToken.objects.all().delete()
            self.stdout.write(self.style.WARNING('🔒 Password reset tokens deleted.'))

            PreCheckoutEmail.objects.all().delete()
            self.stdout.write(self.style.WARNING('📬 Pre-checkout emails deleted.'))

            # Delete all profiles except superadmin's
            try:
                superadmin = User.objects.get(username='dta_user')
                Profile.objects.exclude(user=superadmin).delete()
            except User.DoesNotExist:
                Profile.objects.all().delete()
            self.stdout.write(self.style.WARNING('👤 Admin profiles deleted.'))

            # Pending signups
            PendingSignup.objects.all().delete()
            self.stdout.write(self.style.WARNING('⏳ Pending signup entries deleted.'))

            # Event tracking (replaces AccountHistory)
            EventTracker.objects.all().delete()
            self.stdout.write(self.style.WARNING('📚 Event tracker entries deleted.'))

            # Admin identities
            AdminIdentity.objects.all().delete()
            self.stdout.write(self.style.WARNING('🆔 Admin identities deleted.'))

            # Transaction Log
            TransactionLog.objects.all().delete()
            self.stdout.write(self.style.WARNING('🗒️ Transaction log entries deleted.'))

            # ---- Reset auto-increment/sequence counters ----
            models_to_reset = [
                PasswordResetToken,
                PreCheckoutEmail,
                PendingSignup,
                EventTracker,
                AdminIdentity,
                TransactionLog,
                Profile,  # included since we deleted many of them
            ]

            sql_list = connection.ops.sequence_reset_sql(no_style(), models_to_reset)
            with connection.cursor() as cursor:
                for sql in sql_list:
                    cursor.execute(sql)

        self.stdout.write(self.style.SUCCESS('🎯 All admin-related test data reset and sequences restarted!'))
