from django.urls import path
from .views import (
    admin_dashboard,
    admin_checkout_session,
    admin_stripe_webhook,
    admin_cancel_subscription,
)
from .views.admin_reactivate_checkout_session import admin_reactivate_checkout_session
from .views.admin_stripe_reactivation_webhook import admin_stripe_reactivation_webhook

urlpatterns = [
    path('admin_dashboard/', admin_dashboard.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin_checkout_session/', admin_checkout_session.admin_checkout_session, name='admin_checkout_session'),
    path('admin_stripe_webhook/', admin_stripe_webhook.admin_stripe_webhook, name='admin_stripe_webhook'),
    path('admin_cancel_subscription/', admin_cancel_subscription.admin_cancel_subscription, name='admin_cancel_subscription'),
    path('admin_reactivate_checkout/', admin_reactivate_checkout_session, name='admin_reactivate_checkout'),
    path('admin_stripe_reactivation_webhook/', admin_stripe_reactivation_webhook, name='admin_stripe_reactivation_webhook'),
]
