from rest_framework import serializers
from .models import (
    Activities,
    User,
    InvestmentPlan,
    UserInvestments,
    CoporativeMembership,
    UserSavings,
    Withdrawal,
    Loan,
    SavingsActivities,
    CoporativeActivities
)
import re
from datetime import date, timedelta
from transaction.models import Transaction


# def is_valid_date_format(date_string):
#     pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
#     return bool(pattern.match(date_string))
class UserActivitiesSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    amount = serializers.IntegerField()
    activity_type = serializers.CharField()
    created_at = serializers.DateTimeField()
    source = serializers.CharField()

    def to_representation(self, instance):
        # Customize the representation of each activity depending on the source model
        if isinstance(instance, Activities):
            return {
                "title": instance.title,
                "amount": instance.amount,
                "description": f"{instance.activity_type.lower()} of N{instance.amount} ",
                "activity_type": instance.activity_type,
                "created_at": instance.created_at,
                "source": "activities"
            }
        elif isinstance(instance, Transaction):
            return{
                "title": instance.type.title(),
                "amount": instance.amount,
                "description": instance.description,
                "activity_type": "CREDIT" if instance.type == "WALLET-CREDIT" else "DEBIT",
                "created_at": instance.created_at,
                "destination": instance.source,
                "reference": f'WF-{str(instance.id).upper()}',
                "reason": instance.message, 
                "source": "transactions",
                "status": instance.status
            }
        elif isinstance(instance, SavingsActivities):
            return {
                "title": instance.savings.type,
                "amount": instance.amount,
                "description": f"{instance.activity_type.lower()} of N{instance.amount} ",
                "activity_type": "CREDIT" if instance.activity_type == "WITHDRAWAL" else "DEBIT",
                "created_at": instance.created_at,
                "source": "savings_activities"
            }
        elif isinstance(instance, CoporativeActivities):
            return {
                "title": f"Cooporative {instance.activity_type.lower()}",
                "amount": instance.amount,
                "description": f"{instance.activity_type.lower()} of N{instance.amount} ",
                "activity_type": "CREDIT" if instance.activity_type == "WITHDRAWAL" else "DEBIT",
                "created_at": instance.created_at,
                "source": "coporative_activities"
            }
        return super().to_representation(instance)
class UserDividendsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoporativeMembership
        fields = ["monthly_dividend"]

class UserDashboardSerializer(serializers.ModelSerializer):
    wallet = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    bvn_verified = serializers.SerializerMethodField()
    pin = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id","firstname","lastname","pin","email", "wallet", "notifications", "referal_code", "account_name", "account_number", "bank_name", "is_subscribed", 'is_verified', 'bvn_verified', "phone", "profile_picture", "wages_point"]
    def get_bank_name(self, obj):
        return "Safe Haven Microfinance Bank"
    def get_bvn_verified(self, obj):
        return True if obj.bvn else False
    def get_pin(self, obj):
        return True if obj.pin else False
    def get_profile_picture(self, obj):
        return obj.profile_picture.url if obj.profile_picture else None

    def get_wallet(self, obj):
        return obj.wallet_balance

    def get_notifications(self, obj):
        # TODO return count of notification
        return None


class InvestmentPlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    subscribers = serializers.SerializerMethodField()
    # available_unit = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentPlan
        fields = ["id", "title",  "unit_share","quota",
                  "interest_rate", "image", "subscribers", "duration"]

    def get_subscribers(self, obj):
        return UserInvestments.objects.filter(investment=obj).distinct('user').count()

    def get_image(self, obj):
        return obj.image.url


class SetPinSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000, max_value=9999)


class NewSavingsSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()
    duration = serializers.IntegerField(write_only=True)
    frequency = serializers.ChoiceField(choices=[("daily", "DAILY"), ("weekly", "WEEKLY"), ("monthly", "MONTHLY")], required=False)
    time = serializers.TimeField()
    day_week = serializers.ChoiceField(required=False, choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),])
    day_month = serializers.IntegerField(required=False)
    type = serializers.CharField(read_only=True)

    class Meta:
        model = UserSavings
        fields = ["type", "amount", "start_date", "duration", "frequency", "time", "day_week", "day_month"]

    def validate(self, attrs):
        # Your existing validation logic
        day_week = attrs.get("day_week")
        day_month = attrs.get("day_month")
        duration = attrs.get("duration")
        start_date = attrs.get("start_date")
        frequency = attrs.get("frequency")

        if frequency:
            frequency = frequency.upper()
            if frequency not in ["DAILY", "WEEKLY", "MONTHLY"]:
                raise serializers.ValidationError('Frequency must be one of "DAILY", "WEEKLY", or "MONTHLY".')

            if frequency == "WEEKLY" and not day_week:
                raise serializers.ValidationError('Day of the week must be provided for weekly savings')
            if frequency == "MONTHLY" and not day_month:
                raise serializers.ValidationError('Day of the month must be provided for weekly savings')
            if day_month:
                if day_month < 1 or day_month > 31:
                    raise serializers.ValidationError('Day of the month must be between 1 - 31')

        if start_date and start_date < date.today():
            raise serializers.ValidationError('Start date must be a future date.')
        if duration < 1:
            raise serializers.ValidationError('Duration must be at least 1 month')

        attrs["frequency"] = frequency
        return attrs

    def validate_time(self, value):
        if value.minute != 0:
            raise serializers.ValidationError("Time must be on the hour (HH:00)")
        return value

    def save(self, **kwargs):
        # Calculate the withdrawal date before saving the instance
        start_date = self.validated_data.get("start_date") or date.today()
        duration = self.validated_data.pop("duration", None)  # Remove 'duration' from validated data
        if duration:
            withdrawal_date = start_date + timedelta(days=duration * 30)
            kwargs['withdrawal_date'] = withdrawal_date

        return super().save(**kwargs)

# class UserActivitiesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Activities
#         fields = ["title", "amount", "activity_type", "created_at"]
class UserSavingsSerializers(serializers.ModelSerializer):
    activities = serializers.SerializerMethodField()
    class Meta:
        model = UserSavings
        fields = ["type", "amount", "start_date","target_amount",
                  "withdrawal_date", "frequency", "saved", "goal_met", "activities", "payment_details"]
    def get_activities(self, obj):
        all_savings_activities = SavingsActivities.objects.filter(savings=obj).order_by("-created_at")
        activities_list = [
            {
                "activity_type": "DEBIT" if activity.activity_type == "WITHDRAWAL" else "CREDIT",
                "description": f"{activity.activity_type.lower()} of N{activity.amount} ",
                "amount": activity.amount,
                "date": activity.created_at
            }
            for activity in all_savings_activities
        ]
        return activities_list


class UpdateDP(serializers.Serializer):
    image = serializers.ImageField()
    def validate_image(self, value):
        """
        Validate the uploaded image.
        """
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("The file type is not an image. Please upload a valid image file.")

        # Ensure file size does not exceed 10 MB
        max_size_mb = 8
        if value.size > max_size_mb * 1024 * 1024:  # size in bytes
            raise serializers.ValidationError(f"The image file size exceeds the {max_size_mb} MB limit.")

        return value


class AmountPinSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000, max_value=9999)
    amount = serializers.IntegerField()


class WithdrawalSeializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()
    bank_code = serializers.CharField()
    account_number = serializers.CharField()
    pin = serializers.IntegerField(min_value=1000, max_value=9999, write_only=True)

    class Meta:
        model = Withdrawal
        fields = ["amount", "bank_code", "account_number", "pin"]

    def validate(self, attrs):
        if len(attrs["account_number"]) != 10:
            raise serializers.ValidationError(
                "Account number must be ten digits")
        try:
            account = int(attrs["account_number"])
        except ValueError:
            raise serializers.ValidationError(
                "Account number must digits only")
        return attrs


class CoporativeDashboardSerializer(serializers.ModelSerializer):
    activities = serializers.SerializerMethodField()
    class Meta:
        model = CoporativeMembership
        fields = ["balance", "date_joined", "membership_id", "activities", "monthly_dividend"]
    def get_activities(self, obj):
        all_cooporative_activities = CoporativeActivities.objects.filter(user_coop=obj).order_by("-created_at")
        activities_list = [
            {
                "activity_type": "DEBIT" if activity.activity_type == "WITHDRAWAL" else "CREDIT",
                "description": f"{activity.activity_type.lower()} of N{activity.amount} ",
                "amount": activity.amount,
                "date": activity.created_at
            }
            for activity in all_cooporative_activities
        ]
        return activities_list

