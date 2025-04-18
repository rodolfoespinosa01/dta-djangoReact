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
        plan_name = data.get('plan_name')  # 'adminTrial', 'adminMonthly', etc.
        email = data.get('email')

        # 🚫 Block existing users with active or past plans
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            if existing_user.subscription_status in ['admin_trial', 'admin_monthly', 'admin_annual', 'admin_inactive']:
                return JsonResponse({
                    'error': 'This email is already associated with an account. Please log in to manage or upgrade your plan.'
                }, status=403)

        # 🚫 Prevent reuse of free trial
        if plan_name == 'adminTrial':
            if existing_user and hasattr(existing_user, 'admin_profile'):
                if existing_user.admin_profile.trial_start_date:
                    return JsonResponse({
                        'error': 'This email has already used the free trial. Please choose a paid plan.'
                    }, status=403)

        # 🚫 Prevent duplicate pending signups
        if PendingAdminSignup.objects.filter(email=email, is_used=False).exists():
            return JsonResponse({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=403)

        # ✅ Use adminMonthly plan for trial logic
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name
        plan = AdminPlan.objects.get(name=actual_plan_name)

        # ✅ Create Stripe Customer
        customer = stripe.Customer.create(email=email)

        # ✅ Setup base session params
        session_params = {
            'mode': 'subscription',
            'payment_method_types': ['card'],
            'customer': customer.id,
            'line_items': [{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            'metadata': {
                'plan_name': plan_name  # this is important for webhook to know if it was a trial
            },
            'success_url': 'http://localhost:3000/admin-thank-you?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': 'http://localhost:3000/admin-plans',
        }

        # ⏳ Add 14-day trial if it's the trial plan
        if plan_name == 'adminTrial':
            session_params['subscription_data'] = {
                'trial_period_days': 14
            }

        # ✅ Create Checkout Session
        session = stripe.checkout.Session.create(**session_params)

        return JsonResponse({'url': session.url})

    except AdminPlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return JsonResponse({'error': str(e)}, status=500)
