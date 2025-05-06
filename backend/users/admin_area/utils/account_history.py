from users.admin_area.models import AccountHistory
from core.models import CustomUser

def log_account_event(
    email,
    event_type,
    plan_name=None,
    stripe_customer_id=None,
    stripe_subscription_id=None,
    subscription_start=None,
    subscription_end=None,
    cancelled_at=None,
    reactivated_on=None
):
    user = CustomUser.objects.filter(email=email).first()
    if not user:
        # We log the email, but use NULL for user if not registered yet
        print(f"ℹ️ No user found yet for {email}. Logging email-based entry only.")

    AccountHistory.objects.create(
        user=user,
        event_type=event_type,
        plan_name=plan_name,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        cancelled_at=cancelled_at,
        reactivated_on=reactivated_on,
    )
