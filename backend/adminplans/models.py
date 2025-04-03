from django.db import models
class AdminPlan(models.Model):
    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
        ('adminAnnual', 'Annual Admin Plan'),
    ]

    name = models.CharField(max_length=30, choices=PLAN_CHOICES, unique=True)
    description = models.TextField()
    price_display = models.CharField(max_length=50)
    stripe_price_id = models.CharField(max_length=100)

    def __str__(self):
        return self.get_name_display()

