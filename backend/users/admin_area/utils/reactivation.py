from users.admin_area.models.profile import Profile
from users.admin_area.models.scheduled_subscription import ScheduledSubscription
from django.utils import timezone


def get_current_profile(user):
    return Profile.objects.filter(user=user, is_current=True).first()


def is_mid_cycle_cancellation(profile):
    return (
        profile and
        profile.subscription_end_date and
        profile.subscription_end_date > timezone.now() and
        profile.is_canceled
    )


def schedule_future_subscription(user, plan, start_date, stripe_subscription_id, stripe_transaction_id=None):
    return ScheduledSubscription.objects.create(
        user=user,
        plan=plan,
        starts_on=start_date,
        stripe_subscription_id=stripe_subscription_id,
        stripe_transaction_id=stripe_transaction_id,
    )

def create_scheduled_subscription(user, plan, starts_on, stripe_subscription_id, stripe_transaction_id=None):
    return ScheduledSubscription.objects.create(
        user=user,
        plan=plan,
        starts_on=starts_on,
        stripe_subscription_id=stripe_subscription_id,
        stripe_transaction_id=stripe_transaction_id
    )
