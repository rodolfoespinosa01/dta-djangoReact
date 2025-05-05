from django.urls import path
from users.admin_area.views.admin_dashboard import AdminDashboardView
from users.admin_area.views.admin_forgot_password import AdminForgotPasswordView
from users.admin_area.views.admin_reset_password_confirm import AdminResetPasswordConfirmView
from users.admin_area.views.admin_login import AdminLoginView

from users.admin_area.tasks.admin_register import admin_register
from users.admin_area.tasks.admin_get_pending_signup import admin_get_pending_signup
from users.admin_area.tasks.admin_cancel_subscription import admin_cancel_subscription
from users.admin_area.tasks.admin_stripe_webhook import admin_stripe_webhook
from users.admin_area.tasks.admin_create_checkout_session import admin_create_checkout_session


urlpatterns = [
    path('login/', AdminLoginView.as_view(), name='admin_login'),
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),

    path('register/', admin_register, name='admin_register'),
    path('pending_signup/<str:token>/', admin_get_pending_signup),

    path('forgot_password/', AdminForgotPasswordView.as_view(), name='admin_forgot_password'),
    path('reset_password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin_reset_password_confirm'),

    path('cancel_auto_renew/', admin_cancel_subscription),

    path('stripe_webhook/', admin_stripe_webhook, name='admin_stripe_webhook'),
    path('admin_create_checkout_session/', admin_create_checkout_session, name='admin_create_checkout_session'),

]
