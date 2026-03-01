from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from datetime import timedelta

from users.admin_area.models import AdminIdentity, AdminParameterSettings, Plan
from users.admin_area.utils.log_Profile import log_Profile
from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1


class Command(BaseCommand):
    help = (
        "Create an admin user + AdminIdentity for local development.\n"
        "Optionally initialize admin parameter settings."
    )

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Admin email address")
        parser.add_argument("--password", type=str, default="TestAdmin123!", help="Password for admin user")
        parser.add_argument("--plan_name", type=str, default="adminMonthly", help="Plan name (adminMonthly/adminQuarterly/adminAnnual)")
        parser.add_argument("--is_trial", action="store_true", help="Create as trial")
        parser.add_argument("--initialize_parameters", action="store_true", help="Initialize parameter settings for this admin")
        parser.add_argument("--admin_slug", type=str, default="", help="Optional subdomain slug to set on AdminIdentity")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options.get("password")
        plan_name = options.get("plan_name") or "adminMonthly"
        is_trial = bool(options.get("is_trial"))
        initialize = bool(options.get("initialize_parameters"))
        admin_slug = (options.get("admin_slug") or "").strip().lower()

        User = get_user_model()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise CommandError("User already exists. Choose a different email or reset your DB.")

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            raise CommandError(f"Plan '{plan_name}' not found. Seed plans before creating admins.")

        # create user
        user = User.objects.create_user(username=email, email=email, password=password)
        user.role = "admin"
        user.is_staff = True
        # subscription_status mapping similar to view
        mapping = {"adminMonthly": "admin_monthly", "adminQuarterly": "admin_quarterly", "adminAnnual": "admin_annual"}
        user.subscription_status = mapping.get(plan_name, "admin_monthly")
        user.save()

        # create AdminIdentity
        identity, created = AdminIdentity.objects.get_or_create(admin_email=email)
        if admin_slug:
            identity.subdomain_slug = admin_slug
            identity.save()

        # profile/log
        now = timezone.now()
        trial_start = now if is_trial else None
        next_billing = now + timedelta(days=14 if is_trial else 30)
        subscription_start = None if is_trial else now

        log_Profile(
            user=user,
            plan=plan,
            stripe_transaction_id="dev_seed",
            is_trial=is_trial,
            trial_start=trial_start,
            subscription_start=subscription_start,
            subscription_end=None,
            next_billing=next_billing,
            is_active=True,
            is_canceled=False,
        )

        param_state = {"exists": False, "initialized": False}
        if initialize:
            settings_obj, _ = AdminParameterSettings.objects.get_or_create(admin=identity)
            param_state["exists"] = True
            defaults = get_admin_parameter_defaults_v1()
            settings_obj.parameters_json = defaults
            settings_obj.defaults_version_applied = defaults.get("version", "v1")
            settings_obj.initialized = True
            settings_obj.save(update_fields=["parameters_json", "defaults_version_applied", "initialized", "updated_at"])
            param_state["initialized"] = True

        self.stdout.write(self.style.SUCCESS(f"✅ Admin created: {email}"))
        self.stdout.write(f"admin_email: {email}")
        self.stdout.write(f"admin_slug: {identity.subdomain_slug}")
        self.stdout.write(f"initialized_parameters: {param_state}")
