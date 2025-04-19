from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from adminplans.models import AdminProfile, PendingAdminSignup
from users.models.admin_password_reset_token import AdminPasswordResetToken

class Command(BaseCommand):
    help = 'Fully resets admin data (users, tokens, profiles, pending signups) for local testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Delete non-superadmin users
        User.objects.exclude(username='dta_user').delete()

        # Delete admin password reset tokens
        AdminPasswordResetToken.objects.all().delete()

        # Delete AdminProfiles not linked to dta_user
        try:
            superadmin = User.objects.get(username='dta_user')
            AdminProfile.objects.exclude(user=superadmin).delete()
        except User.DoesNotExist:
            AdminProfile.objects.all().delete()

        # Delete PendingAdminSignup entries
        PendingAdminSignup.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('🎯 All admin test data reset!'))
