from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from .models import Message, MessageAttachment
from .serializers.message_serializer import MessageSerializer, MessageAttachmentSerializer
from users.client_area.models import ClientProfile, ClientProgressPhoto, ClientWeightEntry

User = get_user_model()

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            sender=user
        ) | Message.objects.filter(
            recipient=user
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class MessageAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = MessageAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return MessageAttachment.objects.filter(message__recipient=self.request.user) | \
               MessageAttachment.objects.filter(message__sender=self.request.user)

    def perform_create(self, serializer):
        message = serializer.validated_data['message']
        user = self.request.user
        if message.sender_id != user.id and message.recipient_id != user.id:
            raise PermissionDenied('You are not allowed to attach files to this message.')

        uploaded_file = self.request.FILES.get('file')
        serializer.save(
            original_filename=getattr(uploaded_file, 'name', '') or '',
            content_type=getattr(uploaded_file, 'content_type', '') or '',
            file_size=getattr(uploaded_file, 'size', None),
        )


def _ensure_admin(user):
    if not user.is_authenticated or getattr(user, "role", None) != "admin":
        raise PermissionDenied("Admin access required.")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def admin_conversations(request):
    _ensure_admin(request.user)

    base_qs = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related("sender", "recipient").order_by("-sent_at")

    conversations = {}
    for msg in base_qs:
        other = msg.recipient if msg.sender_id == request.user.id else msg.sender
        if getattr(other, "role", None) != "client":
            continue

        row = conversations.get(other.id)
        if row is None:
            display_name = f"{(other.first_name or '').strip()} {(other.last_name or '').strip()}".strip()
            conversations[other.id] = {
                "client": {
                    "id": other.id,
                    "email": other.email,
                    "name": display_name or other.email,
                },
                "unanswered_count": 0,
                "last_message_at": msg.sent_at,
            }
            row = conversations[other.id]

        if msg.sender_id == other.id and msg.recipient_id == request.user.id and not msg.read:
            row["unanswered_count"] += 1

    payload = sorted(
        conversations.values(),
        key=lambda item: (
            -int(item["unanswered_count"] > 0),
            item["last_message_at"],
        ),
        reverse=True,
    )
    return Response({"conversations": payload}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def admin_conversation_messages(request, client_id):
    _ensure_admin(request.user)

    client = User.objects.filter(id=client_id, role="client").first()
    if not client:
        return Response({"detail": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

    qs = Message.objects.filter(
        (Q(sender=request.user, recipient=client) | Q(sender=client, recipient=request.user))
    ).prefetch_related("attachments").order_by("sent_at")

    Message.objects.filter(sender=client, recipient=request.user, read=False).update(read=True)

    messages = [
        {
            "id": msg.id,
            "sender": msg.sender_id,
            "recipient": msg.recipient_id,
            "content": msg.content,
            "sent_at": msg.sent_at,
            "read": msg.read,
            "attachments": [
                {
                    "id": att.id,
                    "file": att.file.url if att.file else None,
                    "original_filename": att.original_filename,
                }
                for att in msg.attachments.all()
            ],
        }
        for msg in qs
    ]

    return Response({"messages": messages}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def admin_client_tracking_snapshot(request, client_id):
    _ensure_admin(request.user)

    client = User.objects.filter(id=client_id, role="client").first()
    if not client:
        return Response({"detail": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

    has_thread = Message.objects.filter(
        Q(sender=request.user, recipient=client) | Q(sender=client, recipient=request.user)
    ).exists()
    if not has_thread:
        return Response({"detail": "No conversation found for this client."}, status=status.HTTP_404_NOT_FOUND)

    profile = ClientProfile.objects.filter(user=client).first()
    photos = list(
        ClientProgressPhoto.objects
        .filter(user=client)
        .order_by("-captured_for_date", "-created_at")[:120]
    )
    weights = list(
        ClientWeightEntry.objects
        .filter(user=client)
        .order_by("-measured_at", "-created_at")[:180]
    )

    photo_payload = []
    for row in photos:
        file_url = row.file.url if row.file else ""
        if file_url and not file_url.startswith("http"):
            file_url = request.build_absolute_uri(file_url)
        photo_payload.append(
            {
                "id": row.id,
                "captured_for_date": row.captured_for_date.isoformat(),
                "file_url": file_url,
                "notes": row.notes or "",
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    weight_payload = []
    for row in weights:
        local_dt = timezone.localtime(row.measured_at)
        weight_payload.append(
            {
                "id": row.id,
                "measured_at": local_dt.isoformat(),
                "measured_date": local_dt.date().isoformat(),
                "measured_time": local_dt.strftime("%H:%M"),
                "weight_value": float(row.weight_value),
                "unit": row.unit,
                "notes": row.notes or "",
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    return Response(
        {
            "client": {
                "client_user_id": client.id,
                "email": client.email,
                "offer_code": profile.offer_code if profile else None,
                "billing_cycle": (profile.billing_cycle if profile else "") or "",
                "is_active": bool(profile.is_active) if profile else False,
                "created_at": profile.created_at.isoformat() if profile and profile.created_at else None,
            },
            "tracking": {
                "photos": photo_payload,
                "weights": weight_payload,
                "summary": {
                    "photo_count": len(photo_payload),
                    "weight_count": len(weight_payload),
                },
            },
        },
        status=status.HTTP_200_OK,
    )
