from rest_framework import serializers
from django.db.models import Sum, Count, F
from user.models import (
    InvestmentPlan,
    User,
    Withdrawal,
    ForgetPasswordToken,
    UserSavings,
    UserInvestments,
    Loan,
    Activities,
    CoporativeMembership,
    CoporativeActivities,
    SavingsActivities
)
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ParseError
from django.utils import timezone
from datetime import timedelta
from transaction.models import Transaction
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.models import Group
# from user.models import User


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255, min_length=3)
    password = serializers.CharField(
        max_length=68, min_length=8, write_only=True)
    firstname = serializers.CharField(
        max_length=255, min_length=3, read_only=True)
    lastname = serializers.CharField(
        max_length=255, min_length=3, read_only=True)
    role = serializers.CharField(
        max_length=255, min_length=3, read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "password",
                  "firstname", "lastname", "role", "tokens"]

    def validate(self, attrs):
        email = attrs.get('email', '')
        password = attrs.get('password', '')
        valid_user = User.objects.filter(email=email).first()
        if not valid_user:
            raise AuthenticationFailed('invalid credentials, try again')
        if not valid_user.is_active:
            raise AuthenticationFailed('account disabled, contact super admin')
        user = auth.authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed('invalid credentials, try again')
        if not user.is_staff:
            raise AuthenticationFailed('Unauthorized login')
        role = user.groups.all()
        return {
            'id': user.id,
            'email': user.email,
            'firstname': user.firstname,
            'tokens': user.tokens(),
            'lastname': user.lastname,
            'role': [r.name for r in role] if role else None,
        }


class RequestPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)
    token = serializers.CharField(min_length=1, read_only=True)
    # uid64 = serializers.CharField(min_length=1, read_only=True)

    class Meta:
        fields = ['email', 'token']

    def validate(self, attrs):
        email = attrs.get('email', '')
        user = User.objects.filter(email=email).first()

        if not user:
            # if user account not found, don't throw error
            raise AuthenticationFailed('invalid credentials, try again')
        if not user.is_staff:
            raise AuthenticationFailed('invalid credentials, try again')

        # encode userId as base64 uuid
        # uid64 = urlsafe_base64_encode(smart_bytes(user.id))

        # generate reset token
        token = User.objects.make_random_password(
            length=4, allowed_chars=f'0123456789')
        token_expiry = timezone.now() + timedelta(minutes=6)
        forget_pass = ForgetPasswordToken.objects.filter(user=user).first()
        if not forget_pass:
            forget_pass = ForgetPasswordToken.objects.create(
                user=user,
                token=token,
                token_expiry=token_expiry)
        else:
            forget_pass.is_used = False
            forget_pass.token = token
            forget_pass.token_expiry = token_expiry
        forget_pass.save()

        return {"token": token, "email": user.email}


class EmailCodeVerificationSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=4, min_length=4, write_only=True)
    email = serializers.EmailField(write_only=True)
    uuid = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['token', 'email', 'uuid']

    def validate(self, attrs):
        email = attrs.get('email', '')
        token = attrs.get('token', '')

        user = User.objects.filter(email=email).first()
        if not user:
            raise ParseError('user not found')
        verificationObj = ForgetPasswordToken.objects.filter(user=user).first()

        if not verificationObj:
            raise ParseError('user not found')

        if verificationObj.token != token:
            raise ParseError('wrong token')

        if verificationObj.is_used:
            raise ParseError('token expired')

        if verificationObj.token_expiry < timezone.now():
            raise ParseError('token expired')

        verificationObj.is_used = True
        verificationObj.token_expiry = timezone.now()
        verificationObj.save()
        attrs['uid64'] = urlsafe_base64_encode(smart_bytes(user.id))
        return attrs


class UpdateAdminSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["active", 'inactive'], required=False)
    role = serializers.ChoiceField(
        choices=["Administrator", "Accountant", "Customer-support", "Loan-manager"], required=False)


class GetAdminMembersSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "firstname", "lastname", "email", "is_active", "role"]

    def get_role(self, obj):
        groups = obj.groups.all()
        if groups.exists():
            return groups[0].name
        return None


