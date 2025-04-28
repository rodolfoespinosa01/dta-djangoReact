from django.urls import path
from users.tasks.admin.admin_create_checkout_session import admin_create_checkout_session
from users.tasks.admin.admin_stripe_webhook import admin_stripe_webhook

urlpatterns = [
    path('admin_create_checkout_session/', admin_create_checkout_session, name='admin_create_checkout_session'),
    path('admin_stripe_webhook/', admin_stripe_webhook, name='admin_stripe_webhook'),
]