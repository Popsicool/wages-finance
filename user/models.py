from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
from datetime import timedelta
from datetime import date
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

    def create_user(self, firstname, lastname,  email, phone, referal_code, password=None, **extra_fields):
        if email is None:
            raise TypeError('Users should have an Email')
        if firstname is None:
            raise TypeError('Users should have a Firstname')
        if lastname is None:
            raise TypeError('Users should have a Lastname')
        if phone is None:
            raise TypeError('Users should have a phone number')

        user = self.model(firstname=firstname, lastname=lastname, email=self.normalize_email(
            email), phone=phone, referal_code=referal_code, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
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
    ("USERS", "General Users"),
    ("ADMIN", "Admin users"),
]
TIERS_CHOICE = [
    ("T0", "Tier 0"),
    ("T1", "Tier 1"),
    ("T2", "Tier 2"),
]


class User(AbstractBaseUser, PermissionsMixin):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    account_number = models.CharField(max_length=12, blank=True, null=True)
    account_name = models.CharField(max_length=250, blank=True, null=True)
    referal = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    profile_picture = models.ImageField(
        upload_to="profile_pic/", null=True, blank=True)
    phone = models.CharField(
        max_length=255, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_subscribed = models.BooleanField(default=False)
    pin = models.IntegerField(validators=[MinValueValidator(
        1000), MaxValueValidator(9999)], blank=True, null=True)
    wallet_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    wages_point = models.IntegerField(default=0)
    referal_code = models.CharField(max_length=10, blank=True, null=True)
    referal_balance = models.BigIntegerField(default=0)
    total_referal_balance = models.BigIntegerField(default=0)
    bvn = models.CharField(max_length=15, blank=True, null=True)
    bvn_verify_details = models.JSONField(blank=True, null=True)
    nin = models.CharField(max_length=15, blank=True, null=True)
    nin_verify_details = models.JSONField(blank=True, null=True)
    tier = models.CharField(
        max_length=255,
        choices=TIERS_CHOICE,
        default=TIERS_CHOICE[0][0]
    )
    role = models.CharField(
        max_length=255,
        choices=USER_ROLES,
        default=USER_ROLES[0][0]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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


class ForgetPasswordToken(models.Model):
    is_used = models.BooleanField(default=False)
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    token = models.CharField(null=False, blank=False,
                             max_length=4, validators=[MinLengthValidator(4)])
    token_expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstname} - {self.is_used}"

    class Meta:
        db_table = 'PasswordReset'


ACTIVITIES_CHOICE = [
    ("DEBIT", "User got debited"),
    ("CREDIT", "User got credited")
]
SAVINGS_FREQUENCY_CHOICE = [
    ("DAILY", "Daily contribution"),
    ("WEEKLY", "Weekly contribution"),
    ("MONTHLY", "Monthly contribution")
]


class Activities(models.Model):
    title = models.CharField(max_length=250)
    amount = models.IntegerField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_activity')
    activity_type = models.CharField(
        max_length=255,
        choices=ACTIVITIES_CHOICE,
        default=ACTIVITIES_CHOICE[0][0]
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
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_withdrawal')
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   related_name='user_withdrawal_approval', null=True, blank=True)
    bank_name = models.CharField()
    bank_code = models.CharField()
    account_number = models.CharField()
    status = models.CharField(
        choices=WITHDRAWAL_STATUS, default=WITHDRAWAL_STATUS[0][0])
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.created_at} == {self.user.firstname} {self.user.lastname} == {self.amount} == {self.bank_name} == {self.account_number} == {self.status} "


class InvestmentPlan(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="investments/")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    quota = models.IntegerField()
    investors = models.IntegerField(default=0)
    interest_rate = models.IntegerField()
    unit_share = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} from {self.start_date} to {self.end_date}"


USER_INVESTMENT_STATUS = [
    ("ACTIVE", "Active Investment"),
    ("MATURED", "Investment Matured, waiting for payout"),
    ("WITHDRAWN", "Investment has been withdrawn")
]


class UserInvestments(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_investment')
    investment = models.ForeignKey(InvestmentPlan, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='investment_type')
    shares = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=USER_INVESTMENT_STATUS, default=USER_INVESTMENT_STATUS[0][0])
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()

    class Meta:
        unique_together = ('user', 'investment')

    def __str__(self):
        return f"{self.user.lastname} - {self.investment.title} - {self.shares} - {self.amount}"


SAVINGS_TYPES = [
    ("BIRTHDAY", "Birthday"),
    ("CAR-PURCHASE", "Car purchase"),
    ("VACATION", "Vacations"),
    ("GADGET-PURCHASE", "Gadget purchase"),
    ("MISCELLANEOUS", "Miscellaneous")
]


class UserSavings(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_savings')
    type = models.CharField(
        max_length=35, choices=SAVINGS_TYPES, default=SAVINGS_TYPES[0][0])
    amount = models.BigIntegerField()
    saved = models.BigIntegerField(default=0)
    start_date = models.DateField(blank=True, null=True)
    withdrawal_date = models.DateField(blank=True, null=True)
    cancel_date = models.DateField(blank=True, null=True)
    cycle = models.PositiveIntegerField(default=1)
    goal_met = models.BooleanField(default=False)
    frequency = models.CharField(
        choices=SAVINGS_FREQUENCY_CHOICE,
        default=SAVINGS_FREQUENCY_CHOICE[0][0]
    )
    time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.lastname} - {self.type} - {self.amount} - {self.start_date} - {self.withdrawal_date}"


SAVINGS_ACTIVITIES_CHOICE = [
    ("DEPOSIT", "Deposit"),
    ("WITHDRAWAL", "Withdrawal"),
    ("DIVIDENDS", "Dividends"),
]


class SavingsActivities(models.Model):
    savings = models.ForeignKey(
        UserSavings, on_delete=models.CASCADE, related_name="savings_activities"
    )
    amount = models.IntegerField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_saving_activity')
    activity_type = models.CharField(
        max_length=255,
        choices=SAVINGS_ACTIVITIES_CHOICE,
        default=SAVINGS_ACTIVITIES_CHOICE[0][0]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} - {self.savings.type} by {self.user.firstname} on {self.created_at}"


class CoporativeMembership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    membership_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.user.lastname} - {self.membership_id} - {self.balance} -{self.date_joined}"