class AdminInviteSerializer(serializers.Serializer):
    def validate(self, attrs):
        if not 'email' in attrs.keys():
            raise serializers.ValidationError(
                "Email must be provided")
        # if not 'role' in attrs.keys():
        #     raise serializers.ValidationError(
        #         "Role must be provided")
        return attrs
    email = serializers.EmailField()
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    role = serializers.ChoiceField(
        choices=["Administrator", "Accountant", "Customer-support", "Loan-manager"], required=False)


class AdminTransactionSerializer(serializers.ModelSerializer):
    firstname = serializers.CharField(source="user.firstname")
    email = serializers.EmailField(source="user.email")
    user_id = serializers.IntegerField(source="user.id")
    lastname = serializers.CharField(source="user.lastname")
    phone = serializers.CharField(source="user.phone")

    class Meta:
        model = Transaction
        fields = ["id", "firstname", "lastname", "email", "phone",
                  "amount", "status", "description", "user_id", "type"]


class AdminCreateInvestmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=255)
    image = serializers.ImageField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    quota = serializers.IntegerField()
    interest_rate = serializers.IntegerField()
    unit_share = serializers.IntegerField()
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = InvestmentPlan
        fields = ["title", "image", "start_date", "end_date",
                  "quota", "interest_rate", "unit_share", "is_active"]

class AdminSingleInvestment(serializers.ModelSerializer):
    investor_count = serializers.SerializerMethodField(read_only=True)
    amount_invested = serializers.SerializerMethodField(read_only=True)
    days_left = serializers.SerializerMethodField(read_only=True)
    title = serializers.CharField(max_length=255, required=False)
    image = serializers.ImageField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    quota = serializers.IntegerField(required=False)
    interest_rate = serializers.IntegerField(required=False)
    unit_share = serializers.IntegerField(required=False)
    class Meta:
        model = InvestmentPlan
        fields = ["investor_count", "amount_invested", "days_left",
                  "title", "image", "start_date", "end_date",
                  "quota", "interest_rate", "unit_share",]
    def get_amount_invested(self, obj):
        all_investments = UserInvestments.objects.filter(investment=obj)
        amt = all_investments.aggregate(
            total_amount=Sum('amount'))['total_amount'] or 0
        return amt
    def get_investor_count(self, obj):
        return UserInvestments.objects.filter(investment=obj).count()
    def get_days_left(self, obj):
        today = timezone.now()
        days = (obj.end_date - today.date()).days
        return days

class SingleInvestmentInvestors(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id')
    name = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()
    class Meta:
        model = UserInvestments
        fields = ["id","name", "amount", "due_date", "roi", "status"]
    def get_name(self, obj):
        return f"{obj.user.firstname} {obj.user.lastname}"
    def get_roi(self, obj):
        roi = obj.amount * (obj.investment.interest_rate / 100)
        return roi
class GetUsersSerializers(serializers.ModelSerializer):
    membership_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "firstname", "lastname",
                  "email", "membership_status", "phone"]

    def get_membership_status(self, obj):
        if obj.is_subscribed:
            return "ACTIVE"
        return "INACTIVE"


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        fields = ['title', 'activity_type', 'created_at', 'amount']


