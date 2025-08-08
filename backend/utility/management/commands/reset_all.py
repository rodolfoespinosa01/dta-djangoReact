from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from users.admin_area.models import (
    Profile,
    PendingSignup,
    PasswordResetToken,
    PreCheckoutEmail,
    TransactionLog,
    AdminIdentity,
    EventTracker  # ✅ New models
)

class Command(BaseCommand):
    help = 'Fully resets admin data (users, tokens, profiles, scheduled subscriptions, etc.) for local testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()

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

        AdminIdentity.objects.all().delete()
        self.stdout.write(self.style.WARNING('🆔 Admin identities deleted.'))

        # Transaction Log
        TransactionLog.objects.all().delete()
        self.stdout.write(self.style.WARNING('🗒️ Transaction log entries deleted.'))

        self.stdout.write(self.style.SUCCESS('🎯 All admin-related test data reset!'))
