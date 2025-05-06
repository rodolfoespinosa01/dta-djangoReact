from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from core.models import CustomUser

class TokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['subscription_status'] = user.subscription_status
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        return data



class TokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
