# backend/users/backends.py

from django.contrib.auth.backends import ModelBackend
from core.models import CustomUser

class EmailBackend(ModelBackend):
    """
    Custom auth backend to allow login with email instead of username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(email=username)
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None
