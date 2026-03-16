from django.db.models.signals import post_save
from django.dispatch import receiver

from users.admin_area.models import AdminIdentity
from users.admin_area.services.admin_parameter_tables import reset_admin_parameter_payload_to_defaults


@receiver(post_save, sender=AdminIdentity)
def init_admin_parameter_settings(sender, instance, created, **kwargs):
    if not created:
        return

    reset_admin_parameter_payload_to_defaults(instance, version="v1")
