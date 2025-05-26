from rest_framework.views import APIView  # 👉 base class for building custom API views
from rest_framework.response import Response  # 👉 used to send structured JSON responses
from rest_framework import permissions, status  # 👉 access control and HTTP status codes
from django.utils.timezone import now  # 👉 provides current timestamp

from users.admin_area.models import Profile, ScheduledSubscription  # 👉 models used to determine admin subscription state


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # 🔐 only logged-in users can access this view

    def get(self, request):
        user = request.user

        # 🔒 only admins can access this dashboard
        if user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        # 📦 fetch the current active profile for this admin
        try:
            profile = user.profiles.get(is_current=True)
        except Profile.DoesNotExist:
            return Response({"error": "Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # 🕓 snapshot of current time for comparisons
        now_ts = now()

        subscription_status = user.subscription_status
        is_canceled = profile.is_canceled

        # ⚠️ determine if subscription is inactive due to cancellation or expiration
        is_trial = subscription_status == "admin_trial"
        trial_expired = is_trial and (is_canceled or (profile.subscription_end_date and profile.subscription_end_date <= now_ts))
        paid_expired = not is_trial and (is_canceled and profile.subscription_end_date and profile.subscription_end_date <= now_ts)

        inactive = trial_expired or paid_expired
        is_active = not inactive


        # 📅 map the subscription start dates based on plan type
        start_dates = {
            "admin_trial": profile.subscription_start_date if subscription_status == "admin_trial" else None,
            "admin_monthly": profile.subscription_start_date if subscription_status == "admin_monthly" else None,
            "admin_quarterly": profile.subscription_start_date if subscription_status == "admin_quarterly" else None,
            "admin_annual": profile.subscription_start_date if subscription_status == "admin_annual" else None,
        }

        # 🔄 check if this user has a reactivation scheduled for later
        reactivation = ScheduledSubscription.objects.filter(user=user).first()
        reactivation_pending = bool(reactivation)
        reactivation_start_date = reactivation.start_date if reactivation else None

        # 📤 build the response object returned to the frontend dashboard
        response_data = {
            "subscription_status": subscription_status,
            "subscription_active": is_active,
            "is_canceled": is_canceled,
            "inactive": inactive,
            "subscription_end_date": profile.subscription_end_date,
            "trial_start": start_dates["admin_trial"],
            "is_trial": is_trial and is_active,
            "days_remaining": (profile.subscription_end_date - now_ts).days if is_trial and profile.subscription_end_date else None,
            "monthly_start": start_dates["admin_monthly"],
            "quarterly_start": start_dates["admin_quarterly"],
            "annual_start": start_dates["admin_annual"],
            "next_billing_date": profile.next_billing_date if is_active else None,
            "reactivation_pending": reactivation_pending,
            "reactivation_start_date": reactivation_start_date,
        }

        return Response(response_data)


# 👉 summary:
# returns all billing-related metadata for an authenticated admin user.
# determines if the subscription is active, canceled, expired, or trial-based.
# includes plan start dates, remaining trial days, and reactivation status.
# supports frontend logic for showing access warnings, countdowns, or reactivation options.