from django.db.models.signals import post_save
from django.dispatch import receiver

from users.admin_area.models import EventTracker, AdminAccountHistory


@receiver(post_save, sender=EventTracker)
def mirror_event_to_admin_account_history(sender, instance, created, **kwargs):
    if not created:
        return

    AdminAccountHistory.objects.get_or_create(
        source_event=instance,
        defaults={
            "admin": instance.admin,
            "event_type": instance.event_type,
            "details": instance.details,
            "metadata": {"source": "event_tracker"},
        },
    )
