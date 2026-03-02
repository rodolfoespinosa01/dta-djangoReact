from django.urls import path
from rest_framework.routers import DefaultRouter
from core.views_message import (
	MessageViewSet,
	MessageAttachmentViewSet,
	admin_conversations,
	admin_conversation_messages,
	admin_client_tracking_snapshot,
)

router = DefaultRouter()
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'message-attachments', MessageAttachmentViewSet, basename='messageattachment')

urlpatterns = [
	path('messages/admin/conversations/', admin_conversations, name='admin_conversations'),
	path('messages/admin/conversations/<int:client_id>/', admin_conversation_messages, name='admin_conversation_messages'),
	path('messages/admin/clients/<int:client_id>/tracking-snapshot/', admin_client_tracking_snapshot, name='admin_client_tracking_snapshot'),
] + router.urls
