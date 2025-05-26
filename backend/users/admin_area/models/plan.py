from django.db import models  # 👉 provides base model functionality for defining database tables

class Plan(models.Model):  # 👉 stores subscription plans available to admin users

    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
        ('adminQuarterly', 'Quarterly Admin Plan'),
        ('adminAnnual', 'Annual Admin Plan'),
    ]
    # 👉 defines the available plan types that can be selected during signup or reactivation

    name = models.CharField(max_length=30, choices=PLAN_CHOICES, unique=True)  # 👉 stores the internal plan key (e.g. adminMonthly)
    description = models.TextField()  # 👉 short summary or marketing description of the plan
    stripe_price_id = models.CharField(max_length=100)  # 👉 links this plan to a specific price in stripe
    price_cents = models.PositiveIntegerField(default=0)  # 👉 stores the plan price in cents for consistency with stripe

    def __str__(self):
        return self.get_name_display()  # 👉 returns the readable plan name in admin or logs (e.g. "Monthly Admin Plan")

    def price_dollars(self):
        return round(self.price_cents / 100, 2)  # 👉 helper method to convert cents to usd for display purposes

    # 👉 summary:
    # defines the available subscription plans for admin users, including pricing,
    # stripe linkage, and human-readable display names. used for billing and plan selection logic.