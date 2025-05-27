# backend/users/admin_area/tasks/reactivate_admin_subscription.py

import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.admin_area.models.plan import Plan
from users.admin_area.models.profile import Profile
from users.admin_area.models.scheduled_subscription import ScheduledSubscription
from users.admin_area.utils.reactivation import (
    get_current_profile,
    is_mid_cycle_cancellation,
    schedule_future_subscription
)

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reactivate_admin_subscription(request):
    user = request.user
    plan_id = request.data.get("plan_id")

    if not plan_id:
        return Response({"error": "Missing plan_id"}, status=400)

    try:
        selected_plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Plan not found"}, status=404)

    current_profile = get_current_profile(user)

    # Determine the redirect URLs
    success_url = f"{settings.FRONTEND_URL}/admindashboard?reactivated=true"
    cancel_url = f"{settings.FRONTEND_URL}/adminreactivate"

    try:
        # Create Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": selected_plan.stripe_price_id,
                "quantity": 1,
            }],
            customer=user.stripe_customer_id if user.stripe_customer_id else None,
            success_url=f"{settings.FRONTEND_URL}/admindashboard?reactivated=true",
            cancel_url=f"{settings.FRONTEND_URL}/adminreactivate",
            metadata={
                "user_id": str(user.id),
                "plan_id": str(selected_plan.id),
                "plan_name": selected_plan.name,  # ✅ Add this line
                "is_reactivation": "true"
            },
        )

        # If reactivating mid-cycle with a different plan → schedule new activation
        if is_mid_cycle_cancellation(current_profile) and current_profile.plan != selected_plan:
            schedule_future_subscription(
                user=user,
                plan=selected_plan,
                start_date=current_profile.subscription_end_date,
                stripe_subscription_id="pending",  # Stripe ID will be filled in webhook
                stripe_transaction_id=None,
            )

        return Response({"checkout_url": session.url})

    except Exception as e:
        return Response({"error": str(e)}, status=500)
