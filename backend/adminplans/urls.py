from django.urls import path
from .views import (
    admin_dashboard,
    admin_checkout_session,
    admin_stripe_webhook,
    admin_cancel_subscription,
)

urlpatterns = [
    path('admin_dashboard/', admin_dashboard.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin_checkout_session/', admin_checkout_session.admin_checkout_session, name='admin_checkout_session'),
    path('admin_stripe_webhook/', admin_stripe_webhook.admin_stripe_webhook, name='admin_stripe_webhook'),
    path('admin_cancel_subscription/', admin_cancel_subscription.admin_cancel_subscription, name='admin_cancel_subscription'),
]