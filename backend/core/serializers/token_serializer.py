from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# 👆 imports the base serializer used for generating jwt access and refresh tokens


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # 👆 extends the default jwt serializer to include custom user data in the token and response

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)  # 👉 gets the default token with user id and expiration
        token['email'] = user.email  # 👉 adds the user's email to the token payload
        token['role'] = user.role  # 👉 adds the user's role to the token payload
        token['subscription_status'] = user.subscription_status  # 👉 adds the user's subscription status to the token payload
        return token
    # 👆 customizes the token data that gets encoded into the jwt

    def validate(self, attrs):
        data = super().validate(attrs)  # 👉 calls the default validation logic (username/email + password)
        data['email'] = self.user.email  # 👉 includes email in the response body after login
        data['role'] = self.user.role  # 👉 includes role in the response body after login
        data['subscription_status'] = self.user.subscription_status  # 👉 includes subscription status in the response body after login
        return data
    # 👆 customizes the response returned to the frontend after login



# 👉 summary:
# this custom serializer handles login by validating user credentials
# and returning a jwt access + refresh token along with extra user data
# (email, role, subscription_status) in both the token payload and response.
# used by the frontend to display role-specific content immediately after login.
