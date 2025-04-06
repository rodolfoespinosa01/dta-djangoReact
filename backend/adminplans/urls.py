from django.urls import path
from .views import create_checkout_session, stripe_webhook

urlpatterns = [
    path('create-checkout-session/', create_checkout_session),
    path('stripe-webhook/', stripe_webhook),
]
