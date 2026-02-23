from django.urls import path
from users.superadmin_area.views import dashboard
from users.superadmin_area.views.analytics import analytics
from users.superadmin_area.views.food_library import food_library_browser
from users.superadmin_area.views.token_login import SuperAdminTokenObtainPairView

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('analytics/', analytics, name='analytics'),
    path('food-library/', food_library_browser, name='food_library_browser'),
    path('login/', SuperAdminTokenObtainPairView.as_view(), name='login'),
]
