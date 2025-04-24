from django.db import models

class AdminPlan(models.Model):
    # Defines the available subscription types for admins
    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
        ('adminQuarterly', 'Quarterly Admin Plan'),
        ('adminAnnual', 'Annual Admin Plan'),
    ]

    # Internal plan name (e.g., 'adminMonthly'), stored in DB
    name = models.CharField(max_length=30, choices=PLAN_CHOICES, unique=True)

    # Optional text describing this plan
    description = models.TextField()

    # Stripe price ID (e.g., 'price_1RF4JjAYzIGw9RTdQWgrk6HN')
    stripe_price_id = models.CharField(max_length=100)

    # Price stored in cents for currency consistency (e.g., 999 for $9.99)
    price_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        # Displays the human-readable label in Django admin or logs
        return self.get_name_display()

    def price_dollars(self):
        # Helper method to convert cents to formatted dollars
        return round(self.price_cents / 100, 2)
