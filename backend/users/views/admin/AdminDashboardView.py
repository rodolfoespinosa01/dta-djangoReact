from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
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

        if profile.auto_renew_cancelled:
            user.subscription_status = 'admin_inactive'
            user.save()
            return Response({
                "trial_active": False,
                "redirect_to": "/admin-trial-ended",
                "message": "Your trial was cancelled and will not auto-renew."
            }, status=status.HTTP_403_FORBIDDEN)

        if profile.is_trial_expired():
            user.subscription_status = 'admin_inactive'
            user.save()
            return Response({
                "trial_active": False,
                "redirect_to": "/admintrialended"
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "trial_active": True,
            "days_remaining": profile.trial_days_remaining(),
            "message": f"Welcome back, {user.username}. You have {profile.trial_days_remaining()} day(s) left in your trial."
        })
