from users.admin_area.models import ScheduledSubscription

def create_scheduled_subscription(
    user,
    plan,
    starts_on,
    stripe_subscription_id,
    stripe_transaction_id
):
    return ScheduledSubscription.objects.create(
        user=user,
        plan=plan,
        starts_on=starts_on,
        stripe_subscription_id=stripe_subscription_id,
        stripe_transaction_id=stripe_transaction_id
    )
