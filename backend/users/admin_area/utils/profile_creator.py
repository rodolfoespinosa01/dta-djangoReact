# users/admin_area/utils/profile_creator.py

from users.admin_area.models import Profile

def log_profile_event(
    user,
    plan,
    stripe_transaction_id,
    subscription_start,
    subscription_end,
    next_billing
):
    """
    Logs a new profile snapshot representing the user's current subscription cycle.

    Args:
        user (CustomUser): The user tied to the subscription.
        plan (Plan): The selected subscription plan object.
        subscription_id (str): Stripe subscription ID.
        transaction_id (str): Stripe payment intent or charge ID.
        subscription_start (datetime): Start date of this billing period.
        subscription_end (datetime or None): End date (null if still active).
        next_billing (datetime): Next scheduled billing date.

    Returns:
        Profile: The newly created Profile instance.
    """
    return Profile.objects.create(
        user=user,
        plan=plan,
        is_active=True,
        is_canceled=False,
        is_current=True,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        stripe_transaction_id=stripe_transaction_id,
        next_billing=next_billing,
    )
