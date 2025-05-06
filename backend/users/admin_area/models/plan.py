from django.db import models

class Plan(models.Model):
    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
        ('adminQuarterly', 'Quarterly Admin Plan'),
        ('adminAnnual', 'Annual Admin Plan'),
    ]

    name = models.CharField(max_length=30, choices=PLAN_CHOICES, unique=True)
    description = models.TextField()
    stripe_price_id = models.CharField(max_length=100)
    price_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.get_name_display()

    def price_dollars(self):
        return round(self.price_cents / 100, 2)
