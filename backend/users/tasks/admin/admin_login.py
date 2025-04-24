import json
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])  # ✅ Accept only POST requests
@permission_classes([AllowAny])  # 🔓 Public login endpoint
def admin_login(request):
    # Reject non-POST requests
    if request.method != 'POST':
        return Response({'error': 'POST request required'}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data
    email = data.get('email')
    password = data.get('password')

    # 🔐 Authenticate using Django's auth system
    user = authenticate(request, username=email, password=password)

    # 🚫 If credentials don't match
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    # 🚫 Enforce admin-only access
    if user.role != 'admin':
        return Response({'error': 'Not an Admin account'}, status=status.HTTP_403_FORBIDDEN)

    # ✅ Login the user (sets session)
    login(request, user)

    return Response({'success': True, 'message': 'Logged in as admin'}, status=status.HTTP_200_OK)
