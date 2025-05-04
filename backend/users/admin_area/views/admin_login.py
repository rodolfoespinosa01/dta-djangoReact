from rest_framework_simplejwt.views import TokenObtainPairView
from core.serializers.token_serializer import CustomTokenObtainPairSerializer


class AdminLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
