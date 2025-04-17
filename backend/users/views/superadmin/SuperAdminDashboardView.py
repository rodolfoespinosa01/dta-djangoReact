from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.models import CustomUser
from adminplans.models import AdminPlan


class SuperAdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'Forbidden'}, status=403)

        all_admins = CustomUser.objects.filter(role='admin', is_active=True)

        trial_admins, monthly_admins, annual_admins = [], [], []
        total_revenue = 0
        projected_monthly_income = 0

        # Pull pricing dynamically from AdminPlan model (in cents)
        try:
            monthly_plan = AdminPlan.objects.get(name='adminMonthly')
            annual_plan = AdminPlan.objects.get(name='adminAnnual')
            monthly_price = monthly_plan.price_cents / 100
            annual_price = annual_plan.price_cents / 100
        except AdminPlan.DoesNotExist:
            monthly_price = 30.00
            annual_price = 300.00
            print("⚠️ Warning: AdminPlan missing. Fallback prices used.")

        for admin in all_admins:
            sub = admin.subscription_status
            if sub == 'admin_trial':
                trial_admins.append(admin.email)
            elif sub == 'admin_monthly':
                monthly_admins.append(admin.email)
                total_revenue += monthly_price
                projected_monthly_income += monthly_price
            elif sub == 'admin_annual':
                annual_admins.append(admin.email)
                total_revenue += annual_price

        return Response({
            'trial_admins': trial_admins,
            'monthly_admins': monthly_admins,
            'annual_admins': annual_admins,
            'total_revenue': f"${total_revenue:.2f}",
            'projected_monthly_income': f"${projected_monthly_income:.2f}",
        })