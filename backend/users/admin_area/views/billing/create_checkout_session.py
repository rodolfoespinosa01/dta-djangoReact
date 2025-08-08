import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import CustomUser
from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail, EventTracker
from users.admin_area.utils import log_precheckout
from users.admin_area.utils.log_admin_event import log_admin_event

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')
        is_trial = data.get('is_trial', False)

        # ✅ Basic validation
        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Prevent duplicate user accounts
        if CustomUser.objects.filter(email=email).exists():
            return Response({'error': 'This email is already associated with an account. Please log in.'}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Prevent multiple pending signups
        if PendingSignup.objects.filter(email=email).exists():
            return Response({'error': 'A registration link has already been generated for this email.'}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Trial logic — block if a previous trial event was logged
        had_trial = EventTracker.objects.filter(
            admin__admin_email=email,
            event_type__startswith='trial_'
        ).exists()

        if is_trial and had_trial:
            return Response({
                'error': 'You have already used a trial. Please choose a paid plan.',
                'redirect': '/admin_reactivate'
            }, status=403)

        # ✅ Log pre-checkout intent
        log_precheckout(email=email, plan_name=plan_name, is_trial=is_trial)

        # ✅ Log admin event (only assigns adminID if new email)
        log_admin_event(
            admin_email=email,
            event_type="stripe_checkout_created",
            details=f"plan_name={plan_name}, is_trial={is_trial}"
        )

        # ✅ Load plan and create Stripe Checkout
        plan = Plan.objects.get(name=plan_name)

        customer = stripe.Customer.create(email=email)

        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer_email=email,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'plan_name': plan_name,
                'is_trial': str(is_trial),
            },
            subscription_data={
                'trial_period_days': 14 if is_trial else None,
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        return Response({'url': session.url}, status=200)

    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=500)
