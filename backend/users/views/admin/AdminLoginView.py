from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers.token_serializer import CustomTokenObtainPairSerializer


class AdminLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
