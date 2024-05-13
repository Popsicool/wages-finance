from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import MinLengthValidator
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
    email                       = models.EmailField(max_length=255, unique=True, db_index=True)
    phone                       = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_verified                 = models.BooleanField(default=False)
    is_active                   = models.BooleanField(default=True)
    is_staff                    = models.BooleanField(default=False)
    is_subscribed = models.BooleanField(default=False)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wages_point = models.IntegerField(default=0)
    referal_code = models.CharField(max_length=10, blank=True, null=True)
    bvn = models.CharField(max_length=15, blank=True, null=True)
    nin = models.CharField(max_length=15, blank=True, null=True)
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