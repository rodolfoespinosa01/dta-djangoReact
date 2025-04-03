from django.urls import path
from .views import create_checkout_session
from . import views

urlpatterns = [
    path('create-checkout-session/', create_checkout_session),
    path('register-admin/', views.register_admin, name='register_admin'),
]
