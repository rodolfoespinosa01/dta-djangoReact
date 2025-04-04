from django.urls import path
from .views import attach_subscription_to_user

urlpatterns = [
    path('attach/', attach_subscription_to_user),
]
