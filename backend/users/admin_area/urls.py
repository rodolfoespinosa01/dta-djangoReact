from django.urls import path
# 🔐 Auth
from users.admin_area.views.auth.register import register
from users.admin_area.views.auth.token_login import TokenObtainPairView
from users.admin_area.views.auth.get_pending_signup import get_pending_signup
# Password
from users.admin_area.views.password.reset_password_confirm import ResetPasswordConfirmView

from users.admin_area.views.password.admin_forgot_password import AdminForgotPasswordView
# 📊 Dashboard
from users.admin_area.views.dashboard.dashboard import DashboardView
# 💳 Billing
from users.admin_area.views.billing.create_checkout_session import create_checkout_session
from users.admin_area.views.billing.stripe_webhook import stripe_webhook

from users.admin_area.views.pendingsignup.get_pending_signup import get_pending_signup

urlpatterns = [
    # 🔐 Auth
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('pending_signup/<str:token>/', get_pending_signup, name='get_pending_signup'),

    # Password
    # ✅ New (dash format expected by frontend)
    path('reset_password/confirm/', ResetPasswordConfirmView.as_view()),

    # 📊 Dashboard
    path('forgot_password/', AdminForgotPasswordView.as_view(), name='forgot_password'),
    path('dashboard/', DashboardView.as_view()),

    # 💳 Billing
    path('create_checkout_session/', create_checkout_session, name='create_checkout_session'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('pending_signup/<str:token>/', get_pending_signup, name='get_pending_signup'),
]