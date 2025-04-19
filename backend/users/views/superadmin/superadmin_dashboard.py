from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.models.custom_user import CustomUser
from adminplans.models import AdminProfile, AdminPlan

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def superadmin_dashboard(request):
    user = request.user

    if not user.is_superuser:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    admins = CustomUser.objects.filter(role='admin')
    admin_data = []

    for admin in admins:
        profile = getattr(admin, 'admin_profile', None)
        if not profile:
            continue

        # Determine plan type
        status_label = admin.subscription_status
        price = None
        next_billing = None

        if status_label == 'admin_inactive':
            price = ""
            next_billing_str = ""
        elif status_label == 'admin_trial':
            monthly_plan = AdminPlan.objects.filter(name='adminMonthly').first()
            price = monthly_plan.price_dollars() if monthly_plan else "Unknown"
            next_billing = profile.trial_start_date + timedelta(days=14) if profile.trial_start_date else None
            next_billing_str = next_billing.strftime('%Y-%m-%d') if next_billing else ""
        else:
            # Paid plan
            plan_name = status_label.replace('admin_', 'admin').capitalize()
            plan = AdminPlan.objects.filter(name__icontains=plan_name).first()
            price = plan.price_dollars() if plan else "Unknown"
            next_billing_str = profile.next_billing_date.strftime('%Y-%m-%d') if profile.next_billing_date else ""

        admin_data.append({
            "email": admin.email,
            "plan": status_label,
            "price": price,
            "next_billing_date": next_billing_str,
        })

    return Response({
        "admins": admin_data
    }, status=status.HTTP_200_OK)
