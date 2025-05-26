from users.admin_area.models import ScheduledSubscription  # 👉 imports the model used to store future plan activations


def create_scheduled_subscription(
    user,
    plan,
    starts_on,
    stripe_subscription_id,
    stripe_transaction_id
):
    # 👉 creates a record of a plan that should start at a future date
    return ScheduledSubscription.objects.create(
        user=user,
        plan=plan,
        starts_on=starts_on,
        stripe_subscription_id=stripe_subscription_id,
        stripe_transaction_id=stripe_transaction_id
    )


# 👉 summary:
# stores a future-dated subscription upgrade or reactivation for a user.
# used when a new plan should begin after the current billing cycle ends.
# supports seamless transitions between plans without interrupting current access.