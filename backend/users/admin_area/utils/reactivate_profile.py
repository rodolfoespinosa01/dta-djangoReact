import stripe

from django.utils import timezone
from django.contrib.auth import get_user_model
from users.admin_area.models.profile import Profile
from users.admin_area.models.scheduled_subscription import ScheduledSubscription
from users.admin_area.models.plan import Plan

User = get_user_model()


def handle_admin_reactivation(session):
    subscription_id = session.get("subscription")
    stripe_customer_id = session.get("customer")
    stripe_transaction_id = session.get("payment_intent")

    # Try to get customer_email directly from session
    customer_email = session.get("customer_email")

    # If not available, retrieve from Stripe Customer object
    if not customer_email and stripe_customer_id:
        try:
            stripe_customer = stripe.Customer.retrieve(stripe_customer_id)
            customer_email = stripe_customer.get("email")
            print(f"📧 Fallback email from Stripe Customer: {customer_email}")
        except Exception as e:
            print(f"❌ Failed to retrieve customer from Stripe: {e}")
            customer_email = None

    if not customer_email:
        raise ValueError("Missing customer_email")

    try:
        user = User.objects.get(email=customer_email, role="admin")
    except User.DoesNotExist:
        raise ValueError("User not found for reactivation")

    # Get plan name from metadata
    plan_name = session.get('metadata', {}).get('plan_name')
    if not plan_name:
        raise ValueError("Missing plan_name in metadata")

    try:
        plan = Plan.objects.get(name=plan_name)
    except Plan.DoesNotExist:
        raise ValueError(f"Plan not found: {plan_name}")

    # 🧹 Deactivate all old profiles
    user.profiles.update(is_current=False)

    # ⏳ If scheduled, just update the scheduled record
    scheduled = ScheduledSubscription.objects.filter(
        user=user,
        stripe_subscription_id="pending"
    ).first()

    if scheduled:
        scheduled.stripe_subscription_id = subscription_id
        scheduled.stripe_transaction_id = stripe_transaction_id
        scheduled.save()
        print("⏳ Scheduled reactivation updated")
        return

    # ✅ Otherwise, create new active Profile immediately
    Profile.objects.create(
        user=user,
        plan=plan,
        subscription_start_date=timezone.now(),
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=subscription_id,
        stripe_transaction_id=stripe_transaction_id,
        is_current=True,
        is_canceled=False,
    )

    print(f"✅ Reactivation complete: new profile for {user.email} on plan {plan.name}")