class CoporativeActivities(models.Model):
    amount = models.IntegerField()
    balance = models.IntegerField()
    user_coop = models.ForeignKey(
        CoporativeMembership, on_delete=models.CASCADE, related_name='user_coop_activity')
    activity_type = models.CharField(
        max_length=255,
        choices=SAVINGS_ACTIVITIES_CHOICE,
        default=SAVINGS_ACTIVITIES_CHOICE[0][0]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} by {self.user_coop.user.firstname} on {self.created_at}"


class SafeHavenAPIDetails(models.Model):
    acc_token = models.TextField(max_length=255)
    client_id = models.CharField(max_length=255)
    ibs_client_id = models.CharField(max_length=255)
    ibs_user_id = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)


LOAN_STATUS = [
    ("PENDING", "Loan waiting for admin approval"),
    ("APPROVED", "Loan approved by admin"),
    ("REJECTED", "Loan Rejected by admin"),
    ("REPAYED", "Loan fully repayed"),
    ("OVER-DUE", "Loan overdued"),
]


class Loan(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_loan")
    guarantor1 = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="guaranter_1")
    guarantor2 = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="guaranter_2")
    guarantor1_agreed = models.BooleanField(default=False)
    guarantor2_agreed = models.BooleanField(default=False)
    amount = models.PositiveBigIntegerField()
    amount_repayed = models.PositiveBigIntegerField(default=0)
    balance = models.PositiveBigIntegerField(default=0)
    duration_in_months = models.PositiveIntegerField(default=6)
    interest_rate = models.PositiveIntegerField(default=10)
    status = models.CharField(
        choices=LOAN_STATUS, default=LOAN_STATUS[0][0], max_length=10)
    date_requested = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.balance = self.amount + \
                (self.amount * (self.interest_rate / 100))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.lastname} - {self.balance} - {self.status}"

    def get_due_date(self):
        if self.date_approved:
            return self.date_approved + timedelta(days=self.duration_in_months * 30)
        return None

    def is_overdue(self):
        due_date = self.get_due_date()
        if due_date and date.today() > due_date:
            return True
        return False


