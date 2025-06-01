from users.admin_area.models import TransactionLog  # 👉 imports the model that stores Stripe transaction logs
from django.utils import timezone  # 👉 used to timestamp payment events when not explicitly provided


# 👉 logs a Stripe payment transaction to the TransactionLog table
# 👉 requires the user's email and Stripe transaction ID (PaymentIntent)
# 👉 optionally accepts a timestamp override (default = now)
def log_transaction_event(
    email,
    stripe_transaction_id,
    timestamp=None,
):
    """
    Logs a Stripe payment transaction to the TransactionLog model.

    Args:
        email (str): The email associated with the Stripe Checkout.
        stripe_transaction_id (str): Unique Stripe PaymentIntent ID.
        timestamp (datetime, optional): Time the transaction occurred. Defaults to now.
    """

    if not email:
        raise ValueError("Email is required to log a transaction event.")  # 👉 ensures email is always provided

    if not stripe_transaction_id:
        raise ValueError("Stripe transaction ID is required to log a transaction event.")  # 👉 ensures a valid ID

    log_data = {
        'email': email,
        'stripe_transaction_id': stripe_transaction_id,
        'created_at': timestamp or timezone.now(),  # 👉 sets created_at to now unless explicitly overridden
    }

    TransactionLog.objects.create(**log_data)  # 👉 saves a new transaction log entry


# 👉 summary:
# Simple and scalable utility to capture Stripe payments in the TransactionLog.
# Ensures email + transaction_id are required and supports timestamp override.
# Keeps the logic clean and parallel to AccountHistory lifecycle tracking.
