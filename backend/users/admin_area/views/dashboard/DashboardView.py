from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils.timezone import now

from users.admin_area.models import Profile

class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 🔒 only admins
        if getattr(user, "role", None) != "admin":
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        # 📦 active profile (authoritative for billing flags)
        try:
            profile = user.profiles.get(is_active=True)
        except Profile.DoesNotExist:
            return Response({"error": "Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

        now_ts = now()

        # Prefer profile-held status if available
        subscription_status = getattr(profile, "subscription_status", None) or getattr(user, "subscription_status", "")
        is_trial = (subscription_status == "admin_trial") or bool(getattr(profile, "is_trial", False))
        is_canceled = bool(getattr(profile, "is_canceled", False))
        cancel_at_period_end = bool(getattr(profile, "cancel_at_period_end", False))
        auto_renew = bool(getattr(profile, "auto_renew", True))

        period_end = getattr(profile, "subscription_end", None)
        next_billing = getattr(profile, "next_billing", None)

        # ----- Access rules -----
        expired = bool(period_end and period_end <= now_ts)

        # Trial: cancel = immediate lockout; expired trial = lockout
        trial_inactive = is_trial and (is_canceled or expired)

        # Paid: only inactive when actually expired; cancel alone does NOT remove access
        paid_inactive = (not is_trial) and expired

        inactive = trial_inactive or paid_inactive
        is_active = not inactive

        # What the FE should treat as "billing active" (has access to app)
        subscription_active = is_active

        # next_billing shown only if still renewing
        effective_next_billing = None if is_canceled else (next_billing if is_active else None)

        # Map start date field by plan (if you store only one start, reuse it)
        start_dt = getattr(profile, "subscription_start", None)
        start_dates = {
            "admin_trial": start_dt if subscription_status == "admin_trial" else None,
            "admin_monthly": start_dt if subscription_status == "admin_monthly" else None,
            "admin_quarterly": start_dt if subscription_status == "admin_quarterly" else None,
            "admin_annual": start_dt if subscription_status == "admin_annual" else None,
        }

        # Trial days remaining (non-negative)
        days_remaining = None
        if is_trial and period_end:
            delta_days = (period_end - now_ts).days
            days_remaining = max(delta_days, 0)

        payload = {
            "subscription_status": subscription_status,
            "subscription_active": subscription_active,  # ← FE uses this
            "is_active": is_active,                      # ← keep for your banners
            "is_canceled": is_canceled,
            "cancel_at_period_end": cancel_at_period_end,
            "subscription_end": period_end,
            "next_billing": effective_next_billing,
            "is_trial": is_trial and is_active,
            "days_remaining": days_remaining,
            "trial_start": start_dates["admin_trial"],
            "monthly_start": start_dates["admin_monthly"],
            "quarterly_start": start_dates["admin_quarterly"],
            "annual_start": start_dates["admin_annual"],
            "auto_renew": auto_renew,
        }

        # 👉 Return 403 only when the user truly has no access
        if not is_active:
            return Response(payload, status=status.HTTP_403_FORBIDDEN)

        return Response(payload, status=status.HTTP_200_OK)
