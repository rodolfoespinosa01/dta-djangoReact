from django.db.models.signals import post_migrate  # 👉 signal triggered after migrations are applied
from django.dispatch import receiver  # 👉 decorator used to connect the signal to the handler
from users.admin_area.models import Plan  # 👉 imports the Plan model to create or check existing plans


@receiver(post_migrate)
def create_default_plans(sender, **kwargs):
    if sender.name != 'users.admin_area':
        return  # 👉 only run this logic when the admin_area app is migrated


    default_plans = [
        {
            'name': 'adminTrial',
            'description': 'Free 14-day trial',
            'stripe_price_id': 'price_1R8ZfGAYzIGw9RTd5w6Dh5gQ',
            'price_cents': 0,
        },
        {
            'name': 'adminMonthly',
            'description': 'Monthly subscription',
            'stripe_price_id': 'price_1RF4JjAYzIGw9RTdQWgrk6HN',
            'price_cents': 2999,
        },
        {
            'name': 'adminQuarterly',
            'description': 'Quarterly subscription',
            'stripe_price_id': 'price_1RF4LUAYzIGw9RTdxQW8jVoh',
            'price_cents': 7999,
        },
        {
            'name': 'adminAnnual',
            'description': 'Annual subscription',
            'stripe_price_id': 'price_1RF4MDAYzIGw9RTdx50TyiQ6',
            'price_cents': 29999,
        },
    ]
# 👆 defines a list of default admin plans with their stripe price ids and descriptions

    for plan in default_plans:
        Plan.objects.get_or_create(name=plan['name'], defaults=plan)
    # 👆 creates the plan if it doesn't already exist, using the plan name as a unique key


# 👉 summary:
# automatically creates default admin subscription plans after migrations are applied.
# ensures required plans are always seeded in the database with correct stripe references.
# triggered only when the users.admin_area app is migrated to avoid duplicate creation.