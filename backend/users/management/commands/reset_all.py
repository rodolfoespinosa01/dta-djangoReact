from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from adminplans.models import AdminProfile
from users.models import AdminPasswordResetToken

class Command(BaseCommand):
    help = 'Fully resets admin data (users, tokens, profiles) for local testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Keep dta_user, delete other users
        deleted_users, _ = User.objects.exclude(username='dta_user').delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted_users} non-superadmin users.'))

        # Delete admin password reset tokens
        token_count, _ = AdminPasswordResetToken.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'🔒 Cleared {token_count} admin password reset tokens.'))

        # Delete AdminProfiles not linked to dta_user
        superadmin = User.objects.get(username='dta_user')
        profile_count, _ = AdminProfile.objects.exclude(user=superadmin).delete()
        self.stdout.write(self.style.SUCCESS(f'🧾 Deleted {profile_count} AdminProfiles (excluding dta_user).'))

        self.stdout.write(self.style.SUCCESS('🎯 All admin test data reset!'))
