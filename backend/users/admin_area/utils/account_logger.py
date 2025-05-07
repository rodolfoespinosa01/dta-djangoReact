from users.admin_area.models import AccountHistory
from django.utils import timezone

def log_account_event(
    event_type,
    plan_name,
    email=None,
    user=None,
    stripe_customer_id=None,
    stripe_subscription_id=None,
    subscription_start=None,
    subscription_end=None,
    cancelled_at=None,
    reactivated_on=None,
    payment_processed_on=None,
    stripe_transaction_id=None,
):
    """
    Logs lifecycle events to AccountHistory.
    Accepts either a `user` instance (post-registration) or an `email` (pre-registration).
    """

    resolved_email = email or (user.email if user and hasattr(user, "email") else None)

    if not resolved_email:
        raise ValueError("You must provide either a user with email or an email string.")

    history_data = {
        'user': user,
        'email': resolved_email,
        'event_type': event_type,
        'plan_name': plan_name,
        'stripe_customer_id': stripe_customer_id,
        'stripe_subscription_id': stripe_subscription_id,
        'subscription_start': subscription_start,
        'subscription_end': subscription_end,
        'cancelled_at': cancelled_at,
        'reactivated_on': reactivated_on,
        'payment_processed_on': payment_processed_on or (timezone.now() if event_type == 'stripe_payment' else None),
        'stripe_transaction_id': stripe_transaction_id,
    }

    AccountHistory.objects.create(**history_data)
