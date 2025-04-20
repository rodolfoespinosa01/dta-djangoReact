from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils.timezone import now
from adminplans.models import AdminProfile


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

        # ❌ Block access if subscription has ended
        if profile.is_canceled and profile.subscription_end_date and profile.subscription_end_date < now():
            return Response({
                "error": "Your subscription has ended. Please reactivate to access the dashboard."
            }, status=status.HTTP_403_FORBIDDEN)

        subscription_status = user.subscription_status
        is_canceled = profile.is_canceled
        is_active = not is_canceled
        trial_days_left = profile.trial_days_remaining()
        is_trial = trial_days_left > 0 if trial_days_left is not None else False

        # Assign start dates
        monthly_start = profile.subscription_started_at if subscription_status == 'adminMonthly' else None
        quarterly_start = profile.subscription_started_at if subscription_status == 'adminQuarterly' else None
        annual_start = profile.subscription_started_at if subscription_status == 'adminAnnual' else None

        response_data = {
            "subscription_status": subscription_status,
            "subscription_active": is_active,
            "is_canceled": is_canceled,
            "canceled_at": profile.canceled_at,
            "subscription_end_date": profile.subscription_end_date,
            "trial_start": profile.trial_start_date,
            "is_trial": is_trial,
            "days_remaining": trial_days_left if is_trial else None,
            "monthly_start": monthly_start,
            "quarterly_start": quarterly_start,
            "annual_start": annual_start,
            "next_billing_date": profile.next_billing_date if is_active else None
        }

        return Response(response_data)
