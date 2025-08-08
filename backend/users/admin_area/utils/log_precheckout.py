from django.utils import timezone
from users.admin_area.models import PreCheckoutEmail, AdminIdentity

def log_precheckout(email, plan_name, is_trial=False):
    """
    Logs a pre-checkout event by associating the admin via AdminIdentity.
    
    Args:
        email (str): The email entered before Stripe Checkout starts.
        plan_name (str): The selected plan (e.g. 'adminTrial', 'adminMonthly', etc.)
        is_trial (bool): Whether this is a trial checkout or a direct purchase.

    Returns:
        PreCheckoutEmail object or None if duplicate.
    """

    # ✅ Fetch or create AdminIdentity for this email
    admin, _ = AdminIdentity.objects.get_or_create(admin_email=email)

    # ✅ Prevent duplicate PreCheckout entries
    if PreCheckoutEmail.objects.filter(admin=admin).exists():
        print(f"⚠️ PreCheckoutEmail already exists for: {email}")
        return None

    # ✅ Log new pre-checkout event
    record = PreCheckoutEmail.objects.create(
        admin=admin,
        plan_name=plan_name,
        is_trial=is_trial,
        created_at=timezone.now()
    )

    print(f"✅ Logged PreCheckoutEmail for: {email} | plan: {plan_name} | trial: {is_trial}")
    return record
