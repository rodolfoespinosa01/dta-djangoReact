# backend/users/tasks/admin/register_admin.py

import json
import stripe
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta
from rest_framework_simplejwt.tokens import RefreshToken

from adminplans.models import AdminPlan
from adminplans.models import AdminProfile, PendingAdminSignup

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

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
        subscription_id = pending.subscription_id

        # 🔄 Expand customer + setup_intent
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer', 'setup_intent']
        )

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

        # ✅ Prepare AdminProfile fields
        profile_data = {
            'admin_stripe_customer_id': customer_id,
            'admin_stripe_subscription_id': subscription_id,
        }

        if subscription_status == 'admin_trial':
            profile_data['trial_start_date'] = timezone.now()
        elif subscription_status == 'admin_monthly':
            subscription_started = timezone.now()
            next_billing = subscription_started + relativedelta(months=1)
            profile_data['subscription_started_at'] = subscription_started
            profile_data['next_billing_date'] = next_billing
            print(f"📅 Monthly next billing date: {next_billing}")
        elif subscription_status == 'admin_annual':
            subscription_started = timezone.now()
            next_billing = subscription_started + relativedelta(months=12)
            profile_data['subscription_started_at'] = subscription_started
            profile_data['next_billing_date'] = next_billing
            print(f"📅 Annual next billing date: {next_billing}")

        profile, created = AdminProfile.objects.get_or_create(user=user, defaults=profile_data)

        if created:
            print(f"🧾 AdminProfile created for {email}")
        else:
            print(f"⚠️ AdminProfile already existed for {email}")

        # ✅ Attach payment method for trial accounts
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

        # ✅ Schedule auto-upgrade task for trials
        if subscription_status == 'admin_trial':
            from users.tasks.admin.auto_upgrade_admin_trial import auto_upgrade_admin_trial
            auto_upgrade_admin_trial.apply_async((user.id,), countdown=45)
            print(f"🕒 Trial upgrade scheduled for {email}")

        pending.delete()

        # ✅ Generate JWT for auto-login
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['role'] = user.role
        refresh['subscription_status'] = user.subscription_status

        return JsonResponse({
            'success': True,
            'message': f'Admin account created with {subscription_status} plan',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'subscription_status': user.subscription_status,
        })

    except PendingAdminSignup.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)

    except Exception as e:
        print("❌ Error during admin registration:", e)
        return JsonResponse({'error': str(e)}, status=500)
