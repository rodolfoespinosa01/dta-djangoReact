from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils.timezone import now
from users.admin_area.models import AdminProfile

class AdminDashboardView(APIView):
    # Only authenticated users can access this view
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Must be an admin to proceed
        if user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        # Try to get the current AdminProfile (active subscription cycle)
        try:
            profile = user.admin_profile
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

<<<<<<<< HEAD:backend/adminplans/views/admin_dashboard.py
        # ❌ If subscription is fully canceled and period has ended, block access
        if profile.is_canceled and profile.subscription_end_date and profile.subscription_end_date < now():
            return Response({
                "error": "Your subscription has ended.",
                "redirect_to": "/admin_reactivate"  # Frontend will redirect to reactivation options
            }, status=status.HTTP_403_FORBIDDEN)
========
        # ✅ Check if subscription has truly ended
        inactive = False
        if profile.is_canceled and profile.subscription_end_date and profile.subscription_end_date < now():
            inactive = True
>>>>>>>> admin-reactivation-debug:backend/users/admin_area/views/admin_dashboard.py

        # Status flags for use in UI
        subscription_status = user.subscription_status
        is_canceled = profile.is_canceled
<<<<<<<< HEAD:backend/adminplans/views/admin_dashboard.py
        is_active = not is_canceled

        # Trial logic
========
        is_active = not inactive 
>>>>>>>> admin-reactivation-debug:backend/users/admin_area/views/admin_dashboard.py
        trial_days_left = profile.trial_days_remaining()
        is_trial = trial_days_left > 0 if trial_days_left is not None else False

        # Assign plan-specific start dates (for frontend display or analytics)
        monthly_start = profile.subscription_started_at if subscription_status == 'admin_monthly' else None
        quarterly_start = profile.subscription_started_at if subscription_status == 'admin_quarterly' else None
        annual_start = profile.subscription_started_at if subscription_status == 'admin_annual' else None

        # Prepare response payload
        response_data = {
            "subscription_status": subscription_status,
            "subscription_active": is_active,
            "is_canceled": is_canceled,
            "inactive": inactive,
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
