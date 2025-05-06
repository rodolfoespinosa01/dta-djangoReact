from django.urls import path
from users.client_area.views.dashboard import dashboard_view

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
]
