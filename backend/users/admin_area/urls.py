# backend/users/admin_area/urls.py

from django.urls import path
# 🔐 Auth
from users.admin_area.views.auth.register import register
from users.admin_area.views.auth.token_login import TokenObtainPairView
from users.admin_area.views.auth.get_pending_signup import get_pending_signup
# Password
from users.admin_area.views.password.forgot_password import ForgotPasswordView
from users.admin_area.views.password.reset_password_confirm import ResetPasswordConfirmView
# 📊 Dashboard
from users.admin_area.views.dashboard.dashboard import DashboardView
# 💳 Billing
from users.admin_area.views.billing.create_checkout_session import create_checkout_session
from users.admin_area.views.billing.stripe_webhook import stripe_webhook
from users.admin_area.views.billing.cancel_subscription import cancel_subscription
from users.admin_area.views.billing.reactivate_checkout import ReactivateCheckoutView

urlpatterns = [
    # 🔐 Auth
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('pending_signup/<str:token>/', get_pending_signup, name='get_pending_signup'),

    # Password
    path('forgot_password/', ForgotPasswordView.as_view()),
    path('reset_password_confirm/', ResetPasswordConfirmView.as_view()),
    # 📊 Dashboard
    path('dashboard/', DashboardView.as_view()),

    # 💳 Billing
    path('create_checkout_session/', create_checkout_session, name='create_checkout_session'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('cancel_subscription/', cancel_subscription, name='cancel_subscription'),
    path('reactivate_checkout/', ReactivateCheckoutView.as_view(), name='reactivate_checkout'),
]