class GetSingleUserSerializer(serializers.ModelSerializer):
    membership_status = serializers.SerializerMethodField()
    membership_id = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    total_savings = serializers.SerializerMethodField()
    total_investment = serializers.SerializerMethodField()
    outstanding_loan = serializers.SerializerMethodField()
    total_coop_savings = serializers.SerializerMethodField()
    referal_count = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()
    referees = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "firstname", "lastname", "phone", "email", "profile_picture",
            "wallet_balance", "tier", "created_at", "referal_count",
            "membership_id", "membership_status", "total_savings", "outstanding_loan",
            "total_investment","total_coop_savings", "wages_point", "referal_balance", "total_referal_balance",
            "transactions", "referees"
        ]

    def get_membership_status(self, obj):
        if not obj.is_subscribed:
            return "INACTIVE"
        if not CoporativeMembership.objects.filter(user=obj, is_active=True).first():
            return "INACTIVE"
        return "ACTIVE"

    def get_membership_id(self, obj):
        return getattr(obj.coporativemembership, 'membership_id', None) if obj.is_subscribed else None

    def get_profile_picture(self, obj):
        return obj.profile_picture.url if obj.profile_picture else None

    def aggregate_field(self, model, user, field, filter_kwargs=None):
        if filter_kwargs is None:
            filter_kwargs = {}
        filter_kwargs['user'] = user
        total = model.objects.filter(
            **filter_kwargs).aggregate(total=Sum(field)).get('total', 0)
        return total if total is not None else 0

    def get_total_investment(self, obj):
        return self.aggregate_field(UserInvestments, obj, 'amount')

    def get_outstanding_loan(self, obj):
        return self.aggregate_field(Loan, obj, 'balance', {'status__in': ["APPROVED", "OVER-DUE"]})

    def get_total_savings(self, obj):
        return self.aggregate_field(UserSavings, obj, 'saved')

    def get_referal_count(self, obj):
        return User.objects.filter(referal=obj).count()
    def get_total_coop_savings(self, obj):
        cop = CoporativeMembership.objects.filter(user=obj).first()
        if not cop:
            return 0
        return cop.balance

    def get_transactions(self, obj):
        activities = Activities.objects.filter(
            user=obj).order_by('-created_at')[:5]
        return ActivitySerializer(activities, many=True).data
    def get_referees(self, obj):
        referees = obj.user_set.filter(is_subscribed=True)
        referees_list = []

        for referal in referees:
            referal_data = {
                'id': referal.id,
                'firstname': referal.firstname,
                'lastname': referal.lastname,
                'profile_picture': referal.profile_picture.url if referal.profile_picture else None,
                'created_at': referal.created_at,
            }
            referees_list.append(referal_data)

        return referees_list


class GetWithdrawalSerializers(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Withdrawal
        fields = ["id", "amount", "bank_name",
                  "account_number", "status", "message", "user"]

    def get_user(self, obj):
        return f"{obj.user.firstname} {obj.user.lastname}"


class RejectionReason(serializers.Serializer):
    reason = serializers.CharField()


class CoporativeUsersSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "firstname", "lastname", "phone", "email", "status"]


class GetCooperativeUsersSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id')
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')
    coporative_balance = serializers.FloatField(source='balance')
    phone = serializers.CharField(source='user.phone')

    class Meta:
        model = CoporativeMembership
        fields = ["id", "name", "email", "coporative_balance", "phone"]

    def get_name(self, obj):
        return f"{obj.user.firstname} {obj.user.lastname}"


class SavingsTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone')
    email = serializers.EmailField(source='user.email')
    end_date = serializers.DateField(source="withdrawal_date")
    plan = serializers.CharField(source="type")
    amount_per_savings = serializers.IntegerField(source="amount")

    class Meta:
        model = UserSavings
        fields = ["id", "plan", "name", "phone", "email", "saved",
                  "amount_per_savings", "frequency", "start_date", "end_date", "target_amount"]

    def get_name(self, obj):
        return f"{obj.user.firstname} {obj.user.lastname}"


class SingleSavingsSerializer(serializers.ModelSerializer):
    amount_per_savings = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = UserSavings
        fields = ["title", "user", "saved", "frequency",
                  "start_date", "end_date", "amount_per_savings", "target_amount"]

    def get_title(self, obj):
        return obj.type

    def get_end_date(self, obj):
        return obj.withdrawal_date

    def get_amount_per_savings(self, obj):
        return obj.amount
        '''
        start_date = obj.start_date
        end_date = obj.withdrawal_date
        amount = obj.amount
        frequency = obj.frequency

        days_diff = (end_date - start_date).days

        if frequency == 'DAILY':
            number_of_periods = days_diff
        elif frequency == 'WEEKLY':
            number_of_periods = days_diff // 7
        elif frequency == 'MONTHLY':
            # Approximate months, you can refine it as needed
            number_of_periods = days_diff // 30
        else:
            return None  # In case frequency is not recognized

        if number_of_periods == 0:  # To handle division by zero
            return amount

        return amount / number_of_periods
        '''


