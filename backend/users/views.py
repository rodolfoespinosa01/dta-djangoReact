from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from users.models import CustomUser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from adminplans.models import AdminPlan, PendingAdminSignup, AdminProfile
from adminplans.tasks import auto_upgrade_admin_trial
from users.serializers.serializers import CustomTokenObtainPairSerializer
from users.serializers.admin_serializers import AdminForgotPasswordSerializer, AdminResetPasswordSerializer
from dateutil.relativedelta import relativedelta
import json
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

User = get_user_model()

class SuperAdminLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user and user.is_superuser:
            refresh = RefreshToken.for_user(user)

            # Manually add custom claims
            refresh['email'] = user.email
            refresh['role'] = getattr(user, 'role', 'superadmin')
            refresh['is_superuser'] = user.is_superuser

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': refresh['role'],
                'is_superuser': refresh['is_superuser']
            })

        return Response({'error': 'Invalid credentials or not a superadmin'}, status=status.HTTP_401_UNAUTHORIZED)

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



class AdminLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

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
                "redirect_to": "/admintrialended",
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

class AdminForgotPasswordView(APIView):
    def post(self, request):
        serializer = AdminForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset link sent (check terminal)."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminResetPasswordConfirmView(APIView):
    def post(self, request):
        serializer = AdminResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password has been reset successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def get_pending_signup(request, token):
    try:
        pending = PendingAdminSignup.objects.get(token=token)
        return JsonResponse({'email': pending.email})
    except PendingAdminSignup.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)

@csrf_exempt
def login_admin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        user = authenticate(request, username=email, password=password)

        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        if user.role != 'admin':
            return JsonResponse({'error': 'Not an Admin account'}, status=403)

        login(request, user)

        return JsonResponse({'success': True, 'message': 'Logged in as admin'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_admin_trial_auto_renew(request):
    user = request.user
    if user.role != 'admin' or user.subscription_status != 'admin_trial':
        return Response({'error': 'Unauthorized or not a trial admin'}, status=403)

    profile = user.admin_profile
    profile.auto_renew_cancelled = True
    profile.save()

    return Response({'success': True, 'message': 'Auto-renewal cancelled. You will not be charged.'})