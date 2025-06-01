from django.utils import timezone
from users.admin_area.models import PreCheckoutEmail

def log_precheckout_event(email, plan_name, is_trial=False):
    """
    Logs a pre-checkout email submission with the selected plan.

    Args:
        email (str): The email entered before Stripe Checkout starts.
        plan_name (str): The selected plan (e.g. 'adminTrial', 'adminMonthly', etc.)
        is_trial (bool): Whether this is a trial checkout or a direct purchase.

    Returns:
        PreCheckoutEmail object or None if duplicate.
    """

    if PreCheckoutEmail.objects.filter(email=email).exists():
        print(f"⚠️ PreCheckoutEmail already exists for: {email}")
        return None

    record = PreCheckoutEmail.objects.create(
        email=email,
        plan_name=plan_name,
        is_trial=is_trial,
        created_at=timezone.now()
    )

    print(f"✅ Logged PreCheckoutEmail for: {email} | plan: {plan_name} | trial: {is_trial}")
    return record
