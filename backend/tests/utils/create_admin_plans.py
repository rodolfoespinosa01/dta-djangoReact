from users.admin_area.models import AdminPlan

def create_admin_plans():
    AdminPlan.objects.get_or_create(
        name='adminTrial',
        defaults={
            'description': 'Free Admin Trial',
            'stripe_price_id': '',  # No charge
            'price_cents': 0
        }
    )

    AdminPlan.objects.get_or_create(
        name='adminMonthly',
        defaults={
            'description': 'Monthly Admin Plan',
            'stripe_price_id': 'price_1RF4JjAYzIGw9RTdQWgrk6HN',
            'price_cents': 2999
        }
    )

    AdminPlan.objects.get_or_create(
        name='adminQuarterly',
        defaults={
            'description': 'Quarterly Admin Plan',
            'stripe_price_id': 'price_1RF4LUAYzIGw9RTdxQW8jVoh',
            'price_cents': 7999
        }
    )

    AdminPlan.objects.get_or_create(
        name='adminAnnual',
        defaults={
            'description': 'Yearly Admin Plan',
            'stripe_price_id': 'price_1RF4MDAYzIGw9RTdx50TyiQ6',
            'price_cents': 29999
        }
    )
