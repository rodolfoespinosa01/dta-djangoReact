from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class SuperAdminLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user and user.is_superuser:
            refresh = RefreshToken.for_user(user)

            # Manually add custom claims
            refresh['email'] = user.email
            refresh['role'] = getattr(user, 'role', 'superadmin')
            refresh['is_superuser'] = user.is_superuser

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': refresh['role'],
                'is_superuser': refresh['is_superuser']
            })

        return Response({'error': 'Invalid credentials or not a superadmin'}, status=status.HTTP_401_UNAUTHORIZED)
