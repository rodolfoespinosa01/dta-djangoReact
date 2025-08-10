# backend/users/admin_area/views/auth/token_login.py
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from users.admin_area.models import Profile
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, NotFound

class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = getattr(user, 'role', None)
        token['subscription_status'] = getattr(user, 'subscription_status', None)
        try:
            current_profile = user.profiles.get(is_active=True)
            token['is_canceled'] = current_profile.is_canceled
        except Profile.DoesNotExist:
            token['is_canceled'] = True
        return token

    def validate(self, attrs):
        User = get_user_model()
        username = attrs.get('username')
        password = attrs.get('password')

        # look up account
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            # 404 → "no account found"
            raise NotFound(detail={"error": "No account found with that email.", "error_code": "USER_NOT_FOUND"})

        if not user.is_active:
            raise AuthenticationFailed(detail={"error": "This account is inactive.", "error_code": "INACTIVE"})

        if not user.check_password(password):
            # 401 → "wrong password"
            raise AuthenticationFailed(detail={"error": "Account found, but the password is incorrect.", "error_code": "WRONG_PASSWORD"})

        # OK → mint tokens (skip parent validate so we keep our flow)
        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": getattr(user, 'role', None),
            "subscription_status": getattr(user, 'subscription_status', None),
            "is_canceled": refresh.get('is_canceled', True),
        }

class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
