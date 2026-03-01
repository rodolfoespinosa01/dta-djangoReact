from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string

from users.client_area.models import ClientPendingSignup
from users.admin_area.models import AdminIdentity
from users.client_area.services.pricing import OFFER_CATALOG


class Command(BaseCommand):
    help = (
        "Create a pending client signup exactly the way a successful Stripe checkout would.\n"
        "Use this in DEBUG mode to simulate end-user signups without visiting Postman."
    )

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email address for the new client")
        parser.add_argument("offer_code", type=str, help="Offer code (see OFFER_CATALOG) e.g. macro_calculator_free, standard_monthly, premium_monthly")
        parser.add_argument(
            "--admin_slug",
            type=str,
            default="",
            help="Optional admin subdomain slug if signup is via a white‑label page",
        )
        parser.add_argument(
            "--sale_channel",
            type=str,
            default="dta_direct",
            help="Sales channel metadata (dta_direct/admin_white_label)",
        )
        parser.add_argument(
            "--trial_days",
            type=int,
            default=0,
            help="How many trial days the customer should receive",
        )
        parser.add_argument(
            "--amount_cents",
            type=int,
            default=None,
            help="Override amount_cents if you want to force a value",
        )
        parser.add_argument(
            "--includes_food_plan",
            action="store_true",
            help="Force includes_food_plan True (otherwise pulled from offer)",
        )
        parser.add_argument(
            "--includes_coaching",
            action="store_true",
            help="Force includes_coaching True (otherwise pulled from offer)",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        offer_code = options["offer_code"].strip()
        admin_slug = options["admin_slug"].strip().lower()
        sale_channel = options["sale_channel"].strip() or "dta_direct"

        if offer_code not in OFFER_CATALOG:
            raise CommandError(f"Offer code '{offer_code}' not found in OFFER_CATALOG")

        offer = OFFER_CATALOG[offer_code]
        admin = None
        if admin_slug:
            admin = AdminIdentity.objects.filter(subdomain_slug=admin_slug).first()
            if not admin:
                raise CommandError(f"Admin slug '{admin_slug}' not found")
            sale_channel = "admin_white_label"

        # delete any existing pending row to mirror webhook behaviour
        ClientPendingSignup.objects.filter(email__iexact=email).delete()

        billing_cycle = offer.get("billing_cycle")
        amount_cents = (
            options["amount_cents"]
            if options["amount_cents"] is not None
            else int(offer.get("amount_cents") or 0)
        )
        includes_food_plan = (
            options["includes_food_plan"] or bool(offer.get("includes_food_plan"))
        )
        includes_coaching = (
            options["includes_coaching"] or bool(offer.get("includes_coaching"))
        )

        token = get_random_string(64)
        pending = ClientPendingSignup.objects.create(
            email=email,
            token=token,
            admin=admin,
            sale_channel=sale_channel,
            offer_code=offer_code,
            billing_cycle=billing_cycle,
            trial_days=max(0, options.get("trial_days", 0)),
            amount_cents=max(0, amount_cents),
            includes_food_plan=includes_food_plan,
            includes_coaching=includes_coaching,
            registration_link_printed_at=timezone.now(),
        )

        self.stdout.write(self.style.SUCCESS(f"🎉 Pending signup created for {email}"))
        self.stdout.write(f"token: {pending.token}")
        self.stdout.write(f"offer_code: {offer_code}, sale_channel: {sale_channel}")
