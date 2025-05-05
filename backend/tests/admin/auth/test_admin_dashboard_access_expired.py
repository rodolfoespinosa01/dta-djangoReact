from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework.test import APIClient 
from core.models.custom_user import CustomUser
from users.admin_area.models import AdminProfile
from tests.base.base_admin_test import BaseAdminTest

class AdminDashboardAccessTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.admin = CustomUser.objects.create_user(
            username='expiredadmin',
            email='expiredadmin@test.com',
            password='securepass123',
            role='admin',
            subscription_status='admin_monthly'
        )

        AdminProfile.objects.create(
            user=self.admin,
            subscription_started_at=timezone.now() - timedelta(days=60),
            subscription_end_date=timezone.now() - timedelta(days=1),
            is_canceled=True
        )

        refresh = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_expired_admin_blocked_from_dashboard(self):
        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("subscription has ended", response.data.get("error", ""))
