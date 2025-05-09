import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
from django.utils.timezone import now

from users.admin_area.models import Profile, Plan, PendingPlanActivation

stripe.api_key = settings.STRIPE_SECRET_KEY

class ReactivateCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        plan_name = request.data.get('plan_name')

        if user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        try:
            current_profile = user.profiles.get(is_current=True)
        except Profile.DoesNotExist:
            return Response({"error": "Current profile not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            return Response({"error": "Invalid plan name."}, status=status.HTTP_400_BAD_REQUEST)

        is_canceled = current_profile.is_canceled
        sub_end = current_profile.subscription_end_date
        now_ts = now()

        if is_canceled and sub_end and sub_end > now_ts:
            reactivation_type = "scheduled"
        elif is_canceled and sub_end and sub_end <= now_ts:
            reactivation_type = "immediate"
        else:
            return Response({"error": "Account not eligible for reactivation."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Metadata must go inside subscription_data
        checkout_kwargs = {
            "success_url": settings.REACTIVATE_SUCCESS_URL,
            "cancel_url": settings.REACTIVATE_CANCEL_URL,
            "payment_method_types": ['card'],
            "mode": "subscription",
            "line_items": [
                {
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }
            ],
            "subscription_data": {
                "metadata": {
                    'reactivation_type': reactivation_type,
                    'user_id': str(user.id),
                    'plan_name': plan_name,
                }
            }
        }

        if user.stripe_customer_id:
            checkout_kwargs["customer"] = user.stripe_customer_id
        else:
            checkout_kwargs["customer_email"] = user.email

        try:
            checkout_session = stripe.checkout.Session.create(**checkout_kwargs)

            if reactivation_type == "scheduled":
                PendingPlanActivation.objects.update_or_create(
                    user=user,
                    defaults={
                        "plan_name": plan_name,
                        "scheduled_start": sub_end
                    }
                )
                print(f"🕓 Scheduled plan activation saved for {user.email} at {sub_end}")

            return Response({"url": checkout_session.url})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
