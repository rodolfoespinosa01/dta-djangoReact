from users.admin_area.models import AccountHistory  # 👉 imports the model that stores lifecycle event logs
from django.utils import timezone  # 👉 used to timestamp payment events when not explicitly provided

# 👉 logs a user lifecycle event to the accounthistory table
# 👉 accepts either a user instance (post-registration) or an email (pre-registration)
# 👉 tracks events like signup, cancel, reactivation, or stripe payment
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
    Logs a user lifecycle event to the AccountHistory model.

    Accepts either a user instance (post-registration) or an email (pre-registration)
    and records key subscription or billing events such as signup, cancel, reactivation,
    or Stripe payment.

    Args:
        event_type (str): Type of the event (e.g., 'signup', 'cancel', etc.).
        plan_name (str): Name of the associated plan.
        email (str, optional): User's email if no user instance is available.
        user (CustomUser, optional): The user object.
        stripe_customer_id (str, optional): Stripe customer ID.
        stripe_subscription_id (str, optional): Stripe subscription ID.
        subscription_start (datetime, optional): Subscription start date.
        subscription_end (datetime, optional): Subscription end date.
        cancelled_at (datetime, optional): Time of cancellation.
        reactivated_on (datetime, optional): Time of reactivation.
        payment_processed_on (datetime, optional): Time payment was processed.
        stripe_transaction_id (str, optional): Stripe transaction/charge ID.
    """


    resolved_email = email or (user.email if user and hasattr(user, "email") else None)  
    # 👉 resolves the email from provided argument or user instance

    if not resolved_email:
        raise ValueError("You must provide either a user with email or an email string.")
    # 👉 prevents logging if no email is available


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
    # 👆 prepares all the fields to be recorded in the accounthistory table

    AccountHistory.objects.create(**history_data)
    # 👆 creates a new accounthistory record with all relevant info


# 👉 summary:
# central logging utility for all admin subscription lifecycle events.
# captures signups, cancellations, reactivations, and stripe payments tied to either an email or user.
# ensures consistent and centralized tracking of billing history across the platform.