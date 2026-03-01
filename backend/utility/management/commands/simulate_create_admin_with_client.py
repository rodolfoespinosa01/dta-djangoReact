from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from datetime import timedelta

from users.admin_area.models import AdminIdentity, AdminParameterSettings, Plan
from users.admin_area.utils.log_Profile import log_Profile
from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1
from users.client_area.models import ClientProfile, ClientQuestionnaireProgress


class Command(BaseCommand):
    help = (
        "Create or find an admin and then create a client user tied to that admin (dev tool).\n"
        "Creates admin (user + AdminIdentity + parameter defaults optionally) then creates client user and ClientProfile linked to admin."
    )

    def add_arguments(self, parser):
        # Admin args
        parser.add_argument("admin_email", type=str, help="Admin email address")
        parser.add_argument("--admin_password", type=str, default="TestAdmin123!", help="Admin password")
        parser.add_argument("--plan_name", type=str, default="adminMonthly", help="Admin plan name")
        parser.add_argument("--admin_slug", type=str, default="", help="Subdomain slug for admin")
        parser.add_argument("--initialize_parameters", action="store_true", help="Initialize admin parameters")
        parser.add_argument("--is_trial", action="store_true", help="Mark admin as trial")

        # Client args
        parser.add_argument("client_email", type=str, help="Client email to create")
        parser.add_argument("--client_password", type=str, default="TestClient123!", help="Client password")
        parser.add_argument("--offer_code", type=str, default="macro_calculator_free", help="Client offer code")
        parser.add_argument("--billing_cycle", type=str, default="", help="Client billing cycle")
        parser.add_argument("--trial_days", type=int, default=0, help="Client trial days")
        parser.add_argument("--amount_cents", type=int, default=0, help="Client amount cents")
        parser.add_argument("--includes_food_plan", action="store_true", help="Client includes food plan")
        parser.add_argument("--includes_coaching", action="store_true", help="Client includes coaching")
        parser.add_argument("--coaching_term", type=str, default="none", help="Client coaching term")

    def handle(self, *args, **options):
        admin_email = options["admin_email"].strip().lower()
        admin_password = options["admin_password"]
        plan_name = options.get("plan_name") or "adminMonthly"
        admin_slug = (options.get("admin_slug") or "").strip().lower()
        initialize = bool(options.get("initialize_parameters"))
        is_trial = bool(options.get("is_trial"))

        client_email = options["client_email"].strip().lower()
        client_password = options.get("client_password")

        User = get_user_model()

        # --- Admin: find or create user ---
        admin_user = User.objects.filter(email=admin_email).first()
        if admin_user:
            self.stdout.write(self.style.WARNING(f"Admin user exists: {admin_email} — reusing"))
        else:
            admin_user = User.objects.create_user(username=admin_email, email=admin_email, password=admin_password)
            admin_user.role = "admin"
            admin_user.is_staff = True
            admin_user.subscription_status = "admin_monthly"
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))

        # Ensure AdminIdentity exists
        identity, _ = AdminIdentity.objects.get_or_create(admin_email=admin_email)
        if admin_slug:
            identity.subdomain_slug = admin_slug
            identity.save()

        # Initialize admin profile/plan
        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            raise CommandError(f"Plan '{plan_name}' not found. Seed plans first.")

        now = timezone.now()
        trial_start = now if is_trial else None
        next_billing = now + timedelta(days=14 if is_trial else 30)
        subscription_start = None if is_trial else now

        # create profile snapshot
        log_Profile(
            user=admin_user,
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

        # Initialize parameters if requested
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

        # --- Client creation ---
        if User.objects.filter(username=client_email).exists() or User.objects.filter(email=client_email).exists():
            raise CommandError("Client user already exists. Choose a different email or reset DB.")

        client_user = User.objects.create_user(username=client_email, email=client_email, password=client_password)
        client_user.role = "client"
        client_user.is_staff = False
        client_user.subscription_status = "admin_inactive"
        client_user.save()

        profile = ClientProfile.objects.create(
            user=client_user,
            associated_admin=identity,
            sale_channel="admin_white_label",
            offer_code=options.get("offer_code") or "",
            billing_cycle=options.get("billing_cycle") or "",
            trial_days=int(options.get("trial_days") or 0),
            amount_cents=int(options.get("amount_cents") or 0),
            includes_food_plan=bool(options.get("includes_food_plan")),
            includes_coaching=bool(options.get("includes_coaching")),
            coaching_term=options.get("coaching_term") or "none",
            is_active=True,
        )

        ClientQuestionnaireProgress.objects.create(user=client_user, status="not_started", current_step="", answers_json={})

        self.stdout.write(self.style.SUCCESS(f"✅ Admin ({admin_email}) ready (slug: {identity.subdomain_slug})."))
        self.stdout.write(self.style.SUCCESS(f"✅ Client created: {client_email} linked to admin {identity.admin_email} (slug: {identity.subdomain_slug})"))
        self.stdout.write(f"admin_initialized_parameters: {param_state}")
