from django.db.models.signals import post_migrate
from django.dispatch import receiver
from users.admin_area.models import Plan

@receiver(post_migrate)
def create_default_plans(sender, **kwargs):
    if sender.name != 'users.admin_area':
        return

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

    for plan in default_plans:
        Plan.objects.get_or_create(name=plan['name'], defaults=plan)