BANK_LISTS = [
    {
        "name": "BANC CORP MICROFINANCE BANK",
                "routingKey": "090581",
                "logoImage": None,
                "bankCode": "090581",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "STERLING BANK",
                "routingKey": "000001",
                "logoImage": None,
                "bankCode": "000001",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "KEYSTONE BANK",
                "routingKey": "000002",
                "logoImage": None,
                "bankCode": "000002",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "FIRST CITY MONUMENT BANK",
                "routingKey": "000003",
                "logoImage": None,
                "bankCode": "000003",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "UNITED BANK FOR AFRICA",
                "routingKey": "000004",
                "logoImage": None,
                "bankCode": "000004",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "JAIZ BANK",
                "routingKey": "000006",
                "logoImage": None,
                "bankCode": "000006",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "FIDELITY BANK",
                "routingKey": "000007",
                "logoImage": None,
                "bankCode": "000007",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "POLARIS BANK",
                "routingKey": "000008",
                "logoImage": None,
                "bankCode": "000008",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "CITI BANK",
                "routingKey": "000009",
                "logoImage": None,
                "bankCode": "000009",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "ECOBANK",
                "routingKey": "000010",
                "logoImage": None,
                "bankCode": "000010",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "UNITY BANK",
                "routingKey": "000011",
                "logoImage": None,
                "bankCode": "000011",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "STANBIC IBTC BANK",
                "routingKey": "000012",
                "logoImage": None,
                "bankCode": "000012",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "GTBANK PLC",
                "routingKey": "000013",
                "logoImage": None,
                "bankCode": "000013",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "ACCESS BANK",
                "routingKey": "000014",
                "logoImage": None,
                "bankCode": "000014",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "ZENITH BANK",
                "routingKey": "000015",
                "logoImage": None,
                "bankCode": "000015",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "FIRST BANK OF NIGERIA",
                "routingKey": "000016",
                "logoImage": None,
                "bankCode": "000016",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "WEMA BANK",
                "routingKey": "000017",
                "logoImage": None,
                "bankCode": "000017",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "UNION BANK",
                "routingKey": "000018",
                "logoImage": None,
                "bankCode": "000018",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "ENTERPRISE BANK",
                "routingKey": "000019",
                "logoImage": None,
                "bankCode": "000019",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "STANDARD CHARTERED BANK",
                "routingKey": "000021",
                "logoImage": None,
                "bankCode": "000021",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "SUNTRUST BANK",
                "routingKey": "000022",
                "logoImage": None,
                "bankCode": "000022",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "PROVIDUS BANK",
                "routingKey": "000023",
                "logoImage": None,
                "bankCode": "000023",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "CORONATION MERCHANT BANK",
                "routingKey": "060001",
                "logoImage": None,
                "bankCode": "060001",
                "categoryId": "6",
                "nubanCode": None
    },
    {
        "name": "NPF MICROFINANCE BANK",
                "routingKey": "070001",
                "logoImage": None,
                "bankCode": "070001",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FORTIS MICROFINANCE BANK",
                "routingKey": "070002",
                "logoImage": None,
                "bankCode": "070002",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PAGE MFBANK",
                "routingKey": "070008",
                "logoImage": None,
                "bankCode": "070008",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ASO SAVINGS",
                "routingKey": "090001",
                "logoImage": None,
                "bankCode": "090001",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "JUBILEE LIFE",
                "routingKey": "090003",
                "logoImage": None,
                "bankCode": "090003",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SAFETRUST",
                "routingKey": "090006",
                "logoImage": None,
                "bankCode": "090006",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FIRST TRUST MORTGAGE BANK PLC",
                "routingKey": "090107",
                "logoImage": None,
                "bankCode": "090107",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NEW PRUDENTIAL BANK",
                "routingKey": "090108",
                "logoImage": None,
                "bankCode": "090108",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PAGA",
                "routingKey": "100002",
                "logoImage": None,
                "bankCode": "100002",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "PARKWAY-READYCASH",
                "routingKey": "100003",
                "logoImage": None,
                "bankCode": "100003",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "CELLULANT",
                "routingKey": "100005",
                "logoImage": None,
                "bankCode": "100005",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "ETRANZACT",
                "routingKey": "100006",
                "logoImage": None,
                "bankCode": "100006",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "STANBIC IBTC @EASE WALLET",
                "routingKey": "100007",
                "logoImage": None,
                "bankCode": "100007",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "ECOBANK XPRESS ACCOUNT",
                "routingKey": "100008",
                "logoImage": None,
                "bankCode": "100008",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "GT MOBILE",
                "routingKey": "100009",
                "logoImage": None,
                "bankCode": "100009",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "TEASY MOBILE",
                "routingKey": "100010",
                "logoImage": None,
                "bankCode": "100010",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "KUDA MICROFINANCE BANK",
                "routingKey": "090267",
                "logoImage": None,
                "bankCode": "090267",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "VT NETWORKS",
                "routingKey": "100012",
                "logoImage": None,
                "bankCode": "100012",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "KEGOW(CHAMSMOBILE)",
                "routingKey": "100036",
                "logoImage": None,
                "bankCode": "100036",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "FORTIS MOBILE",
                "routingKey": "100016",
                "logoImage": None,
                "bankCode": "100016",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "HEDONMARK",
                "routingKey": "100017",
                "logoImage": None,
                "bankCode": "100017",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "ZENITH MOBILE",
                "routingKey": "100018",
                "logoImage": None,
                "bankCode": "100018",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "FIDELITY MOBILE",
                "routingKey": "100019",
                "logoImage": None,
                "bankCode": "100019",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "MONEY BOX",
                "routingKey": "100020",
                "logoImage": None,
                "bankCode": "100020",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "EARTHOLEUM",
                "routingKey": "100021",
                "logoImage": None,
                "bankCode": "100021",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "STERLING MOBILE",
                "routingKey": "100022",
                "logoImage": None,
                "bankCode": "100022",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "TAGPAY",
                "routingKey": "100023",
                "logoImage": None,
                "bankCode": "100023",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "IMPERIAL HOMES MORTGAGE BANK",
                "routingKey": "100024",
                "logoImage": None,
                "bankCode": "100024",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "NIP VIRTUAL BANK",
                "routingKey": "999999",
                "logoImage": None,
                "bankCode": "999999",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "FINATRUST MICROFINANCE BANK",
                "routingKey": "090111",
                "logoImage": None,
                "bankCode": "090111",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SEED CAPITAL MICROFINANCE BANK",
                "routingKey": "090112",
                "logoImage": None,
                "bankCode": "090112",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TCF MICROFINANCE BANK",
                "routingKey": "090115",
                "logoImage": None,
                "bankCode": "090115",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EMPIRE TRUST MICROFINANCE BANK",
                "routingKey": "090114",
                "logoImage": None,
                "bankCode": "090114",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MICROVIS MICROFINANCE BANK ",
                "routingKey": "090113",
                "logoImage": None,
                "bankCode": "090113",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AMML MICROFINANCE BANK ",
                "routingKey": "090116",
                "logoImage": None,
                "bankCode": "090116",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BOCTRUST MICROFINANCE BANK LIMITED",
                "routingKey": "090117",
                "logoImage": None,
                "bankCode": "090117",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "WETLAND  MICROFINANCE BANK",
                "routingKey": "090120",
                "logoImage": None,
                "bankCode": "090120",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "IBILE MICROFINANCE BANK",
                "routingKey": "090118",
                "logoImage": None,
                "bankCode": "090118",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "REGENT MICROFINANCE BANK",
                "routingKey": "090125",
                "logoImage": None,
                "bankCode": "090125",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NDIORAH MICROFINANCE BANK",
                "routingKey": "090128",
                "logoImage": None,
                "bankCode": "090128",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BC KASH MICROFINANCE BANK",
                "routingKey": "090127",
                "logoImage": None,
                "bankCode": "090127",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "HASAL MICROFINANCE BANK",
                "routingKey": "090121",
                "logoImage": None,
                "bankCode": "090121",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FBNQUEST MERCHANT BANK",
                "routingKey": "060002",
                "logoImage": None,
                "bankCode": "060002",
                "categoryId": "6",
                "nubanCode": None
    },
    {
        "name": "RICHWAY MICROFINANCE BANK",
                "routingKey": "090132",
                "logoImage": None,
                "bankCode": "090132",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PERSONAL TRUST MICROFINANCE BANK",
                "routingKey": "090135",
                "logoImage": None,
                "bankCode": "090135",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MICROCRED MICROFINANCE BANK",
                "routingKey": "090136",
                "logoImage": None,
                "bankCode": "090136",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GOWANS MICROFINANCE BANK",
                "routingKey": "090122",
                "logoImage": None,
                "bankCode": "090122",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "RAND MERCHANT BANK",
                "routingKey": "000024",
                "logoImage": None,
                "bankCode": "000024",
                "categoryId": "6",
                "nubanCode": None
    },
    {
        "name": "YES MICROFINANCE BANK",
                "routingKey": "090142",
                "logoImage": None,
                "bankCode": "090142",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SAGAMU MICROFINANCE BANK",
                "routingKey": "090140",
                "logoImage": None,
                "bankCode": "090140",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MONEY TRUST MICROFINANCE BANK",
                "routingKey": "090129",
                "logoImage": None,
                "bankCode": "090129",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LAGOS BUILDING AND INVESTMENT COMPANY",
                "routingKey": "070012",
                "logoImage": None,
                "bankCode": "070012",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "GATEWAY MORTGAGE BANK",
                "routingKey": "070009",
                "logoImage": None,
                "bankCode": "070009",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "ABBEY MORTGAGE BANK",
                "routingKey": "070010",
                "logoImage": None,
                "bankCode": "070010",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "FIRST GENERATION MORTGAGE BANK",
                "routingKey": "070014",
                "logoImage": None,
                "bankCode": "070014",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "PLATINUM MORTGAGE BANK",
                "routingKey": "070013",
                "logoImage": None,
                "bankCode": "070013",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "INFINITY TRUST MORTGAGE BANK",
                "routingKey": "070016",
                "logoImage": None,
                "bankCode": "070016",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "OHAFIA MICROFINANCE BANK",
                "routingKey": "090119",
                "logoImage": None,
                "bankCode": "090119",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "XSLNCE MICROFINANCE BANK",
                "routingKey": "090124",
                "logoImage": None,
                "bankCode": "090124",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CONSUMER MICROFINANCE BANK",
                "routingKey": "090130",
                "logoImage": None,
                "bankCode": "090130",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ALLWORKERS MICROFINANCE BANK",
                "routingKey": "090131",
                "logoImage": None,
                "bankCode": "090131",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ACCION MICROFINANCE BANK",
                "routingKey": "090134",
                "logoImage": None,
                "bankCode": "090134",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "VISA MICROFINANCE BANK",
                "routingKey": "090139",
                "logoImage": None,
                "bankCode": "090139",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CHIKUM MICROFINANCE BANK",
                "routingKey": "090141",
                "logoImage": None,
                "bankCode": "090141",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "APEKS MICROFINANCE BANK",
                "routingKey": "090143",
                "logoImage": None,
                "bankCode": "090143",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CIT MICROFINANCE BANK",
                "routingKey": "090144",
                "logoImage": None,
                "bankCode": "090144",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FULLRANGE MICROFINANCE BANK",
                "routingKey": "090145",
                "logoImage": None,
                "bankCode": "090145",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FFS MICROFINANCE BANK",
                "routingKey": "090153",
                "logoImage": None,
                "bankCode": "090153",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ADDOSSER MICROFINANCE BANK",
                "routingKey": "090160",
                "logoImage": None,
                "bankCode": "090160",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FIDFUND MICROFINANCE BANK",
                "routingKey": "090126",
                "logoImage": None,
                "bankCode": "090126",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AG MORTGAGE BANK",
                "routingKey": "100028",
                "logoImage": None,
                "bankCode": "100028",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "PECANTRUST MICROFINANCE BANK",
                "routingKey": "090137",
                "logoImage": None,
                "bankCode": "090137",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BOWEN MICROFINANCE BANK",
                "routingKey": "090148",
                "logoImage": None,
                "bankCode": "090148",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FUTO MICROFINANCE BANK",
                "routingKey": "090158",
                "logoImage": None,
                "bankCode": "090158",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "REFUGE MORTGAGE BANK",
                "routingKey": "070011",
                "logoImage": None,
                "bankCode": "070011",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "BRENT MORTGAGE BANK",
                "routingKey": "070015",
                "logoImage": None,
                "bankCode": "070015",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "ROYAL EXCHANGE MICROFINANCE BANK",
                "routingKey": "090138",
                "logoImage": None,
                "bankCode": "090138",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "HACKMAN MICROFINANCE BANK",
                "routingKey": "090147",
                "logoImage": None,
                "bankCode": "090147",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TRIDENT MICROFINANCE BANK",
                "routingKey": "090146",
                "logoImage": None,
                "bankCode": "090146",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "INFINITY MICROFINANCE BANK",
                "routingKey": "090157",
                "logoImage": None,
                "bankCode": "090157",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CREDIT AFRIQUE MICROFINANCE BANK",
                "routingKey": "090159",
                "logoImage": None,
                "bankCode": "090159",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "E-BARCS MICROFINANCE BANK",
                "routingKey": "090156",
                "logoImage": None,
                "bankCode": "090156",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "VFD MFB",
                "routingKey": "090110",
                "logoImage": None,
                "bankCode": "090110",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ECOMOBILE",
                "routingKey": "100030",
                "logoImage": None,
                "bankCode": "100030",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "INNOVECTIVES KESH",
                "routingKey": "100029",
                "logoImage": None,
                "bankCode": "100029",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "EKONDO MICROFINANCE BANK",
                "routingKey": "090097",
                "logoImage": None,
                "bankCode": "090097",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "VIRTUE MICROFINANCE BANK",
                "routingKey": "090150",
                "logoImage": None,
                "bankCode": "090150",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "IRL MICROFINANCE BANK",
                "routingKey": "090149",
                "logoImage": None,
                "bankCode": "090149",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FCMB MOBILE",
                "routingKey": "100031",
                "logoImage": None,
                "bankCode": "100031",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "MUTUAL TRUST MICROFINANCE BANK",
                "routingKey": "090151",
                "logoImage": None,
                "bankCode": "090151",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OKPOGA MICROFINANCE BANK",
                "routingKey": "090161",
                "logoImage": None,
                "bankCode": "090161",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NOVA MERCHANT BANK",
                "routingKey": "060003",
                "logoImage": None,
                "bankCode": "060003",
                "categoryId": "6",
                "nubanCode": None
    },
    {
        "name": "CEMCS MICROFINANCE BANK",
                "routingKey": "090154",
                "logoImage": None,
                "bankCode": "090154",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "DAYLIGHT MICROFINANCE BANK",
                "routingKey": "090167",
                "logoImage": None,
                "bankCode": "090167",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "HAGGAI MORTGAGE BANK LIMITED",
                "routingKey": "070017",
                "logoImage": None,
                "bankCode": "070017",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "MAINSTREET MICROFINANCE BANK",
                "routingKey": "090171",
                "logoImage": None,
                "bankCode": "090171",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GREENBANK MICROFINANCE BANK",
                "routingKey": "090178",
                "logoImage": None,
                "bankCode": "090178",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FAST MICROFINANCE BANK",
                "routingKey": "090179",
                "logoImage": None,
                "bankCode": "090179",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LAPO MICROFINANCE BANK",
                "routingKey": "090177",
                "logoImage": None,
                "bankCode": "090177",
                "categoryId": "0",
                "nubanCode": None
    },
    {
        "name": "HERITAGE BANK",
                "routingKey": "000020",
                "logoImage": None,
                "bankCode": "000020",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "UNIVERSITY OF NIGERIA, NSUKKA MICROFINANCE BANK",
                "routingKey": "090251",
                "logoImage": None,
                "bankCode": "090251",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PENNYWISE MICROFINANCE BANK ",
                "routingKey": "090196",
                "logoImage": None,
                "bankCode": "090196",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ABU MICROFINANCE BANK ",
                "routingKey": "090197",
                "logoImage": None,
                "bankCode": "090197",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NIRSAL NATIONAL MICROFINANCE BANK",
                "routingKey": "090194",
                "logoImage": None,
                "bankCode": "090194",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BOSAK MICROFINANCE BANK",
                "routingKey": "090176",
                "logoImage": None,
                "bankCode": "090176",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ASTRAPOLARIS MICROFINANCE BANK",
                "routingKey": "090172",
                "logoImage": None,
                "bankCode": "090172",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "QUICKFUND MICROFINANCE BANK",
                "routingKey": "090261",
                "logoImage": None,
                "bankCode": "090261",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ALEKUN MICROFINANCE BANK",
                "routingKey": "090259",
                "logoImage": None,
                "bankCode": "090259",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "RENMONEY MICROFINANCE BANK ",
                "routingKey": "090198",
                "logoImage": None,
                "bankCode": "090198",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "STELLAS MICROFINANCE BANK ",
                "routingKey": "090262",
                "logoImage": None,
                "bankCode": "090262",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NEW DAWN MICROFINANCE BANK",
                "routingKey": "090205",
                "logoImage": None,
                "bankCode": "090205",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ALPHA KAPITAL MICROFINANCE BANK ",
                "routingKey": "090169",
                "logoImage": None,
                "bankCode": "090169",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AUCHI MICROFINANCE BANK ",
                "routingKey": "090264",
                "logoImage": None,
                "bankCode": "090264",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AB MICROFINANCE BANK ",
                "routingKey": "090270",
                "logoImage": None,
                "bankCode": "090270",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NIGERIAN NAVY MICROFINANCE BANK ",
                "routingKey": "090263",
                "logoImage": None,
                "bankCode": "090263",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "IMO STATE MICROFINANCE BANK",
                "routingKey": "090258",
                "logoImage": None,
                "bankCode": "090258",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TRUSTFUND MICROFINANCE BANK ",
                "routingKey": "090276",
                "logoImage": None,
                "bankCode": "090276",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GROOMING MICROFINANCE BANK",
                "routingKey": "090195",
                "logoImage": None,
                "bankCode": "090195",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ABOVE ONLY MICROFINANCE BANK ",
                "routingKey": "090260",
                "logoImage": None,
                "bankCode": "090260",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OLABISI ONABANJO UNIVERSITY MICROFINANCE ",
                "routingKey": "090272",
                "logoImage": None,
                "bankCode": "090272",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ADEYEMI COLLEGE STAFF MICROFINANCE BANK",
                "routingKey": "090268",
                "logoImage": None,
                "bankCode": "090268",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MEGAPRAISE MICROFINANCE BANK",
                "routingKey": "090280",
                "logoImage": None,
                "bankCode": "090280",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TAJ BANK",
                "routingKey": "000026",
                "logoImage": None,
                "bankCode": "000026",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "ARISE MICROFINANCE BANK",
                "routingKey": "090282",
                "logoImage": None,
                "bankCode": "090282",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PRESTIGE MICROFINANCE BANK",
                "routingKey": "090274",
                "logoImage": None,
                "bankCode": "090274",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GLORY MICROFINANCE BANK",
                "routingKey": "090278",
                "logoImage": None,
                "bankCode": "090278",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BAINES CREDIT MICROFINANCE BANK",
                "routingKey": "090188",
                "logoImage": None,
                "bankCode": "090188",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ACCESS(DIAMOND) BANK",
                "routingKey": "000005",
                "logoImage": None,
                "bankCode": "000005",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "PILLAR MICROFINANCE BANK",
                "routingKey": "090289",
                "logoImage": None,
                "bankCode": "090289",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SAFE HAVEN MICROFINANCE BANK",
                "routingKey": "090286",
                "logoImage": None,
                "bankCode": "090286",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AFEKHAFE MICROFINANCE BANK",
                "routingKey": "090292",
                "logoImage": None,
                "bankCode": "090292",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GLOBUS BANK",
                "routingKey": "000027",
                "logoImage": None,
                "bankCode": "000027",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "FIRST OPTION MICROFINANCE BANK",
                "routingKey": "090285",
                "logoImage": None,
                "bankCode": "090285",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "POLYUNWANA MICROFINANCE BANK",
                "routingKey": "090296",
                "logoImage": None,
                "bankCode": "090296",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OMIYE MICROFINANCE BANK",
                "routingKey": "090295",
                "logoImage": None,
                "bankCode": "090295",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ASSETMATRIX MICROFINANCE BANK",
                "routingKey": "090287",
                "logoImage": None,
                "bankCode": "090287",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TITAN TRUST BANK",
                "routingKey": "000025",
                "logoImage": None,
                "bankCode": "000025",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "LAVENDER MICROFINANCE BANK",
                "routingKey": "090271",
                "logoImage": None,
                "bankCode": "090271",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FCT MICROFINANCE BANK",
                "routingKey": "090290",
                "logoImage": None,
                "bankCode": "090290",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "IKIRE MICROFINANCE BANK",
                "routingKey": "090279",
                "logoImage": None,
                "bankCode": "090279",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PURPLEMONEY MICROFINANCE BANK",
                "routingKey": "090303",
                "logoImage": None,
                "bankCode": "090303",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ACCESS YELLO & BETA",
                "routingKey": "100052",
                "logoImage": None,
                "bankCode": "100052",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TRUSTBANC J6 MICROFINANCE BANK LIMITED",
                "routingKey": "090123",
                "logoImage": None,
                "bankCode": "090123",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SULSPAP MICROFINANCE BANK",
                "routingKey": "090305",
                "logoImage": None,
                "bankCode": "090305",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ESO-E MICROFINANCE BANK",
                "routingKey": "090166",
                "logoImage": None,
                "bankCode": "090166",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EMERALD MICROFINANCE BANK",
                "routingKey": "090273",
                "logoImage": None,
                "bankCode": "090273",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ACCESS MONEY",
                "routingKey": "100013",
                "logoImage": None,
                "bankCode": "100013",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "ALERT MICROFINANCE BANK",
                "routingKey": "090297",
                "logoImage": None,
                "bankCode": "090297",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BRIGHTWAY MICROFINANCE BANK",
                "routingKey": "090308",
                "logoImage": None,
                "bankCode": "090308",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PALMPAY",
                "routingKey": "100033",
                "logoImage": None,
                "bankCode": "100033",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "SPARKLE",
                "routingKey": "090325",
                "logoImage": None,
                "bankCode": "090325",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BALOGUN GAMBARI MICROFINANCE BANK",
                "routingKey": "090326",
                "logoImage": None,
                "bankCode": "090326",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PATRICKGOLD MICROFINANCE BANK",
                "routingKey": "090317",
                "logoImage": None,
                "bankCode": "090317",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MAYFRESH MORTGAGE BANK",
                "routingKey": "070019",
                "logoImage": None,
                "bankCode": "070019",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "TRUST MICROFINANCE BANK",
                "routingKey": "090327",
                "logoImage": None,
                "bankCode": "090327",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AL-BARAKAH MICROFINANCE BANK",
                "routingKey": "090133",
                "logoImage": None,
                "bankCode": "090133",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EYOWO",
                "routingKey": "090328",
                "logoImage": None,
                "bankCode": "090328",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EVANGEL MICROFINANCE BANK ",
                "routingKey": "090304",
                "logoImage": None,
                "bankCode": "090304",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EVERGREEN MICROFINANCE BANK",
                "routingKey": "090332",
                "logoImage": None,
                "bankCode": "090332",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OCHE MICROFINANCE BANK",
                "routingKey": "090333",
                "logoImage": None,
                "bankCode": "090333",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NUTURE MICROFINANCE BANK",
                "routingKey": "090364",
                "logoImage": None,
                "bankCode": "090364",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FIRSTMONIE WALLET",
                "routingKey": "100014",
                "logoImage": None,
                "bankCode": "100014",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "NEPTUNE MICROFINANCE BANK",
                "routingKey": "090329",
                "logoImage": None,
                "bankCode": "090329",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "U & C MICROFINANCE BANK",
                "routingKey": "090315",
                "logoImage": None,
                "bankCode": "090315",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "UNAAB MICROFINANCE BANK",
                "routingKey": "090331",
                "logoImage": None,
                "bankCode": "090331",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "IKENNE MICROFINANCE BANK",
                "routingKey": "090324",
                "logoImage": None,
                "bankCode": "090324",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MAYFAIR MICROFINANCE BANK",
                "routingKey": "090321",
                "logoImage": None,
                "bankCode": "090321",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "REPHIDIM MICROFINANCE BANK",
                "routingKey": "090322",
                "logoImage": None,
                "bankCode": "090322",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "KONTAGORA MICROFINANCE BANK",
                "routingKey": "090299",
                "logoImage": None,
                "bankCode": "090299",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CASHCONNECT MICROFINANCE BANK",
                "routingKey": "090360",
                "logoImage": None,
                "bankCode": "090360",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BIPC MICROFINANCE BANK",
                "routingKey": "090336",
                "logoImage": None,
                "bankCode": "090336",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MOLUSI MICROFINANCE BANK",
                "routingKey": "090362",
                "logoImage": None,
                "bankCode": "090362",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LEGEND MICROFINANCE BANK",
                "routingKey": "090372",
                "logoImage": None,
                "bankCode": "090372",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SEEDVEST MICROFINANCE BANK",
                "routingKey": "090369",
                "logoImage": None,
                "bankCode": "090369",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EAGLE FLIGHT MICROFINANCE BANK",
                "routingKey": "090294",
                "logoImage": None,
                "bankCode": "090294",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "THINK FINANCE MICROFINANCE BANK",
                "routingKey": "090373",
                "logoImage": None,
                "bankCode": "090373",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FETS",
                "routingKey": "100001",
                "logoImage": None,
                "bankCode": "100001",
                "categoryId": "12",
                "nubanCode": None
    },
    {
        "name": "COASTLINE MICROFINANCE BANK",
                "routingKey": "090374",
                "logoImage": None,
                "bankCode": "090374",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MINT-FINEX MFB",
                "routingKey": "090281",
                "logoImage": None,
                "bankCode": "090281",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "HEADWAY MICROFINANCE BANK",
                "routingKey": "090363",
                "logoImage": None,
                "bankCode": "090363",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ISALEOYO MICROFINANCE BANK",
                "routingKey": "090377",
                "logoImage": None,
                "bankCode": "090377",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NEW GOLDEN PASTURES MICROFINANCE BANK",
                "routingKey": "090378",
                "logoImage": None,
                "bankCode": "090378",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FSDH",
                "routingKey": "400001",
                "logoImage": None,
                "bankCode": "400001",
                "categoryId": "4",
                "nubanCode": None
    },
    {
        "name": "CORESTEP MICROFINANCE BANK",
                "routingKey": "090365",
                "logoImage": None,
                "bankCode": "090365",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FEDPOLY NASARAWA MICROFINANCE BANK",
                "routingKey": "090298",
                "logoImage": None,
                "bankCode": "090298",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FIRMUS MICROFINANCE BANK",
                "routingKey": "090366",
                "logoImage": None,
                "bankCode": "090366",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MANNY MICROFINANCE BANK",
                "routingKey": "090383",
                "logoImage": None,
                "bankCode": "090383",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "DAVODANI  MICROFINANCE BANK",
                "routingKey": "090391",
                "logoImage": None,
                "bankCode": "090391",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EK-RELIABLE MICROFINANCE BANK",
                "routingKey": "090389",
                "logoImage": None,
                "bankCode": "090389",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GTI MICROFINANCE BANK",
                "routingKey": "090385",
                "logoImage": None,
                "bankCode": "090385",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "YOBE MICROFINANCE  BANK",
                "routingKey": "090252",
                "logoImage": None,
                "bankCode": "090252",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "9 PAYMENT SOLUTIONS BANK",
                "routingKey": "120001",
                "logoImage": None,
                "bankCode": "120001",
                "categoryId": "12",
                "nubanCode": None
    },
    {
        "name": "OPAY",
                "routingKey": "100004",
                "logoImage": None,
                "bankCode": "100004",
                "categoryId": "12",
                "nubanCode": None
    },
    {
        "name": "VENTURE GARDEN NIGERIA LIMITED",
                "routingKey": "110009",
                "logoImage": None,
                "bankCode": "110009",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "RUBIES MICROFINANCE BANK",
                "routingKey": "090175",
                "logoImage": None,
                "bankCode": "090175",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MOZFIN MICROFINANCE BANK",
                "routingKey": "090392",
                "logoImage": None,
                "bankCode": "090392",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "INTERLAND MICROFINANCE BANK",
                "routingKey": "090386",
                "logoImage": None,
                "bankCode": "090386",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FINCA MICROFINANCE BANK",
                "routingKey": "090400",
                "logoImage": None,
                "bankCode": "090400",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "KONGAPAY",
                "routingKey": "100025",
                "logoImage": None,
                "bankCode": "100025",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "ILISAN MICROFINANCE BANK",
                "routingKey": "090370",
                "logoImage": None,
                "bankCode": "090370",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NWANNEGADI MICROFINANCE BANK",
                "routingKey": "090399",
                "logoImage": None,
                "bankCode": "090399",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GIREI MICROFINANACE BANK",
                "routingKey": "090186",
                "logoImage": None,
                "bankCode": "090186",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OSCOTECH MICROFINANCE BANK",
                "routingKey": "090396",
                "logoImage": None,
                "bankCode": "090396",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BRIDGEWAY MICROFINANACE BANK",
                "routingKey": "090393",
                "logoImage": None,
                "bankCode": "090393",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "KREDI MONEY MICROFINANCE BANK ",
                "routingKey": "090380",
                "logoImage": None,
                "bankCode": "090380",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SHERPERD TRUST MICROFINANCE BANK",
                "routingKey": "090401",
                "logoImage": None,
                "bankCode": "090401",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "NOWNOW DIGITAL SYSTEMS LIMITED",
                "routingKey": "100032",
                "logoImage": None,
                "bankCode": "100032",
                "categoryId": "0",
                "nubanCode": None
    },
    {
        "name": "AMAC MICROFINANCE BANK",
                "routingKey": "090394",
                "logoImage": None,
                "bankCode": "090394",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LIVINGTRUST MORTGAGE BANK PLC",
                "routingKey": "070007",
                "logoImage": None,
                "bankCode": "070007",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "M36",
                "routingKey": "100035",
                "logoImage": None,
                "bankCode": "100035",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "NNEW WOMEN MICROFINANCE BANK ",
                "routingKey": "090283",
                "logoImage": None,
                "bankCode": "090283",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GMB MICROFINANCE BANK",
                "routingKey": "090408",
                "logoImage": None,
                "bankCode": "090408",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "3LINE CARD MANAGEMENT LIMITED",
                "routingKey": "110005",
                "logoImage": None,
                "bankCode": "110005",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "TEAMAPT LIMITED",
                "routingKey": "110007",
                "logoImage": None,
                "bankCode": "110007",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "INTERSWITCH LIMITED",
                "routingKey": "110003",
                "logoImage": None,
                "bankCode": "110003",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "PAYSTACK PAYMENT LIMITED",
                "routingKey": "110006",
                "logoImage": None,
                "bankCode": "110006",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "TRUSTBOND MORTGAGE BANK",
                "routingKey": "090005",
                "logoImage": None,
                "bankCode": "090005",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "NAGARTA MICROFINANCE BANK",
                "routingKey": "090152",
                "logoImage": None,
                "bankCode": "090152",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ADVANS LA FAYETTE  MICROFINANCE BANK",
                "routingKey": "090155",
                "logoImage": None,
                "bankCode": "090155",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "STANFORD MICROFINANCE BANK",
                "routingKey": "090162",
                "logoImage": None,
                "bankCode": "090162",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FIRST ROYAL MICROFINANCE BANK",
                "routingKey": "090164",
                "logoImage": None,
                "bankCode": "090164",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PETRA MICROFINANCE BANK",
                "routingKey": "090165",
                "logoImage": None,
                "bankCode": "090165",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GASHUA MICROFINANCE BANK",
                "routingKey": "090168",
                "logoImage": None,
                "bankCode": "090168",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "RELIANCE MICROFINANCE BANK",
                "routingKey": "090173",
                "logoImage": None,
                "bankCode": "090173",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MALACHY MICROFINANCE BANK",
                "routingKey": "090174",
                "logoImage": None,
                "bankCode": "090174",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AMJU UNIQUE MICROFINANCE BANK",
                "routingKey": "090180",
                "logoImage": None,
                "bankCode": "090180",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ESAN MICROFINANCE BANK",
                "routingKey": "090189",
                "logoImage": None,
                "bankCode": "090189",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MUTUAL BENEFITS MICROFINANCE BANK",
                "routingKey": "090190",
                "logoImage": None,
                "bankCode": "090190",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "KCMB MICROFINANCE BANK",
                "routingKey": "090191",
                "logoImage": None,
                "bankCode": "090191",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MIDLAND MICROFINANCE BANK",
                "routingKey": "090192",
                "logoImage": None,
                "bankCode": "090192",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "UNICAL MICROFINANCE BANK",
                "routingKey": "090193",
                "logoImage": None,
                "bankCode": "090193",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LOVONUS MICROFINANCE BANK",
                "routingKey": "090265",
                "logoImage": None,
                "bankCode": "090265",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "UNIBEN MICROFINANCE BANK",
                "routingKey": "090266",
                "logoImage": None,
                "bankCode": "090266",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GREENVILLE MICROFINANCE BANK",
                "routingKey": "090269",
                "logoImage": None,
                "bankCode": "090269",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AL-HAYAT MICROFINANCE BANK",
                "routingKey": "090277",
                "logoImage": None,
                "bankCode": "090277",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BRETHREN MICROFINANCE BANK",
                "routingKey": "090293",
                "logoImage": None,
                "bankCode": "090293",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "EDFIN MICROFINANCE BANK",
                "routingKey": "090310",
                "logoImage": None,
                "bankCode": "090310",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FEDERAL UNIVERSITY DUTSE MICROFINANCE BANK",
                "routingKey": "090318",
                "logoImage": None,
                "bankCode": "090318",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "KADPOLY MICROFINANCE BANK",
                "routingKey": "090320",
                "logoImage": None,
                "bankCode": "090320",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MAINLAND MICROFINANCE BANK",
                "routingKey": "090323",
                "logoImage": None,
                "bankCode": "090323",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "APPLE MICROFINANCE BANK",
                "routingKey": "090376",
                "logoImage": None,
                "bankCode": "090376",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BORGU  MICROFINANCE BANK",
                "routingKey": "090395",
                "logoImage": None,
                "bankCode": "090395",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FEDERAL POLYTECHNIC NEKEDE MICROFINANCE BANK",
                "routingKey": "090398",
                "logoImage": None,
                "bankCode": "090398",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "OLOWOLAGBA MICROFINANCE BANK",
                "routingKey": "090404",
                "logoImage": None,
                "bankCode": "090404",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "BUSINESS SUPPORT MICROFINANCE BANK",
                "routingKey": "090406",
                "logoImage": None,
                "bankCode": "090406",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MKUDI",
                "routingKey": "100011",
                "logoImage": None,
                "bankCode": "100011",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "INTELLIFIN",
                "routingKey": "100027",
                "logoImage": None,
                "bankCode": "100027",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "PAYATTITUDE ONLINE",
                "routingKey": "110001",
                "logoImage": None,
                "bankCode": "110001",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "FLUTTERWAVE TECHNOLOGY SOLUTIONS LIMITED",
                "routingKey": "110002",
                "logoImage": None,
                "bankCode": "110002",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "FIRST APPLE LIMITED",
                "routingKey": "110004",
                "logoImage": None,
                "bankCode": "110004",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "CYBERSPACE LIMITED",
                "routingKey": "110014",
                "logoImage": None,
                "bankCode": "110014",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "ACCELEREX NETWORK LIMITED",
                "routingKey": "090202",
                "logoImage": None,
                "bankCode": "090202",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "HOPEPSB",
                "routingKey": "120002",
                "logoImage": None,
                "bankCode": "120002",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "BAYERO UNIVERSITY MICROFINANCE BANK",
                "routingKey": "090316",
                "logoImage": None,
                "bankCode": "090316",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "MARITIME MICROFINANCE BANK",
                "routingKey": "090410",
                "logoImage": None,
                "bankCode": "090410",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "AGOSASA MICROFINANCE BANK",
                "routingKey": "090371",
                "logoImage": None,
                "bankCode": "090371",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ZENITH EASY WALLET",
                "routingKey": "100034",
                "logoImage": None,
                "bankCode": "100034",
                "categoryId": "10",
                "nubanCode": None
    },
    {
        "name": "COOP MORTGAGE BANK",
                "routingKey": "070021",
                "logoImage": None,
                "bankCode": "070021",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "CARBON",
                "routingKey": "100026",
                "logoImage": None,
                "bankCode": "100026",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "LINKS MICROFINANCE BANK",
                "routingKey": "090435",
                "logoImage": None,
                "bankCode": "090435",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "RIGO MICROFINANCE BANK",
                "routingKey": "090433",
                "logoImage": None,
                "bankCode": "090433",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PEACE MICROFINANCE BANK",
                "routingKey": "090402",
                "logoImage": None,
                "bankCode": "090402",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SPECTRUM MICROFINANCE BANK ",
                "routingKey": "090436",
                "logoImage": None,
                "bankCode": "090436",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "GREENWICH MERCHANT BANK",
                "routingKey": "060004",
                "logoImage": None,
                "bankCode": "060004",
                "categoryId": "6",
                "nubanCode": None
    },
    {
        "name": "LOTUS BANK",
                "routingKey": "000029",
                "logoImage": None,
                "bankCode": "000029",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "TANGERINE MONEY",
                "routingKey": "090426",
                "logoImage": None,
                "bankCode": "090426",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PARALLEX BANK",
                "routingKey": "000030",
                "logoImage": None,
                "bankCode": "000030",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "SAFEGATE MICROFINANCE BANK",
                "routingKey": "090485",
                "logoImage": None,
                "bankCode": "090485",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "YCT MICROFINANCE BANK",
                "routingKey": "090466",
                "logoImage": None,
                "bankCode": "090466",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SUPPORT MICROFINANCE BANK",
                "routingKey": "090446",
                "logoImage": None,
                "bankCode": "090446",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "CBN",
                "routingKey": "000028",
                "logoImage": None,
                "bankCode": "000028",
                "categoryId": "11",
                "nubanCode": None
    },
    {
        "name": "FEDETH MICROFINANCE BANK",
                "routingKey": "090482",
                "logoImage": None,
                "bankCode": "090482",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "DOT MICROFINANCE BANK",
                "routingKey": "090470",
                "logoImage": None,
                "bankCode": "090470",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "ZIKORA MICROFINANCE BANK",
                "routingKey": "090504",
                "logoImage": None,
                "bankCode": "090504",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "SOLID ALLIANZE MICROFINANCE BANK",
                "routingKey": "090506",
                "logoImage": None,
                "bankCode": "090506",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "PREMIUM TRUST  BANK",
                "routingKey": "000031",
                "logoImage": None,
                "bankCode": "000031",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "SMARTCASH PAYMENT SERVICE BANK",
                "routingKey": "120004",
                "logoImage": None,
                "bankCode": "120004",
                "categoryId": "0",
                "nubanCode": None
    },
    {
        "name": "MONIEPOINT MICROFINANCE BANK",
                "routingKey": "090405",
                "logoImage": None,
                "bankCode": "090405",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "HOMEBASE MORTGAGE BANK",
                "routingKey": "0070024",
                "logoImage": None,
                "bankCode": "0070024",
                "categoryId": "7",
                "nubanCode": None
    },
    {
        "name": "MOMO PAYMENT SERVICE BANK ",
                "routingKey": "120003 ",
                "logoImage": None,
                "bankCode": "120003 ",
                "categoryId": "12",
                "nubanCode": None
    },
    {
        "name": "GOODNEWS MICROFINANCE BANK",
                "routingKey": "090495",
                "logoImage": None,
                "bankCode": "090495",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "FEWCHORE FINANCE COMPANY LIMITED",
                "routingKey": "050002",
                "logoImage": None,
                "bankCode": "050002",
                "categoryId": "5",
                "nubanCode": None
    },
    {
        "name": "COVENANT MICROFINANCE BANK",
                "routingKey": "070006",
                "logoImage": None,
                "bankCode": "070006",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "STATESIDE MFB",
                "routingKey": "090583",
                "logoImage": None,
                "bankCode": "090583",
                "categoryId": "9",
                "nubanCode": None
    },
    {
        "name": "TEST BANK",
                "routingKey": "999239",
                "logoImage": None,
                "bankCode": "999239",
                "categoryId": "2",
                "nubanCode": None
    },
    {
        "name": "SAFE HAVEN SANDBOX BANK",
                "routingKey": "999240",
                "logoImage": None,
                "bankCode": "999240",
                "categoryId": "9",
                "nubanCode": None
    }
]
