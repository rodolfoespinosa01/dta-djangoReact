from django.urls import path
from users.superadmin_area.views import dashboard
from users.superadmin_area.views.token_login import TokenObtainPairView

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
]
