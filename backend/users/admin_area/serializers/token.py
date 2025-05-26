from rest_framework_simplejwt.serializers import TokenObtainPairSerializer  # 👉 base serializer for jwt token generation


class CustomAdminTokenSerializer(TokenObtainPairSerializer):  # 👉 extends the default jwt serializer to include custom admin data
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)  # 👉 creates the default jwt token with user id and expiration

        # add custom claims to the token payload
        token['email'] = user.email  # 👉 includes the user's email
        token['role'] = user.role  # 👉 includes the user's role (should be 'admin')
        token['subscription_status'] = user.subscription_status  # 👉 includes the user's subscription status

        try:
            current_profile = user.profiles.get(is_current=True)  # 👉 gets the current active subscription profile
            token['is_canceled'] = current_profile.is_canceled  # 👉 includes whether the plan was canceled
        except:
            token['is_canceled'] = True  # 👉 fallback value if no profile is found

        return token  # 👉 returns the modified jwt token with custom fields


# 👉 summary:
# extends the jwt token serializer to embed admin-specific data like role, subscription status,
# and cancel status from the current profile. used during login to inform the frontend of access and billing state.