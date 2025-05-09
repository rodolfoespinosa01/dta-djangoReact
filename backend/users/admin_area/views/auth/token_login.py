from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from users.admin_area.models import Profile

class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Core user info
        token['email'] = user.email
        token['role'] = user.role
        token['subscription_status'] = user.subscription_status

        # Add is_canceled from current Profile (if it exists)
        try:
            current_profile = user.profiles.get(is_current=True)
            token['is_canceled'] = current_profile.is_canceled
        except Profile.DoesNotExist:
            token['is_canceled'] = True  # Safe default if no profile exists

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        return data


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
