import json
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([AllowAny])
def superadmin_login(request):
    if request.method != 'POST':
        return Response({'error': 'POST request required'}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    email = data.get('email')
    password = data.get('password')

    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_superuser:
        return Response({'error': 'Not a SuperAdmin account'}, status=status.HTTP_403_FORBIDDEN)

    login(request, user)

    return Response({
        'success': True,
        'message': 'Logged in as SuperAdmin',
        'email': user.email
    }, status=status.HTTP_200_OK)