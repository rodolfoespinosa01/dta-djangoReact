import stripe  # 👉 stripe sdk for billing and checkout
from rest_framework.views import APIView  # 👉 base class for class-based views
from rest_framework.response import Response  # 👉 formats API responses
from rest_framework import permissions, status  # 👉 handles permission and status codes
from django.conf import settings  # 👉 loads environment config like stripe keys
from django.utils.timezone import now  # 👉 gets the current timestamp

from users.admin_area.models import Profile, Plan, PendingPlanActivation  # 👉 core models for reactivation and scheduling

stripe.api_key = settings.STRIPE_SECRET_KEY  # 👉 set stripe secret key

class ReactivateCheckoutView(APIView):
    # ✅ Only authenticated users (admins) can access this endpoint
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        plan_name = request.data.get('plan_name')  # 📨 plan user is attempting to reactivate

        # 🔒 Only admins can proceed with reactivation
        if user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        # 🧾 Get the user's most recent active or canceled profile
        try:
            current_profile = user.profiles.get(is_current=True)
        except Profile.DoesNotExist:
            return Response({"error": "Current profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # 🔍 Validate that the requested plan exists in the database
        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            return Response({"error": "Invalid plan name."}, status=status.HTTP_400_BAD_REQUEST)

        # 🧠 Determine reactivation logic based on current profile's cancellation and expiration state
        is_canceled = current_profile.is_canceled
        sub_end = current_profile.subscription_end_date
        now_ts = now()

        if is_canceled and sub_end and sub_end > now_ts:
            # ✅ User still has time left in their previous billing period, so we delay activation
            reactivation_type = "scheduled"
        elif is_canceled and sub_end and sub_end <= now_ts:
            # ⏱️ Previous plan already expired — reactivation should be immediate
            reactivation_type = "immediate"
        else:
            # 🚫 Either not canceled or no clear subscription timing — block reactivation
            return Response({"error": "Account not eligible for reactivation."}, status=status.HTTP_400_BAD_REQUEST)

        # 🛒 Build a Stripe Checkout Session for the reactivation
        #    Includes metadata so the webhook knows how to handle the subscription
        checkout_kwargs = {
            "success_url": settings.REACTIVATE_SUCCESS_URL,  # ✅ redirect after payment success
            "cancel_url": settings.REACTIVATE_CANCEL_URL,    # ❌ redirect if user cancels checkout
            "payment_method_types": ['card'],
            "mode": "subscription",
            "line_items": [
                {
                    'price': plan.stripe_price_id,  # 💳 Stripe price ID for selected plan
                    'quantity': 1,
                }
            ],
            "subscription_data": {
                "metadata": {
                    'reactivation_type': reactivation_type,  # 🧠 used in webhook to decide when to activate
                    'user_id': str(user.id),                 # 🆔 needed for user lookup in webhook
                    'plan_name': plan_name,                  # 📦 for logging and future logic
                }
            }
        }

        # 🔁 If we already have a Stripe customer, attach it; otherwise use email to create one
        if user.stripe_customer_id:
            checkout_kwargs["customer"] = user.stripe_customer_id
        else:
            checkout_kwargs["customer_email"] = user.email

        try:
            # 🚀 Create the Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(**checkout_kwargs)

            # 🗓️ If this is a delayed activation, log it to the PendingPlanActivation table
            if reactivation_type == "scheduled":
                PendingPlanActivation.objects.update_or_create(
                    user=user,
                    defaults={
                        "plan_name": plan_name,
                        "scheduled_start": sub_end  # 📅 activate after the current billing period ends
                    }
                )
                print(f"🕓 Scheduled plan activation saved for {user.email} at {sub_end}")

            # 🔁 Return the Stripe-hosted URL to the frontend so the user can complete payment
            return Response({"url": checkout_session.url})

        except Exception as e:
            # ❌ If Stripe or logic fails, return error to frontend
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 👉 summary:
# handles reactivation flow by creating a new Stripe checkout session for canceled admins.
# determines if the reactivation is immediate or delayed, embeds metadata for webhook,
# and saves a PendingPlanActivation if needed. used for seamless plan resumption with billing automation.
