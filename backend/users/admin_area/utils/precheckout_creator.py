from django.utils import timezone  # 👉 for timestamp (optional if not passed explicitly)
from users.admin_area.models import PreCheckoutEmail  # 👉 model to store emails before checkout


def log_precheckout_event(email, plan_name):
    """
    Logs a pre-checkout email submission with the selected plan.

    Args:
        email (str): The email entered before Stripe Checkout starts.
        plan_name (str): The selected plan (e.g. 'adminTrial', 'adminMonthly', etc.)

    Returns:
        PreCheckoutEmail object or None if duplicate.
    """

    if not email or not plan_name:
        raise ValueError("Email and plan_name are required to log pre-checkout email.")

    if PreCheckoutEmail.objects.filter(email=email).exists():
        print(f"⚠️ PreCheckoutEmail already exists for: {email}")
        return None

    record = PreCheckoutEmail.objects.create(
        email=email,
        plan_name=plan_name,
        created_at=timezone.now()
    )

    print(f"✅ Logged PreCheckoutEmail for: {email} with plan {plan_name}")
    return record
