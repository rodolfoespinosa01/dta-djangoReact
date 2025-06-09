# users/utils/history_creator.py

from django.utils import timezone
from users.admin_area.models import AccountHistory
from django.contrib.auth import get_user_model

User = get_user_model()


def log_history_event(
    email,
    event_type,
    plan_name,
    is_trial=False,
    stripe_transaction_id=None,
    notes=None
):
    """
    Logs an account lifecycle event for an admin user.

    Args:
        email (str): Email of the admin user.
        event_type (str): Type of event (e.g. 'trial_monthly_start', 'cancel', 'reactivation').
        plan_name (str): The Stripe plan name ('adminMonthly', etc.).
        is_trial (bool): Whether this event was part of a free trial.
        stripe_transaction_id (str): Stripe invoice or session ID.
        stripe_subscription_id (str): Stripe subscription ID.
        notes (str): Optional notes.

    Returns:
        AccountHistory object.
    """

    user = User.objects.filter(email=email).first()

    if not user:
        print(f"⚠️ Could not find user with email: {email}")
        return None

    history = AccountHistory.objects.create(
        user=user,
        event_type=event_type,
        plan_name=plan_name,
        is_trial=is_trial,
        stripe_transaction_id=stripe_transaction_id,
        stripe_subscription_id=stripe_subscription_id,
        timestamp=timezone.now(),
        notes=notes
    )

    print(f"✅ Logged {event_type} for {email}")
    return history
