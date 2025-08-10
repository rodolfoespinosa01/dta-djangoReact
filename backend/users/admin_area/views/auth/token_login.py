from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView  # 👉 base login view
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer  # 👉 base jwt serializer
from users.admin_area.models import Profile  # 👉 imports the profile model to check subscription status


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):  # 👉 customizes jwt token payload for admin users

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)  # 👉 gets the default jwt token

        # 👉 core user info added to the token payload
        token['email'] = user.email
        token['role'] = user.role
        token['subscription_status'] = user.subscription_status

        # 👉 adds cancel status from the user's current profile
        try:
            current_profile = user.profiles.get(is_active=True)
            token['is_canceled'] = current_profile.is_canceled
        except Profile.DoesNotExist:
            token['is_canceled'] = True  # 👉 safe default if no profile exists

        return token

    def validate(self, attrs):
        data = super().validate(attrs)  # 👉 standard jwt username/password validation
        return data


class TokenObtainPairView(BaseTokenObtainPairView):  # 👉 exposes the login endpoint with the custom serializer
    serializer_class = TokenObtainPairSerializer


# 👉 summary:
# extends the default jwt login view to include custom user data in the token:
# email, role, subscription status, and cancel status from the current profile.
# used to support role-based access and billing logic immediately after login.