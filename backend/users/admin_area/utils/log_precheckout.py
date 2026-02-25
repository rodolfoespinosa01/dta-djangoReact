from django.utils import timezone
from users.admin_area.models import PreCheckout, AdminIdentity

def log_PreCheckout(email, plan_name, is_trial=False):
    """
    Logs a pre-checkout event by associating the admin via AdminIdentity.
    
    Args:
        email (str): The email entered before Stripe Checkout starts.
        plan_name (str): The selected plan (e.g. 'adminTrial', 'adminMonthly', etc.)
        is_trial (bool): Whether this is a trial checkout or a direct purchase.

    Returns:
        PreCheckout object or None if duplicate.
    """

    # ✅ Fetch or create AdminIdentity for this email
    admin, _ = AdminIdentity.objects.get_or_create(admin_email=email)

    # ✅ Upsert latest pre-checkout state so retries don't keep stale/empty plan values.
    record = PreCheckout.objects.filter(admin=admin).order_by('-created_at').first()
    if record:
        record.plan_name = plan_name
        record.is_trial = is_trial
        record.save(update_fields=['plan_name', 'is_trial'])
        print(f"♻️ Updated PreCheckout for: {email} | plan: {plan_name} | trial: {is_trial}")
        return record

    record = PreCheckout.objects.create(
        admin=admin,
        plan_name=plan_name,
        is_trial=is_trial,
        created_at=timezone.now()
    )

    print(f"✅ Logged PreCheckout for: {email} | plan: {plan_name} | trial: {is_trial}")
    return record
