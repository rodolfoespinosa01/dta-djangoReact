# backend/users/management/commands/reset_admin_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from users.admin_area.models import (
    Profile,
    PendingSignup,
    PasswordResetToken,
)

class Command(BaseCommand):
    help = 'Fully resets admin data (users, tokens, profiles, pending signups) for local testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Delete non-superadmin users
        User.objects.exclude(username='dta_user').delete()

        # Delete password reset tokens
        PasswordResetToken.objects.all().delete()

        # Delete profiles not linked to superadmin
        try:
            superadmin = User.objects.get(username='dta_user')
            Profile.objects.exclude(user=superadmin).delete()
        except User.DoesNotExist:
            Profile.objects.all().delete()

        # Delete pending signups
        PendingSignup.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('🎯 All admin test data reset!'))
