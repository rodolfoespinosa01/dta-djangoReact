from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from django.utils import timezone
from users.models.custom_user import CustomUser
from adminplans.models import AdminProfile

class AdminSessionPersistenceTest(BaseAdminTest):
    def test_admin_session_persists_via_token(self):
        print("🔁 Test: Admin session persists after refresh with valid token")

        # Step 1: Create admin user
        user = CustomUser.objects.create_user(
            username='admin2@example.com',
            email='admin2@example.com',
            password='strongpass456',
            role='admin',
            is_staff=True,
            subscription_status='admin_trial'
        )

        # Step 2: Create AdminProfile with trial
        AdminProfile.objects.create(
            user=user,
            trial_start_date=timezone.now(),
            subscription_started_at=None,
            admin_stripe_customer_id='cus_mock123'
        )

        # Step 3: Login to get token
        login_response = self.client.post(
            reverse('admin-login'),
            data={'username': 'admin2@example.com', 'password': 'strongpass456'},
            content_type='application/json'
        )
        token = login_response.data.get('access')  # ✅ use DRF .data
        self.assertIsNotNone(token)

        # Step 4: Use token to access admin dashboard
        dashboard_response = self.client.get(
            reverse('admin-dashboard'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertTrue(dashboard_response.data.get('subscription_active'))
        self.assertEqual(dashboard_response.data.get('days_remaining'), 14)

