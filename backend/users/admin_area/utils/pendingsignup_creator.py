from django.utils import timezone  # 👉 used to timestamp the signup creation
from users.admin_area.models import PendingSignup  # 👉 model to store signups post-Stripe payment


# 👉 logs a pending admin signup after Stripe checkout (before registration)
# 👉 requires session ID, email, plan, customer ID, transaction ID, subscription ID
# 👉 generates a secure token for use in the registration URL
def log_pendingsignup_event(
    email,
    token,
    session_id,
    plan_name,
    stripe_transaction_id,
    created_at,
):
    """
    Logs a pending admin signup to the PendingSignup model after Stripe Checkout.

    Args:
        email (str): Email used during Stripe Checkout.
        session_id (str): Stripe Checkout Session ID.
        plan_name (str): Plan selected (e.g. 'adminMonthly').
        stripe_customer_id (str): Stripe customer ID.
        stripe_transaction_id (str): Stripe invoice or payment ID.
        stripe_subscription_id (str): Stripe subscription ID.

    Returns:
        str: The generated token for admin registration.
    """

    if not session_id:
        raise ValueError("Session ID is required to log a pending signup event.")

    if PendingSignup.objects.filter(session_id=session_id).exists():
        print(f"⚠️ PendingSignup already exists for session: {session_id}")
        return None


    signup_data = {
        'email': email,
        'session_id': session_id,
        'token': token,
        'plan': plan_name,
        'stripe_transaction_id': stripe_transaction_id, 
        'created_at': timezone.now(),
    }

    PendingSignup.objects.create(**signup_data)

    print(f"✅ Logged PendingSignup for: {email}")
    return token
