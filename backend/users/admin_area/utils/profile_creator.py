from users.admin_area.models import Profile  # 👉 imports the profile model used to track subscription history
from django.utils import timezone  # 👉 used for date handling (not used directly here but good for future logic)


def deactivate_previous_profiles(user):
    # 👉 sets all current profiles for this user to not current
    # 👉 ensures only one profile has is_current = true at any time
    Profile.objects.filter(user=user, is_current=True).update(is_current=False)



def create_profile_with_stripe_data(
    user,
    plan,
    subscription_id,
    transaction_id,
    subscription_start,
    subscription_end,
    next_billing_date
):
    # 👉 deactivates any previous current profiles before creating a new one
    deactivate_previous_profiles(user)

    # 👉 creates a new profile snapshot representing this subscription period
    return Profile.objects.create(
        user=user,
        plan=plan,
        is_active=True,
        is_canceled=False,
        is_current=True,
        subscription_start_date=subscription_start,
        subscription_end_date=subscription_end,
        stripe_subscription_id=subscription_id,
        stripe_transaction_id=transaction_id,
        next_billing_date=next_billing_date,
    )


# 👉 summary:
# creates a fresh subscription profile for a user after stripe checkout.
# ensures previous profiles are marked as inactive, keeping only one marked as current.
# used for tracking billing state, plan history, and controlling dashboard access.