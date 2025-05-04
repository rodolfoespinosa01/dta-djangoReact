from django.urls import path
from users.client_area.views.client_dashboard import client_dashboard_view

urlpatterns = [
    path('dashboard/', client_dashboard_view, name='client_dashboard'),
]
