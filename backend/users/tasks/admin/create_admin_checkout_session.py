from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.conf import settings
import stripe, json

from users.models import CustomUser
from adminplans.models import AdminPlan, PendingAdminSignup

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_admin_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        plan_name = data.get('plan_name')
        email = data.get('email')

        # 🚫 Check if user already exists and has a completed account
        from users.models import CustomUser
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            if existing_user.subscription_status in ['admin_trial', 'admin_monthly', 'admin_annual', 'admin_inactive']:
                return JsonResponse({
                    'error': 'This email is already associated with an account. Please log in to manage or upgrade your plan.'
                }, status=403)

        # 🚫 Prevent reusing free trial for same email
        if plan_name == 'adminTrial':
            if existing_user and hasattr(existing_user, 'admin_profile'):
                if existing_user.admin_profile.trial_start_date:
                    return JsonResponse({
                        'error': 'This email has already used the free trial. Please choose a paid plan.'
                    }, status=403)

        # 🚫 Block if a pending signup already exists for this email
        from adminplans.models import PendingAdminSignup
        if PendingAdminSignup.objects.filter(email=email, is_used=False).exists():
            return JsonResponse({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=403)

        # ✅ Create Stripe Customer and Checkout Session
        plan = AdminPlan.objects.get(name=plan_name)
        customer = stripe.Customer.create(email=email)

        if plan.name == 'adminTrial':
            session = stripe.checkout.Session.create(
                mode='setup',
                payment_method_types=['card'],
                customer=customer.id,
                metadata={'plan_name': plan.name},
                success_url='http://localhost:3000/admin-thank-you?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:3000/admin-plans',
            )
        else:
            session = stripe.checkout.Session.create(
                mode='subscription',
                payment_method_types=['card'],
                customer=customer.id,
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                metadata={'plan_name': plan.name},
                success_url='http://localhost:3000/admin-thank-you?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:3000/admin-plans',
            )

        return JsonResponse({'url': session.url})

    except AdminPlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return JsonResponse({'error': str(e)}, status=500)