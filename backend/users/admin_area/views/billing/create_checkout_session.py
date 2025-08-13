import time
import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import CustomUser
from users.admin_area.models import Plan, PendingSignup, PreCheckout, EventTracker, AdminIdentity
from users.admin_area.utils import log_PreCheckout
from users.admin_area.utils.log_EventTracker import log_EventTracker

stripe.api_key = settings.STRIPE_SECRET_KEY

# Alias map so callers can use snake_case or your canonical names
PLAN_NAME_ALIASES = {
    "admin_monthly": "adminMonthly",
    "admin_quarterly": "adminQuarterly",
    "admin_annual": "adminAnnual",
}


@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    """
    Body (JSON):
    {
      "plan_name": "admin_monthly" | "admin_quarterly" | "admin_annual" | canonical names,
      "email": "someone@example.com",
      "is_trial": true|false,
      // DEV helpers (optional):
      "use_test_clock": true|false,
      "trial_seconds": 120
    }
    """
    try:
        data = request.data
        raw_plan_name = (data.get('plan_name') or '').strip()
        plan_name = PLAN_NAME_ALIASES.get(raw_plan_name, raw_plan_name)  # normalize
        email = (data.get('email') or '').strip().lower()
        is_trial = bool(data.get('is_trial', False))

        # DEV helpers
        use_test_clock = bool(data.get('use_test_clock', False))
        trial_seconds = data.get('trial_seconds')
        trial_seconds = int(trial_seconds) if str(trial_seconds).isdigit() else 0

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
        log_PreCheckout(email=email, plan_name=plan_name, is_trial=is_trial)

        # ✅ Ensure AdminIdentity exists and get its UUID (our canonical link to this admin)
        admin_identity, _ = AdminIdentity.objects.get_or_create(admin_email=email)
        admin_id = str(admin_identity.adminID)

        # ✅ Log admin event
        log_EventTracker(
            admin_email=email,
            event_type="stripe_checkout_created",
            details=f"plan_name={plan_name}, is_trial={is_trial}"
        )

        # ✅ Load plan
        plan = Plan.objects.get(name=plan_name)

        # ✅ Find or create Stripe Customer (prefer search by admin_id, fallback by email)
        customer = None
        try:
            # Requires Stripe Search API (enabled by default on most accounts)
            res = stripe.Customer.search(query=f"metadata['admin_id']:'{admin_id}'", limit=1)
            if res and res.data:
                customer = res.data[0]
        except Exception:
            pass
        if not customer:
            try:
                res = stripe.Customer.list(email=email, limit=1)
                if res and res.data:
                    customer = res.data[0]
            except Exception:
                pass

        clock_id = None
        if customer:
            # keep metadata fresh
            try:
                stripe.Customer.modify(
                    customer.id,
                    email=email,
                    **({"test_clock": clock_id} if clock_id else {}),
                    metadata={"admin_id": admin_id, "admin_email": email}
                )
            except Exception:
                pass
        else:
            # Create new customer; attach test clock in DEV if requested
            if use_test_clock and getattr(settings, 'DEBUG', False):
                clock = stripe.test_helpers.TestClock.create(frozen_time=int(time.time()))
                clock_id = clock.id
                customer = stripe.Customer.create(
                    email=email,
                    test_clock=clock_id,
                    metadata={"admin_id": admin_id, "admin_email": email}
                )
            else:
                customer = stripe.Customer.create(
                    email=email,
                    metadata={"admin_id": admin_id, "admin_email": email}
                )

        # ✅ Build subscription_data
        # Mark as NON-reactivation so the unified webhook routes this to the "new purchase" path.
        subscription_data = {
            'metadata': {
                'admin_id': admin_id,
                'admin_email': email,
                'plan_name': plan_name,
                'is_trial': 'true' if is_trial else 'false',
                'reactivation': '0',
            }
        }
        # Use explicit trial_end for short-trial testing, else trial_period_days for normal trial
        if is_trial:
            if trial_seconds > 0:
                subscription_data['trial_end'] = int(time.time()) + trial_seconds
            else:
                subscription_data['trial_period_days'] = 14

        # ✅ Create Checkout Session
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            allow_promotion_codes=True,
            customer=customer.id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            subscription_data=subscription_data,
            # Session-level metadata mirrors intent; also mark non-reactivation
            metadata={
                'admin_id': admin_id,
                'admin_email': email,
                'plan_name': plan_name,
                'is_trial': 'true' if is_trial else 'false',
                'reactivation': '0',  # not a reactivation flow
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        resp = {'url': session.url}
        if clock_id:
            resp['test_clock_id'] = clock_id

        return Response(resp, status=200)

    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=500)
