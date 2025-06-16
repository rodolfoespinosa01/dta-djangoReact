from users.admin_area.models import Profile
from django.utils import timezone


def log_profile_event(
    user,
    plan,
    stripe_transaction_id,
    is_trial,
    trial_start=None,
    subscription_start=None,
    subscription_end=None,
    next_billing=None
):

    """
    Logs a new profile snapshot representing the user's current subscription cycle.

    Args:
        user (CustomUser): The user tied to the subscription.
        plan (Plan): The selected subscription plan object.
        stripe_transaction_id (str): Stripe session or invoice ID.
        is_trial (bool): Whether this is a trial cycle.
        subscription_start (datetime or None): When this plan begins (null for trials).
        subscription_end (datetime or None): When it ends (optional).
        next_billing (datetime or None): Next billing date (from Stripe).

    Returns:
        Profile: The newly created Profile instance.
    """

    return Profile.objects.create(
        user=user,
        plan=plan,
        is_active=True,
        is_canceled=False,
        is_current=True,
        is_trial=is_trial,
        trial_start=trial_start if is_trial else None,
        subscription_start=None if is_trial else subscription_start,
        subscription_end=subscription_end,
        next_billing=next_billing,
        stripe_transaction_id=stripe_transaction_id,
    )
