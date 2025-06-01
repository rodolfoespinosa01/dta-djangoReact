from rest_framework import serializers
from users.admin_area.models import PendingSignup

class PendingSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingSignup
        fields = '__all__'
