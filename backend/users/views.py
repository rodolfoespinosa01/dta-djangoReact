from rest_framework_simplejwt.tokens import RefreshToken
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



class AdminLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)

        if user and getattr(user, 'role', '') == 'admin':
            refresh = RefreshToken.for_user(user)

            # Add only relevant admin fields
            refresh['email'] = user.email
            refresh['role'] = user.role

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
                'email': user.email,
                'role': user.role
            })

        return Response({'error': 'Invalid credentials or not an admin'}, status=status.HTTP_401_UNAUTHORIZED)

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

from .serializers import AdminForgotPasswordSerializer, AdminResetPasswordSerializer

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
    
@csrf_exempt
def register_admin(request):
    print("📩 Incoming registration request received")

    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        token = data.get('token')

        print(f"📥 Incoming data: email={email}, password={'✅' if password else '❌'}, token={token}")

        if not all([email, password, token]):
            return JsonResponse({'error': 'Missing fields'}, status=400)

        pending = PendingAdminSignup.objects.get(token=token)
        session_id = pending.session_id

        # 🔄 Expand customer + setup_intent
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer', 'setup_intent']
        )

        # ✅ Handle both expanded object and string customer ID
        customer = checkout_session.get("customer")
        customer_id = customer.id if hasattr(customer, 'id') else customer

        customer_email = checkout_session.get("customer_email")

        if not customer_email and customer_id:
            customer_obj = stripe.Customer.retrieve(customer_id)
            customer_email = customer_obj.get("email")

        plan_name = checkout_session.get('metadata', {}).get('plan_name')
        plan = AdminPlan.objects.get(name=plan_name)

        plan_mapping = {
            'adminTrial': 'admin_trial',
            'adminMonthly': 'admin_monthly',
            'adminAnnual': 'admin_annual',
        }

        subscription_status = plan_mapping.get(plan.name, 'admin_trial')

        # ✅ Create user
        User = get_user_model()
        if User.objects.filter(username=email).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)

        user = User.objects.create_user(username=email, email=email, password=password)
        user.role = 'admin'
        user.is_staff = True
        user.subscription_status = subscription_status
        user.save()

        # ✅ AdminProfile
        profile_data = {
            'admin_stripe_customer_id': customer_id,
        }

        if subscription_status == 'admin_trial':
            profile_data['trial_start_date'] = timezone.now()
        else:
            profile_data['subscription_started_at'] = timezone.now()

        profile, created = AdminProfile.objects.get_or_create(
            user=user,
            defaults=profile_data
        )

        if created:
            print(f"🧾 AdminProfile created for {email}")
        else:
            print(f"⚠️ AdminProfile already existed for {email}")

        # ✅ Attach payment method if setup_intent exists
        if checkout_session.mode == 'setup':
            setup_intent = checkout_session.get('setup_intent')
            if setup_intent and setup_intent.get('payment_method'):
                payment_method = setup_intent['payment_method']
                stripe.PaymentMethod.attach(payment_method, customer=customer_id)
                stripe.Customer.modify(customer_id, invoice_settings={
                    'default_payment_method': payment_method
                })
                print(f"✅ Attached and set default payment method for {email}")
            else:
                print(f"⚠️ No payment method found in setup intent")

        # ✅ Schedule upgrade task for free trials
        if subscription_status == 'admin_trial':
            from adminplans.tasks import auto_upgrade_admin_trial
            auto_upgrade_admin_trial.apply_async((user.id,), countdown=60)  # Use 60*60*24*14 in prod
            print(f"🕒 Trial upgrade scheduled for {email}")

        pending.delete()
        return JsonResponse({'success': True, 'message': f'Admin account created with {subscription_status} plan'})

    except PendingAdminSignup.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)

    except Exception as e:
        print("❌ Error during admin registration:", e)
        return JsonResponse({'error': str(e)}, status=500)


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