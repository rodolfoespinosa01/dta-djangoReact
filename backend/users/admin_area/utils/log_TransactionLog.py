from django.db import IntegrityError, transaction
from users.admin_area.models import TransactionLog

def log_TransactionLog(*, email: str, stripe_transaction_id: str | None, **extra_defaults):
    if not stripe_transaction_id:
        return

    # short‑circuit
    if TransactionLog.objects.filter(stripe_transaction_id=stripe_transaction_id).exists():
        return

    # only include fields that actually exist on TransactionLog
    valid = {f.name for f in TransactionLog._meta.get_fields()}
    defaults = {}
    if "admin_email" in valid:
        defaults["admin_email"] = email
    elif "email" in valid:
        defaults["email"] = email
    for k, v in (extra_defaults or {}).items():
        if k in valid:
            defaults[k] = v

    try:
        with transaction.atomic():
            TransactionLog.objects.get_or_create(
                stripe_transaction_id=stripe_transaction_id,
                defaults=defaults
            )
    except IntegrityError:
        pass
