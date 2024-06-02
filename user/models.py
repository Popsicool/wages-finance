from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
# Create your models here.

class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be provided")
        if not password:
            raise ValueError("Password must be provided")
        user = self.model(email=self.normalize_email(email), role="ADMIN")
        user.set_password(password)
        user.save()
        return user

    def create_user(self, firstname, lastname,  email, phone,referal_code, password=None):
        if email is None:
            raise TypeError('Users should have an Email')
        if firstname is None:
            raise TypeError('Users should have a Firstname')
        if lastname is None:
            raise TypeError('Users should have a Lastname')
        if phone is None:
            raise TypeError('Users should have a phone number')

        user = self.model(firstname=firstname, lastname=lastname, email=self.normalize_email(email), phone=phone, referal_code=referal_code)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self,email, password=None, **extra_fields):
        if password is None:
            raise TypeError('Password should not be none')
        user = self._create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.is_verified = True
        user.role = "ADMIN"
        user.save()
        return user

USER_ROLES = [
            ("USERS","General Users"),
            ("ADMIN","Admin users"),
        ]
TIERS_CHOICE = [
            ("T0","Tier 0"),
            ("T1","Tier 1"),
            ("T2","Tier 2"),
        ]

class User(AbstractBaseUser, PermissionsMixin):
    firstname                   = models.CharField(max_length=255)
    lastname                    = models.CharField(max_length=255)
    account_number              = models.CharField(max_length=12, blank=True, null=True)
    email                       = models.EmailField(max_length=255, unique=True, db_index=True)
    profile_picture             = models.ImageField(upload_to="profile_pic/", null=True, blank=True)
    phone                       = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_verified                 = models.BooleanField(default=False)
    is_active                   = models.BooleanField(default=True)
    is_staff                    = models.BooleanField(default=False)
    is_subscribed = models.BooleanField(default=False)
    pin = models.IntegerField(validators=[MinValueValidator(1000), MaxValueValidator(9999)], blank=True, null=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wages_point = models.IntegerField(default=0)
    referal_code = models.CharField(max_length=10, blank=True, null=True)
    bvn = models.CharField(max_length=15, blank=True, null=True)
    bvn_verify_details = models.JSONField(blank=True, null=True)
    nin = models.CharField(max_length=15, blank=True, null=True)
    nin_verify_details = models.JSONField(blank=True, null=True)
    tier                        = models.CharField(
        max_length=255,
        choices= TIERS_CHOICE,
        default= TIERS_CHOICE[0][0]
    )
    role                        = models.CharField(
        max_length=255,
        choices= USER_ROLES,
        default= USER_ROLES[0][0]
    )
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname', 'phone']

    objects = UserManager()

    def __str__(self):
        return f"{self.firstname} - {self.phone}"

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

    class Meta:
        db_table = "Users"

class EmailVerification(models.Model):
    is_used = models.BooleanField(default=False)
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    token = models.CharField(null=False, blank=False,
                             max_length=6, validators=[MinLengthValidator(6)])
    token_expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstname} - {self.is_used}"

    class Meta:
        db_table = 'EmailVerification'

ACTIVITIES_CHOICE = [
    ("DEBIT", "User got debited"),
    ("CREDIT", "User got creadited")
]
SAVINGS_FREQUENCY_CHOICE = [
    ("DAILY", "Daily contribution"),
    ("WEEKLY", "Weekly contribution"),
    ("MONTHLY", "Monthly contribution")
]

class Activities(models.Model):
    title = models.CharField(max_length=250)
    amount = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_activity')
    activity_type = models.CharField(
        max_length=255,
        choices= ACTIVITIES_CHOICE,
        default= ACTIVITIES_CHOICE[0][0]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.amount} - {self.title} by {self.user.firstname} on {self.created_at}"

WITHDRAWAL_STATUS = [
    ("PENDING", "Withdrawal yet to be approved"),
    ("REJECTED", "Withdrawal Rejected by admin"),
    ("PROCESSING", "Withdrawal has been approved by admin, waiting for payout"),
    ("SUCCESS", "Withdrawal Successfully done"),
    ("FAILED", "Withdrawal failed on payment gateway")
]
class Withdrawal(models.Model):
    amount = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_withdrawal')
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='user_withdrawal_approval', null=True, blank=True)
    bank_name =  models.CharField()
    account_number = models.CharField()
    status = models.CharField(choices=WITHDRAWAL_STATUS, default=WITHDRAWAL_STATUS[0][0])
    message = models.TextField(blank=True, null=True)
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.created_at} == {self.user.firstname} {self.user.lastname} == {self.amount} == {self.bank_name} == {self.account_number} == {self.status} "
class InvestmentPlan(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="investments/")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    quota = models.IntegerField()
    interest_rate = models.IntegerField()
    unit_share = models.IntegerField()
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} from {self.start_date} to {self.end_date}"

class UserInvestments(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_investment')
    investment = models.ForeignKey(InvestmentPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name='investment_type')
    shares = models.IntegerField()
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    def __str__(self):
        return f"{self.user.lastname} - {self.investment.title} - {self.shares} - {self.amount}"

class UserSavings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_savings')
    title = models.TextField()
    amount = models.BigIntegerField()
    saved = models.BigIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    cancel_date = models.DateField(blank=True, null=True)
    goal_met = models.BooleanField(default=False)
    frequency = models.CharField(
        choices=SAVINGS_FREQUENCY_CHOICE,
        default=SAVINGS_FREQUENCY_CHOICE[0][0]
    )
    is_active = models.BooleanField(default=True)
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.user.lastname} - {self.title} - {self.amount} - {self.start_date} - {self.end_date}"


class CoporativeMembership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)
    membership_id = models.CharField(max_length=20,unique=True)
    def __str__(self):
        return f"{self.user.lastname} - {self.membership_id} - {self.balance} -{self.date_joined}"



class SafeHavenAPIDetails(models.Model):
    acc_token = models.TextField(max_length=255)
    client_id = models.CharField(max_length=255)
    ibs_client_id = models.CharField(max_length=255)
    ibs_user_id = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

