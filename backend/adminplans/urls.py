from django.urls import path
from .views import create_checkout_session 

urlpatterns = [
    path('create-checkout-session/', create_checkout_session),
]
