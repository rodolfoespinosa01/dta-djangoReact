from users.admin_area.models import Profile
from django.utils import timezone


def deactivate_previous_profiles(user):
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
    # 🧼 Deactivate any previous current profiles
    deactivate_previous_profiles(user)

    # 🆕 Create a new active subscription snapshot
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