from decimal import Decimal
from django.core.paginator import Paginator

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.models import CustomUser
from users.admin_area.models import Plan
from users.superadmin_area.serializers.contracts import (
    SuperAdminDashboardItemSerializer,
    SuperAdminPaginationSerializer,
)
from .api_contract import error, ok, require_superadmin


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
    auth_error = require_superadmin(request)
    if auth_error:
        return auth_error

    try:
        page = int(request.query_params.get("page", 1) or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", 25) or 25)
    except (TypeError, ValueError):
        page_size = 25
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    admins_qs = CustomUser.objects.filter(role="admin").order_by("-date_joined")
    paginator = Paginator(admins_qs, page_size)
    page_obj = paginator.get_page(page)

    admin_data = []

    for admin in page_obj.object_list:
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

    admins_serializer = SuperAdminDashboardItemSerializer(data=admin_data, many=True)
    if not admins_serializer.is_valid():
        return error(
            code="DASHBOARD_PAYLOAD_INVALID",
            message="SuperAdmin dashboard payload validation failed.",
            http_status=500,
            details=admins_serializer.errors,
        )

    pagination_payload = {
        "page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "total_items": paginator.count,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }
    pagination_serializer = SuperAdminPaginationSerializer(data=pagination_payload)
    if not pagination_serializer.is_valid():
        return error(
            code="PAGINATION_PAYLOAD_INVALID",
            message="SuperAdmin pagination payload validation failed.",
            http_status=500,
            details=pagination_serializer.errors,
        )

    return ok(
        {
            "admins": admins_serializer.validated_data,
            "pagination": pagination_serializer.validated_data,
        }
    )
