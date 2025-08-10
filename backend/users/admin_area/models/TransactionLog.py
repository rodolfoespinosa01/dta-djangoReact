from django.db import models


class TransactionLog(models.Model):
    email = models.EmailField()
    stripe_transaction_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} | {self.stripe_transaction_id} | {self.created_at}"
