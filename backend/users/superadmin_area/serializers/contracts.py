from rest_framework import serializers


class SuperAdminDashboardItemSerializer(serializers.Serializer):
    email = serializers.EmailField()
    plan = serializers.CharField()
    price = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    next_billing = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    cancelled = serializers.BooleanField()
    amount_spent = serializers.FloatField()


class SuperAdminPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_items = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()


class SuperAdminAnalyticsPointSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.FloatField()
    amount_cents = serializers.IntegerField(min_value=0)


class SuperAdminAnalyticsWindowSerializer(serializers.Serializer):
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    timezone = serializers.CharField()
    bucket = serializers.ChoiceField(choices=["hour", "day"])


class SuperAdminAnalyticsPayloadSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=["day", "week", "month"])
    currency = serializers.CharField()
    total_revenue = serializers.FloatField()
    total_revenue_cents = serializers.IntegerField(min_value=0)
    transactions = serializers.IntegerField(min_value=0)
    generated_at = serializers.DateTimeField()
    window = SuperAdminAnalyticsWindowSerializer()
    points = SuperAdminAnalyticsPointSerializer(many=True)
