from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.conf import settings
from django.core.mail import send_mail
import stripe, json

from .models import AdminPlan, PendingAdminSignup

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@csrf_exempt
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    try:
        data = json.loads(request.body)
        plan_name = data.get('plan_name')
        email = data.get('email')

        # 🚫 Prevent reusing free trial for same email
        if plan_name == 'adminTrial':
            from users.models import CustomUser
            existing_user = CustomUser.objects.filter(email=email).first()

            if existing_user:
                if existing_user.subscription_status in ['admin_trial', 'admin_inactive']:
                    if hasattr(existing_user, 'admin_profile') and existing_user.admin_profile.trial_start_date:
                        return JsonResponse({
                            'error': 'This email has already used the free trial. Please choose a paid plan.'
                        }, status=403)

        plan = AdminPlan.objects.get(name=plan_name)
        customer = stripe.Customer.create(email=email)

        if plan.name == 'adminTrial':
            session = stripe.checkout.Session.create(
                mode='setup',
                payment_method_types=['card'],
                customer=customer.id,
                metadata={'plan_name': plan.name},
                success_url='http://localhost:3000/adminthankyou',
                cancel_url='http://localhost:3000/adminplans',
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
                success_url='http://localhost:3000/adminthankyou',
                cancel_url='http://localhost:3000/adminplans',
            )

        return JsonResponse({'url': session.url})

    except AdminPlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
def stripe_webhook(request):
    token = get_random_string(length=64)
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        customer_email = session.get('customer_email')
        subscription_id = session.get('subscription')  # ✅ Extract subscription ID for paid plans

        # Fallback for missing email
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {customer_email}")
        print(f"🧾 Subscription ID: {subscription_id}")

        plan_name = session.get('metadata', {}).get('plan_name')
        if not plan_name:
            print("❌ Missing plan name in session metadata")
            return HttpResponse(status=500)

        try:
            plan = AdminPlan.objects.get(name=plan_name)
        except AdminPlan.DoesNotExist:
            print(f"❌ AdminPlan not found for: {plan_name}")
            return HttpResponse(status=500)

        try:
            PendingAdminSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=plan_name,
                subscription_id=subscription_id  # ✅ Store it here
            )
            print(f"✅ PendingAdminSignup saved for {customer_email}")

            registration_link = f"http://localhost:3000/adminregister?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email (simulated):")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print("Body:")
            print(f"➡️ Click to register:\n{registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error saving PendingAdminSignup: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)
