from celery import shared_task
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import stripe

from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan


@shared_task
def auto_upgrade_admin_trial(user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        if user.subscription_status != 'admin_trial':
            print(f"⏭️ User {user.email} is not on trial. Skipping upgrade.")
            return

        profile = user.admin_profile
        if profile.auto_renew_cancelled:
            print(f"❌ Auto-renew was cancelled by {user.email}. No upgrade will occur.")
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

        # ✅ Create subscription
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": monthly_plan.stripe_price_id}],
            trial_period_days=0
        )

        subscription_id = subscription.id
        subscription_started = timezone.now()
        next_billing = subscription_started + relativedelta(months=1)

        # ✅ Log confirmation
        print(f"✅ Stripe subscription created for {user.email}")
        print(f"📅 Subscription started: {subscription_started}")
        print(f"📅 Next billing (manually calculated): {next_billing}")

        # ✅ Update AdminProfile
        profile.admin_stripe_subscription_id = subscription_id
        profile.subscription_started_at = subscription_started
        profile.next_billing_date = next_billing
        profile.save()

        user.subscription_status = 'admin_monthly'
        user.save()

        print(f"✅ {user.email} upgraded from trial to monthly!")
        print(f"🧾 AdminProfile updated: Subscription ID = {subscription_id}, Next Billing Date = {next_billing}")

    except Exception as e:
        print(f"❌ Failed to auto-upgrade user {user_id}: {str(e)}")