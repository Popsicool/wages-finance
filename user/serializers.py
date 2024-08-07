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
from datetime import date, datetime


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
                "activity_type": instance.activity_type,
                "created_at": instance.created_at,
                "source": "activities"
            }
        elif isinstance(instance, SavingsActivities):
            return {
                "title": instance.savings.type,
                "amount": instance.amount,
                "activity_type": "DEBIT" if instance.activity_type == "WITHDRAWAL" else "CREDIT",
                "created_at": instance.created_at,
                "source": "savings_activities"
            }
        elif isinstance(instance, CoporativeActivities):
            return {
                "title": f"Cooporative {instance.activity_type.lower()}",
                "amount": instance.amount,
                "activity_type": "DEBIT" if instance.activity_type == "WITHDRAWAL" else "CREDIT",
                "created_at": instance.created_at,
                "source": "coporative_activities"
            }
        return super().to_representation(instance)

class UserDashboardSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["name", "wallet", "notifications", "referal_code", "account_name", "account_number", "bank_name"]
    def get_name(self, obj):
        return obj.lastname
    def get_bank_name(self, obj):
        return "Safe Heaven Microfinance Bank"

    def get_wallet(self, obj):
        return obj.wallet_balance

    def get_notifications(self, obj):
        # TODO return count of notification
        return None


class InvestmentPlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    subscribers = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentPlan
        fields = ["id", "title",  "unit_share",
                  "interest_rate", "end_date", "image", "subscribers"]

    def get_subscribers(self, obj):
        return UserInvestments.objects.filter(investment=obj).count()

    def get_image(self, obj):
        return obj.image.url


class SetPinSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000, max_value=9999)


class NewSavingsSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()
    withdrawal_date = serializers.DateField()
    frequency = serializers.ChoiceField(choices=[("daily", "DAILY"), ("weekly", "WEEKLY"), ("monthly", "MONTHLY")], required=False)
    time = serializers.TimeField(required=False)

    class Meta:
        model = UserSavings
        fields = ["type", "amount", "start_date", "withdrawal_date", "frequency", "time"]

    def validate(self, attrs):
        time = attrs.get("time")
        withdrawal_date = attrs.get("withdrawal_date")
        frequency = attrs.get("frequency")

        if frequency:
            frequency = frequency.upper()
            if frequency not in ["DAILY", "WEEKLY", "MONTHLY"]:
                raise serializers.ValidationError('Frequency must be one of "DAILY", "WEEKLY", or "MONTHLY".')

            if frequency == "DAILY" and not time:
                raise serializers.ValidationError('Time must be provided for daily savings')

        # Check if the withdrawal_date is in the future
        if withdrawal_date and withdrawal_date <= date.today():
            raise serializers.ValidationError('Withdrawal date must be a future date.')

        if frequency:
            attrs["frequency"] = frequency
        return attrs

# class UserActivitiesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Activities
#         fields = ["title", "amount", "activity_type", "created_at"]
class UserSavingsSerializers(serializers.ModelSerializer):
    activities = serializers.SerializerMethodField()
    class Meta:
        model = UserSavings
        fields = ["type", "amount", "start_date",
                  "withdrawal_date", "frequency", "saved", "goal_met", "activities"]
    def get_activities(self, obj):
        all_savings_activities = SavingsActivities.objects.filter(savings=obj).order_by("-created_at")
        activities_list = [
            {
                "activity_type": activity.activity_type,
                "amount": activity.amount,
                "date": activity.created_at
            }
            for activity in all_savings_activities
        ]
        return activities_list


class UpdateDP(serializers.Serializer):
    image = serializers.ImageField()


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
        fields = ["balance", "date_joined", "membership_id", "activities"]
    def get_activities(self, obj):
        all_cooporative_activities = CoporativeActivities.objects.filter(user_coop=obj).order_by("-created_at")
        activities_list = [
            {
                "activity_type": activity.activity_type,
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

# class ReferalInnerSerializer(serializers.ModelSerializer):
#     class Meta:


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
    image = serializers.CharField(source="investment.image")
    start_date = serializers.CharField(source="investment.start_date")
    end_date = serializers.CharField(source="investment.end_date")
    return_on_investment = serializers.SerializerMethodField()
    expected_payout = serializers.SerializerMethodField()

    class Meta:
        model = UserInvestments
        fields = ["shares", "amount", "title", "start_date","status",
                  "end_date", "return_on_investment", "expected_payout", "image"]
    def get_return_on_investment(self, obj):
        rate = obj.investment.interest_rate
        return obj.amount * (rate / 100)
    def get_expected_payout(self, obj):
        rate = obj.investment.interest_rate
        total = (obj.amount * (rate / 100)) + obj.amount
        return total


class VerifyResetPinTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
class ChangePinSerializer(serializers.Serializer):
    current_pin = serializers.IntegerField(min_value=1000, max_value=9999)
    new_pin = serializers.IntegerField(min_value=1000, max_value=9999)