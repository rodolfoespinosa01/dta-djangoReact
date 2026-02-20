from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import CustomUser
from users.admin_area.models import Plan


def _sum_admin_spend_dollars(admin):
    total_cents = 0
    seen_transactions = set()

    for profile in admin.profiles.select_related("plan").order_by("created_at"):
        if not profile.plan or profile.is_trial:
            continue
        if profile.plan.price_cents <= 0:
            continue

        tx_id = (profile.stripe_transaction_id or "").strip()
        dedupe_key = tx_id or str(profile.profile_id)
        if dedupe_key in seen_transactions:
            continue

        seen_transactions.add(dedupe_key)
        total_cents += profile.plan.price_cents

    return float(Decimal(total_cents) / Decimal("100"))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user

    if not user.is_superuser:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    admins = CustomUser.objects.filter(role="admin").order_by("-date_joined")
    admin_data = []

    for admin in admins:
        latest_profile = admin.profiles.select_related("plan").order_by("-created_at").first()

        status_label = admin.subscription_status or "admin_inactive"
        price = None
        next_billing_str = ""
        cancelled = False

        if status_label == "admin_inactive":
            price = ""
        elif status_label == "admin_trial":
            monthly_plan = Plan.objects.filter(name="adminMonthly").first()
            price = monthly_plan.price_dollars() if monthly_plan else "Unknown"
            if latest_profile and latest_profile.next_billing:
                next_billing_str = latest_profile.next_billing.strftime("%Y-%m-%d")
        else:
            plan_name = status_label.replace("admin_", "admin").capitalize()
            plan = Plan.objects.filter(name__icontains=plan_name).first()
            price = plan.price_dollars() if plan else "Unknown"
            if latest_profile and latest_profile.next_billing:
                next_billing_str = latest_profile.next_billing.strftime("%Y-%m-%d")

        if latest_profile:
            cancelled = bool(latest_profile.is_canceled)

        admin_data.append(
            {
                "email": admin.email,
                "plan": status_label,
                "price": price,
                "next_billing": next_billing_str,
                "cancelled": cancelled,
                "amount_spent": _sum_admin_spend_dollars(admin),
            }
        )

    return Response({"admins": admin_data}, status=status.HTTP_200_OK)
