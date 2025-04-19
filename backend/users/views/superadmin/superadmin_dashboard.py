from datetime import timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def superadmin_dashboard(request):
    admins = CustomUser.objects.filter(role='admin').select_related('admin_profile')
    admin_data = []

    for admin in admins:
        profile = getattr(admin, 'admin_profile', None)

        if not profile:
            continue

        
        plan_code = admin.subscription_status

        # Dynamically calculate next billing for trial
        if plan_code == 'admin_trial' and profile.trial_start_date:
            next_billing = profile.trial_start_date + timedelta(days=14)
        else:
            next_billing = profile.next_billing_date

        price_dollars = "N/A"

        try:
            # Map the DB plan_code to AdminPlan name
            plan_lookup = {
                'admin_monthly': 'adminMonthly',
                'admin_quarterly': 'adminQuarterly',
                'admin_annual': 'adminAnnual'
            }

            plan_obj = AdminPlan.objects.get(name=plan_lookup.get(plan_code, 'adminMonthly'))
            price_dollars = f"${plan_obj.price_dollars():.2f}"

        except AdminPlan.DoesNotExist:
            price_dollars = "Unknown"

        admin_data.append({
            "email": admin.email,
            "plan": plan_code,
            "price": price_dollars,
            "next_billing_date": next_billing.strftime('%Y-%m-%d') if next_billing else "N/A"
        })

    return JsonResponse({"admins": admin_data})
