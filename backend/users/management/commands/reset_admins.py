from django.core.management.base import BaseCommand
from users.models import CustomUser, AdminPasswordResetToken
from adminplans.models import PendingAdminSignup
from django.conf import settings

class Command(BaseCommand):
    help = 'Resets all admin users, pending signups, and password reset tokens (dev only)'

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            self.stdout.write(self.style.ERROR("⚠️  This command is only allowed in DEBUG mode."))
            return

        CustomUser.objects.filter(role='admin').delete()
        PendingAdminSignup.objects.all().delete()
        AdminPasswordResetToken.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("✅ Admin users, pending signups, and tokens have been reset."))
