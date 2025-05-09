from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomAdminTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['subscription_status'] = user.subscription_status

        try:
            current_profile = user.profiles.get(is_current=True)
            token['is_canceled'] = current_profile.is_canceled
        except:
            token['is_canceled'] = True  # default if no profile found

        return token
