from django.urls import path

# 🔐 Auth
from users.admin_area.views.auth.register import register
from users.admin_area.views.auth.token_login import TokenObtainPairView
from users.admin_area.views.auth.google_login import admin_google_login
from users.admin_area.views.pendingsignup.get_pending_signup import get_pending_signup  # keep this ONE

# 🔑 Password
from users.admin_area.views.password.reset_password_confirm import ResetPasswordConfirmView
from users.admin_area.views.password.admin_forgot_password import AdminForgotPasswordView

# 📊 Dashboard
from users.admin_area.views.dashboard.DashboardView import DashboardView
from users.admin_area.views.dashboard.direct_client_tracking import admin_client_tracking

# 💳 Billing
from users.admin_area.views.billing.create_checkout_session import create_checkout_session
from users.admin_area.views.billing.cancel_subscription import cancel_subscription
from users.admin_area.views.billing.change_subscription import change_subscription
from users.admin_area.views.billing.stripe_webhook import stripe_webhook
from users.admin_area.views.billing.payment_method import (
    get_payment_method,
    create_payment_method_update_session,
)
from users.admin_area.views.billing.reactivate import preview, start
from users.admin_area.views.parameters.admin_parameter_settings import (
    parameter_settings_detail,
    parameter_settings_status,
    parameter_settings_use_defaults,
)
from users.admin_area.views.dev.create_test_admin import create_test_admin


urlpatterns = [
    # 🔐 Auth
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('google_login/', admin_google_login, name='google_login'),
    path('dev/create_test_admin/', create_test_admin, name='dev_create_test_admin'),
    path('pending_signup/<str:token>/', get_pending_signup, name='get_pending_signup'),

    # 🔑 Password
    path('forgot_password/', AdminForgotPasswordView.as_view(), name='forgot_password'),
    path('reset_password/confirm/', ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),

    # 📊 Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('clients/<int:user_id>/tracking/', admin_client_tracking, name='admin_client_tracking'),
    path('parameter_settings/status/', parameter_settings_status, name='parameter_settings_status'),
    path('parameter_settings/use_defaults/', parameter_settings_use_defaults, name='parameter_settings_use_defaults'),
    path('parameter_settings/', parameter_settings_detail, name='parameter_settings_detail'),

    # 💳 Billing
    path('create_checkout_session/', create_checkout_session, name='create_checkout_session'),
    path('cancel_subscription/', cancel_subscription, name='cancel_subscription'),
    path('change_subscription/', change_subscription, name='change_subscription'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('payment_method/', get_payment_method, name='payment_method'),
    path('payment_method/update_session/', create_payment_method_update_session, name='payment_method_update_session'),
    # 💳 Billing (reactivation)
    path("reactivation/preview/", preview, name="reactivation_preview"),
    path("reactivation/start/", start, name="reactivation_start"),
]