class LoanRequestSerializer(serializers.ModelSerializer):
    guarantor1 = serializers.EmailField()
    guarantor2 = serializers.EmailField()
    amount = serializers.IntegerField()
    duration_in_months = serializers.IntegerField(required=False)

    class Meta:
        model = Loan
        fields = ["guarantor1", "guarantor2", "amount", "duration_in_months"]

    def validate(self, attrs):
        guarantor1 = attrs.get("guarantor1")
        guarantor2 = attrs.get("guarantor2")
        amount = attrs.get("amount")
        if amount <= 0:
            raise serializers.ValidationError(
                "Amount must be a positive number")
        g1 = User.objects.filter(email=guarantor1).first()
        g2 = User.objects.filter(email=guarantor2).first()
        if not g1:
            raise serializers.ValidationError("Guarantor1 not found")
        if not g2:
            raise serializers.ValidationError("Guarantor2 not found")
        g1_member = CoporativeMembership.objects.filter(user=g1).first()
        g2_member = CoporativeMembership.objects.filter(user=g2).first()
        if not g1_member:
            raise serializers.ValidationError(
                "Guarantor1 not an active cooporative member")
        if not g2_member:
            raise serializers.ValidationError(
                "Guarantor2 not an active cooporative member")
        attrs['guarantor1'] = g1
        attrs['guarantor2'] = g2
        return attrs

class AllLoansSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ["id", "amount", 'amount_repayed','status']
class LoanDetailsSerializer(serializers.ModelSerializer):
    interest = serializers.SerializerMethodField()
    class Meta:
        model = Loan
        fields = [
            'id', 'amount',
            'amount_repayed', 'balance', 'duration_in_months',
            'interest_rate', 'status', 'date_requested',
            'date_approved', 'repayment_details', 'interest'
        ]

    def get_interest(self, obj):
        """Calculate the total interest on the loan based on repayment details."""
        total_interest = 0
        if not obj.repayment_details:
            return 0
        for repayment in obj.repayment_details.values():
            payment_amount = repayment['amount']
            principal_payment = obj.amount / obj.duration_in_months
            interest_payment = payment_amount - principal_payment
            total_interest += interest_payment

        return round(total_interest)

class RepaymentSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000, max_value=9999)
    repayment_indices = serializers.ListField(
        child=serializers.IntegerField(), 
        min_length=1
    )

class ReferalSerializer(serializers.ModelSerializer):
    referals = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["referal_balance", "referals"]

    def get_referals(self, obj):
        # Fetch all users with the given referral
        refs = User.objects.filter(referal=obj)

        # Pre-fetch all relevant memberships
        memberships = CoporativeMembership.objects.filter(user__in=refs)
        memberships_dict = {
            membership.user_id: membership.date_joined for membership in memberships}

        default_picture_url = None

        return [
            {
                "name": f"{person.firstname} {person.lastname}",
                "picture": person.profile_picture.url if person.profile_picture else default_picture_url,
                "date_joined": person.created_at,
                "date_subscribed": memberships_dict.get(person.id)
            }
            for person in refs
        ]


class UserInvestment(serializers.Serializer):
    unit = serializers.IntegerField()
    pin = serializers.IntegerField(min_value=1000, max_value=9999)

    class Meta:
        model = InvestmentPlan
        fields = ["unit", "id"]


class UserInvestmentHistory(serializers.ModelSerializer):
    title = serializers.CharField(source="investment.title")
    image = serializers.CharField(source="investment.image.url")
    start_date = serializers.SerializerMethodField()
    end_date = serializers.DateField(source="due_date")
    return_on_investment = serializers.SerializerMethodField()
    expected_payout = serializers.SerializerMethodField()

    class Meta:
        model = UserInvestments
        fields = ["id","shares", "amount", "title", "start_date","status",
                  "end_date", "return_on_investment", "expected_payout", "image"]
    def get_return_on_investment(self, obj):
        rate = obj.investment.interest_rate
        return obj.amount * (rate / 100)
    def get_expected_payout(self, obj):
        rate = obj.investment.interest_rate
        total = (obj.amount * (rate / 100)) + obj.amount
        return total
    def get_start_date(self, obj):
        return obj.created_at.date()


class VerifyResetPinTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
class ChangePinSerializer(serializers.Serializer):
    current_pin = serializers.IntegerField(min_value=1000, max_value=9999)
    new_pin = serializers.IntegerField(min_value=1000, max_value=9999)