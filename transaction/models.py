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
    ("WITHDRAWAL", "Withdrawal"),
    ("DATA_PURCHASE", "Data purchase"),
]
TRANSACTION_NATURE = [
    ("Others", "OTHERS"),
    ("SAVINGS", "Savings"),
    ("LOAN_REPAYMENT", "Loan Repayment"),
]
class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.PositiveBigIntegerField()
    revenue = models.PositiveBigIntegerField(default=0)
    source = models.CharField(max_length=1000)
    message = models.TextField(null=True, blank=True)
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
    nature = models.CharField(
        max_length=250,
        choices=TRANSACTION_NATURE,
        default=TRANSACTION_NATURE[0][0]
    )
    description = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstname} - {self.description} - {self.status}"