class AdminLoanList(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    firstname = serializers.CharField(source="user.firstname")
    lastname = serializers.CharField(source="user.lastname")
    phone = serializers.CharField(source="user.phone")
    email = serializers.CharField(source="user.email")
    guarantors = serializers.SerializerMethodField()
    # guarantor_2 = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ["id", "user_id", "firstname", "lastname", "amount",
                  "date_requested", "phone", "email", "profile_picture",
                  "duration_in_months", "interest_rate",
                  "date_approved", "status", "guarantors"]

    def get_guarantors(self, obj):
        guarantors = []
        if obj.guarantor1:
            details1 = {
                "id": obj.guarantor1.id,
                "name": f"{obj.guarantor1.firstname} {obj.guarantor1.lastname}",
                "email": obj.guarantor1.email,
                "phone": obj.guarantor1.phone,
                "status": obj.guarantor1_agreed
            }
            guarantors.append(details1)
        if obj.guarantor2:
            details2 = {
                "id": obj.guarantor2.id,
                "name": f"{obj.guarantor2.firstname} {obj.guarantor2.lastname}",
                "email": obj.guarantor2.email,
                "phone": obj.guarantor2.phone,
                "status": obj.guarantor2_agreed
            }
            guarantors.append(details2)
        return guarantors

    def get_profile_picture(self, obj):
        return obj.user.profile_picture.url if obj.user.profile_picture else None


class CustomReferal(serializers.Serializer):
    referal_code = serializers.CharField(max_length=50)


class AdminSingleUserCoporativeDetails(serializers.ModelSerializer):
    class Meta:
        model = CoporativeActivities
        fields = ["created_at", "amount", "balance"]


class AdminUserInvestmentSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(source="investment.title")
    duration = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()

    class Meta:
        model = UserInvestments
        fields = ['plan', 'amount', 'duration', 'roi', 'due_date', 'status']

    def get_roi(self, obj):
        roi = obj.amount * (obj.investment.interest_rate / 100)
        return roi

    def get_duration(self, obj):
        return 6


class AdminUserInvestmentSerializerHistory(serializers.ModelSerializer):
    plan = serializers.CharField(source="investment.title")
    duration = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()

    class Meta:
        model = UserInvestments
        fields = ['plan', 'amount', 'duration', 'roi', 'due_date', 'status']

    def get_roi(self, obj):
        roi = obj.amount * (obj.investment.interest_rate / 100)
        return roi

    def get_duration(self, obj):
        return 6


class AdminUserSavingsDataSerializers(serializers.ModelSerializer):
    amount_per_Savings = serializers.SerializerMethodField()
    amount_saved = serializers.SerializerMethodField()
    class Meta:
        model = UserSavings
        fields = ["type", "cycle", 'amount_per_Savings', "target_amount", "amount_saved"]
    def get_amount_per_Savings(self, obj):
        return obj.amount
    def get_amount_saved(self, obj):
        return obj.saved


class AdminUserSavingsBreakdown(serializers.ModelSerializer):
    class Meta:
        model = SavingsActivities
        fields = ["created_at", "amount", "balance"]
class AdminUserCoporativeBreakdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoporativeActivities
        fields = ["created_at", "amount", "balance"]


class AdminReferralList(serializers.ModelSerializer):
    referral_count = serializers.SerializerMethodField()
    referees = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'firstname', 'lastname', 'total_referal_balance', 'referral_count', 'referees']

    def get_referral_count(self, obj):
        # Use obj.user_set instead of querying the database again.
        return obj.user_set.filter(is_subscribed=True).count()

    def get_referees(self, obj):
        referees = obj.user_set.filter(is_subscribed=True)
        referees_list = []

        for referal in referees:
            referal_data = {
                'id': referal.id,
                'firstname': referal.firstname,
                'lastname': referal.lastname,
                'profile_picture': referal.profile_picture.url if referal.profile_picture else None,
                'created_at': referal.created_at,
            }
            referees_list.append(referal_data)

        return referees_list