from django.conf import settings
from django.db import models

def message_attachment_upload_path(instance, filename):
    return f"messages/{instance.message.id}/{filename}"

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient} at {self.sent_at}"

class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=message_attachment_upload_path)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=120, blank=True, default="")
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for message {self.message.id}"
