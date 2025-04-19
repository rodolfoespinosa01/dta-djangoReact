from datetime import timedelta
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def superadmin_dashboard(request):
    user = request.user

    if not user.is_superuser:
        return Response({'error': 'Unauthorized'}, status=403)

    admins = CustomUser.objects.filter(role='admin').select_related('admin_profile')
    admin_data = []

    for admin in admins:
        profile = getattr(admin, 'admin_profile', None)
        if not profile:
            continue

        plan_code = admin.subscription_status

        if plan_code == 'admin_inactive':
            next_billing = None
            price_dollars = ""
        else:
            if plan_code == 'admin_trial' and profile.trial_start_date:
                next_billing = profile.trial_start_date + timedelta(days=14)
            else:
                next_billing = profile.next_billing_date

            try:
                plan_lookup = {
                    'admin_trial': 'adminMonthly',
                    'admin_monthly': 'adminMonthly',
                    'admin_quarterly': 'adminQuarterly',
                    'admin_annual': 'adminAnnual',
                }
                plan_obj = AdminPlan.objects.get(name=plan_lookup.get(plan_code))
                price_dollars = f"${plan_obj.price_dollars():.2f}"
            except AdminPlan.DoesNotExist:
                price_dollars = "Unknown"

        admin_data.append({
            "email": admin.email,
            "plan": plan_code,
            "price": price_dollars,
            "next_billing_date": next_billing.strftime('%Y-%m-%d') if next_billing else "",
            "cancelled": profile.auto_renew_cancelled if plan_code == 'admin_trial' else False
        })

    return JsonResponse({"admins": admin_data})
