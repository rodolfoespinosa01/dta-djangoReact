from rest_framework import serializers
from core.models import Message, MessageAttachment
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageAttachmentSerializer(serializers.ModelSerializer):
    message_id = serializers.PrimaryKeyRelatedField(source='message', queryset=Message.objects.all(), write_only=True)

    def validate_file(self, value):
        content_type = (getattr(value, 'content_type', '') or '').lower()
        file_name = (getattr(value, 'name', '') or '').lower()
        if content_type != 'application/pdf' and not file_name.endswith('.pdf'):
            raise serializers.ValidationError('Only PDF files are allowed.')
        return value

    class Meta:
        model = MessageAttachment
        fields = ['id', 'message_id', 'file', 'original_filename', 'content_type', 'file_size', 'uploaded_at']

class MessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    sender = serializers.StringRelatedField(read_only=True)
    recipient = serializers.StringRelatedField(read_only=True)
    recipient_id = serializers.PrimaryKeyRelatedField(source='recipient', queryset=User.objects.all(), write_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'recipient_id', 'content', 'sent_at', 'read', 'attachments']
