from django.db import models


class AdminDiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percent Off"),
        ("fixed_amount", "Fixed Amount Off"),
    ]
    SCOPE_CHOICES = [
        ("one_time", "One-Time Purchase"),
        ("recurring", "Recurring Subscription"),
        ("either", "Either"),
    ]

    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default="percent")
    percent_off = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    amount_cents = models.PositiveIntegerField(default=0)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default="either")
    eligible_plan_names = models.JSONField(default=list, blank=True)
    associated_admin = models.ForeignKey(
        "admin_area.AdminIdentity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_discount_codes",
    )
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Admin Discount Code"
        verbose_name_plural = "Admin Discount Codes"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code or "ADMIN-DISCOUNT"
