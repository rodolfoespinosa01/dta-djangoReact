from django.urls import path
from users.tasks.admin.admin_create_checkout_session import create_admin_checkout_session
from users.tasks.admin.admin_stripe_webhook import admin_stripe_webhook

urlpatterns = [
    path('create-checkout-session/', create_admin_checkout_session, name='create_checkout_session'),
    path('stripe-webhook/', admin_stripe_webhook, name='admin_stripe_webhook'),
]