from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from adminplans.models import AdminProfile
from datetime import date


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        try:
            profile = user.admin_profile
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

        subscription_status = user.subscription_status  # e.g., "admin_monthly"
        plan = subscription_status.replace('_', '').lower()  # Normalize to match conditions

        is_cancelled = profile.auto_renew_cancelled
        is_trial = plan == 'admintrial'
        trial_active = is_trial and not profile.is_trial_expired()

        # Determine if subscription is active
        is_active = plan in ['admintrial', 'adminmonthly', 'adminquarterly', 'adminannual'] and not is_cancelled

        # Assign start dates based on plan
        trial_start = profile.trial_start_date
        monthly_start = profile.subscription_started_at if plan == 'adminmonthly' else None
        quarterly_start = profile.subscription_started_at if plan == 'adminquarterly' else None
        annual_start = profile.subscription_started_at if plan == 'adminannual' else None

        response_data = {
            "subscription_status": subscription_status,
            "subscription_active": is_active,
            "trial_start": trial_start,
            "monthly_start": monthly_start,
            "quarterly_start": quarterly_start,
            "annual_start": annual_start,
            "next_billing_date": profile.next_billing_date if is_active else None,
            "days_remaining": profile.trial_days_remaining() if trial_active else None
        }

        return Response(response_data)
