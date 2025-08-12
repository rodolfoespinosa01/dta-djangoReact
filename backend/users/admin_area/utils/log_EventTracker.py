from users.admin_area.models import AdminIdentity, PreCheckout, PendingSignup, EventTracker
from core.models import CustomUser

def log_EventTracker(admin_email, event_type, details=None):
    print(f"\n⚙️ Attempting to log event for: {admin_email}")

    # Check if user already exists or has an admin identity
    is_existing_user = CustomUser.objects.filter(email=admin_email).exists()
    has_identity = AdminIdentity.objects.filter(admin_email=admin_email).exists()

    if is_existing_user or has_identity:
        try:
            admin = AdminIdentity.objects.get(admin_email=admin_email)
            print("✅ Using existing AdminIdentity")
        except AdminIdentity.DoesNotExist:
            print("❌ User exists but AdminIdentity missing — not creating one")
            return
    else:
        # ✅ This is the one allowed moment to create it
        admin = AdminIdentity.objects.create(admin_email=admin_email)
        print("🆕 AdminIdentity created")

    # ✅ Log the event
    EventTracker.objects.create(
        admin=admin,
        event_type=event_type,
        details=details
    )
    print(f"📝 Event logged: {event_type} — {details}\n")
