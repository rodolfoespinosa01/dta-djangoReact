from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import stripe
import json
from django.conf import settings
from .models import AdminPlan
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        plan_name = data.get('plan_name')
        plan = AdminPlan.objects.get(name=plan_name)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            success_url='http://localhost:3000/adminregister?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/cancel',
        )

        return JsonResponse({'url': session.url})

    except AdminPlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
User = get_user_model()
@csrf_exempt
def register_admin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        session_id = data.get('session_id')

        if not all([email, password, session_id]):
            return JsonResponse({'error': 'Missing fields'}, status=400)

        # Check if user already exists
        if User.objects.filter(username=email).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)

        # Create user using custom user model
        user = User.objects.create_user(username=email, email=email, password=password)
        user.is_staff = True
        user.role = 'admin'  # ✅ Explicitly set admin role
        user.subscription_status = 'trial'  # Optional: Set default plan
        user.save()

        return JsonResponse({'success': True, 'message': 'Admin account created'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
