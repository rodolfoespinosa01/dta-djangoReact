from celery import shared_task
from django.utils import timezone
from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan
import stripe
import logging

logger = logging.getLogger(__name__)

@shared_task
def test_celery():
    print("🔥 Celery is working!")
    return "success"

@shared_task
def auto_upgrade_admin_trial(user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        if user.subscription_status != 'admin_trial':
            print(f"⏭️ User {user.email} is not on trial. Skipping upgrade.")
            return

        profile = user.admin_profile
        if profile.auto_renew_cancelled:
            logger.info(f"❌ Auto-renew was cancelled by {user.email}. No upgrade will occur.")
            return
        customer_id = profile.admin_stripe_customer_id

        if not customer_id:
            print(f"❌ No Stripe customer ID for {user.email}")
            return

        # 🧠 Get correct monthly plan from DB dynamically
        try:
            monthly_plan = AdminPlan.objects.get(name='adminMonthly')
        except AdminPlan.DoesNotExist:
            print("❌ AdminMonthly plan not found in DB")
            return

        # ✅ Use the correct dynamic price ID
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": monthly_plan.stripe_price_id}],
            trial_period_days=0
        )

        profile.admin_stripe_subscription_id = subscription.id
        profile.subscription_started_at = timezone.now()
        profile.save()

        user.subscription_status = 'admin_monthly'
        user.save()

        print(f"✅ {user.email} upgraded from trial to monthly!")

    except Exception as e:
        print(f"❌ Failed to auto-upgrade user {user_id}: {str(e)}")