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
    next_billing=None,
    is_active=None,
    is_canceled=False,
):
    """
    Create a snapshot Profile for the current cycle.

    Rules:
    - Trial: subscription_start is None.
    - Paid users keep access (is_active=True) until subscription_end; trials can be toggled by caller.
    """

    # Normalize trial fields
    if is_trial:
        subscription_start = None



    if is_active is None:
        # Paid users keep access until subscription_end; trials are active by default here
        if is_trial:
            is_active = True
        else:
            # If we already have an end date in the past, turn off; otherwise keep on
            if subscription_end and subscription_end <= timezone.now():
                is_active = False
            else:
                is_active = True

    return Profile.objects.create(
        user=user,
        plan=plan,
        is_active=is_active,
        is_canceled=bool(is_canceled),
        is_trial=is_trial,
        trial_start=trial_start if is_trial else None,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        next_billing=next_billing,
        stripe_transaction_id=stripe_transaction_id,
    )
