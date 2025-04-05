from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.conf import settings
from adminplans.models import AdminPlan
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

        # 🧠 Pull pricing dynamically from AdminPlan model (in cents)
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "message": f"Welcome, {user.email}!",
            "role": user.role,
            "subscription_status": user.subscription_status
        })
    
    
@csrf_exempt
def register_admin(request):
    print("📩 Incoming registration request received")
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        session_id = data.get('session_id')

        if not all([email, password, session_id]):
            return JsonResponse({'error': 'Missing fields'}, status=400)

        # ✅ Step 1: Retrieve Stripe session
        try:
            print("📦 Attempting to fetch Stripe session...")

            checkout_session = stripe.checkout.Session.retrieve(session_id)
            print("✅ Stripe session:", checkout_session)

            line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
            print("✅ Line items:", line_items)

            stripe_price_id = line_items.data[0].price.id
            print("✅ Stripe price ID:", stripe_price_id)

        except Exception as stripe_error:
            print("❌ Final error handler hit:", str(e))
            return JsonResponse({'error': 'Stripe session retrieval failed'}, status=400)

        # ✅ Step 2: Match Stripe price ID to AdminPlan
        try:
            plan = AdminPlan.objects.get(stripe_price_id=stripe_price_id)
            print("✅ Matched AdminPlan:", plan.name)

            plan_mapping = {
                'adminTrial': 'admin_trial',
                'adminMonthly': 'admin_monthly',
                'adminAnnual': 'admin_annual',
            }

            subscription_status = plan_mapping.get(plan.name, 'trial')

        except AdminPlan.DoesNotExist:
            print("❌ Plan not found for price_id:", stripe_price_id)
            subscription_status = 'trial'

        # ✅ Step 3: Create user
        User = get_user_model()
        if User.objects.filter(username=email).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)

        user = User.objects.create_user(username=email, email=email, password=password)
        user.role = 'admin'
        user.is_staff = True
        user.subscription_status = plan_mapping.get(plan.name, 'admin_trial')
        user.save()

        print(f"✅ Admin {email} created with subscription_status: {subscription_status}")
        return JsonResponse({'success': True, 'message': f'Admin account created with {subscription_status} plan'})

    except Exception as e:
        print("❌ Error during admin registration:", e)
        return JsonResponse({'error': str(e)}, status=500)


