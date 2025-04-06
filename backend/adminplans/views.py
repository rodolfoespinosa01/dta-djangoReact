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
        plan = AdminPlan.objects.get(name=plan_name)
        email = data.get('email')

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            customer_email=email,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            success_url='http://localhost:3000/adminthankyou',

            cancel_url='https://localhost:3000/cancel',
        )

        return JsonResponse({'url': session.url})

    except AdminPlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
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
        customer_email = session.get('customer_email')
        session_id = session.get('id')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email from session: {customer_email}")

        try:
            line_items = stripe.checkout.Session.list_line_items(
                session_id,
                expand=['data.price'],
                limit=1
            )
            price_id = line_items.data[0].price.id
            print(f"📦 Price ID from session: {price_id}")
        except Exception as e:
            print(f"❌ Error fetching line_items: {str(e)}")
            return HttpResponse(status=500)

        try:
            plan = AdminPlan.objects.get(stripe_price_id=price_id)
            plan_name = plan.name
        except AdminPlan.DoesNotExist:
            print("❌ No AdminPlan matched price ID")
            return HttpResponse(status=500)

        try:
            PendingAdminSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=plan_name
            )
            print(f"✅ PendingAdminSignup created for {customer_email}")

            # Simulated email logging
            registration_link = f"http://localhost:3000/adminregister?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email (simulated):")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print("Body:")
            print("Thanks for your payment!")
            print(f"➡️  Click here to complete registration:\n{registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error saving PendingAdminSignup: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)



