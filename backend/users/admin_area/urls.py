from django.urls import path

# 🔐 Auth
from users.admin_area.views.auth.register import register
from users.admin_area.views.auth.token_login import TokenObtainPairView
from users.admin_area.views.pendingsignup.get_pending_signup import get_pending_signup  # keep this ONE

# 🔑 Password
from users.admin_area.views.password.reset_password_confirm import ResetPasswordConfirmView
from users.admin_area.views.password.admin_forgot_password import AdminForgotPasswordView

# 📊 Dashboard
from users.admin_area.views.dashboard.DashboardView import DashboardView

# 💳 Billing
from users.admin_area.views.billing.create_checkout_session import create_checkout_session
from users.admin_area.views.billing.cancel_subscription import cancel_subscription
from users.admin_area.views.billing.stripe_webhook import stripe_webhook
from users.admin_area.views.billing.reactivation import preview, start

urlpatterns = [
    # 🔐 Auth
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('pending_signup/<str:token>/', get_pending_signup, name='get_pending_signup'),

    # 🔑 Password
    path('forgot_password/', AdminForgotPasswordView.as_view(), name='forgot_password'),
    path('reset_password/confirm/', ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),

    # 📊 Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # 💳 Billing
    path('create_checkout_session/', create_checkout_session, name='create_checkout_session'),
    path('cancel_subscription/', cancel_subscription, name='cancel_subscription'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    # 💳 Billing (reactivation)
    path("reactivation/preview/", preview, name="reactivation_preview"),
    path("reactivation/start/", start, name="reactivation_start"),
]
