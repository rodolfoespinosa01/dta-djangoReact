from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model

from users.admin_area.models import AdminIdentity
from users.client_area.models import ClientProfile, ClientQuestionnaireProgress


class Command(BaseCommand):
    help = "Create a client user tied to an existing AdminIdentity (dev tool)."

    def add_arguments(self, parser):
        parser.add_argument("admin_email_or_slug", type=str, help="Admin email or subdomain slug to associate the client with")
        parser.add_argument("client_email", type=str, help="Client email address to create")
        parser.add_argument("--password", type=str, default="TestClient123!", help="Client password")
        parser.add_argument("--offer_code", type=str, default="macro_calculator_free", help="Offer code for client profile")
        parser.add_argument("--billing_cycle", type=str, default="", help="Billing cycle")
        parser.add_argument("--trial_days", type=int, default=0, help="Trial days")
        parser.add_argument("--amount_cents", type=int, default=0, help="Amount in cents")
        parser.add_argument("--includes_food_plan", action="store_true", help="Set includes_food_plan True")
        parser.add_argument("--includes_coaching", action="store_true", help="Set includes_coaching True")
        parser.add_argument("--coaching_term", type=str, default="none", help="coaching term: none/1_month/3_months")

    def handle(self, *args, **options):
        admin_in = options["admin_email_or_slug"].strip().lower()
        client_email = options["client_email"].strip().lower()
        password = options.get("password")

        # find admin identity by email or slug
        admin = AdminIdentity.objects.filter(admin_email__iexact=admin_in).first()
        if not admin:
            admin = AdminIdentity.objects.filter(subdomain_slug__iexact=admin_in).first()
        if not admin:
            raise CommandError("AdminIdentity not found by email or slug: %s" % admin_in)

        User = get_user_model()
        if User.objects.filter(username=client_email).exists() or User.objects.filter(email=client_email).exists():
            raise CommandError("Client user already exists. Choose a different email or reset DB.")

        user = User.objects.create_user(username=client_email, email=client_email, password=password)
        user.role = "client"
        user.is_staff = False
        user.subscription_status = "admin_inactive"
        user.save()

        profile = ClientProfile.objects.create(
            user=user,
            associated_admin=admin,
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

        ClientQuestionnaireProgress.objects.create(user=user, status="not_started", current_step="", answers_json={})

        self.stdout.write(self.style.SUCCESS(f"✅ Client user created: {client_email} (admin: {admin.admin_email})"))
        self.stdout.write(f"client_email: {client_email}")
        self.stdout.write(f"associated_admin: {admin.admin_email} (slug: {admin.subdomain_slug})")
        self.stdout.write(f"offer_code: {profile.offer_code}, trial_days: {profile.trial_days}, amount_cents: {profile.amount_cents}")
