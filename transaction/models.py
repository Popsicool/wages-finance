from django.db import models
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.

TRANSACTION_STATUS = [
    ("PENDING", "Pending Transaction"),
    ("SUCCESS", "Successful Transaction"),
    ("FAILED", "Failed Transaction"),
]
TRANSACTION_TYPE = [
    ("WALLET-CREDIT", "Wallet Credit"),
    ("Withdrawal", "Withdrawal"),
    ("DATA_PURCHASE", "Data purchase"),
]
class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=250,
        choices=TRANSACTION_STATUS,
        default=TRANSACTION_STATUS[0][0]
    )
    type = models.CharField(
        max_length=250,
        choices=TRANSACTION_TYPE,
        default=TRANSACTION_TYPE[0][0]
    )
    description = models.CharField(max_length=250)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.description} - {self.status}"