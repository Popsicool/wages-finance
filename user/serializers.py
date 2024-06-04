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
    )
import re


# def is_valid_date_format(date_string):
#     pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
#     return bool(pattern.match(date_string))
class UserActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        fields = ["title","amount","activity_type","created_at"]



class UserDashboardSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [ "name", "wallet", "notifications"]
    def get_name(self, obj):
        return obj.lastname
    def get_wallet(self, obj):
        return obj.wallet_balance
    def get_notifications(self, obj):
        return None

class InvestmentPlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentPlan
        fields = ["title",  "unit_share", "interest_rate", "end_date", "image"]
    
    def get_image(self, obj):
        return obj.image.url

class SetPinSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000,max_value=9999)

class NewSavingsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField()
    amount= serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    frequency = serializers.CharField()
    class Meta:
        model = UserSavings
        fields = ["id","title", "amount", "start_date","end_date", "frequency"]
    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        frequency = attrs.get("frequency").strip().upper()
        if frequency not in ["DAILY", "WEEKLY", "MONTHLY"]:
            raise serializers.ValidationError(
                'Frequency must be one of "DAILY", "WEEKLY" or "MONTHLY"')
        #! check past date
        attrs["frequency"] = frequency
        return attrs
class UserSavingsSerializers(serializers.ModelSerializer):
    class Meta:
        model = UserSavings
        fields = ["id","title", "amount", "start_date","end_date", "frequency", "saved", "goal_met"]  


class UpdateDP(serializers.Serializer):
    image = serializers.ImageField()

class AmountPinSerializer(serializers.Serializer):
    pin = serializers.IntegerField(min_value=1000,max_value=9999)
    amount = serializers.IntegerField()

class WithdrawalSeializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()
    bank_name = serializers.CharField()
    account_number = serializers.CharField()
    class Meta:
        model = Withdrawal
        fields = ["amount", "bank_name", "account_number"]
    def validate(self, attrs):
        if len(attrs["account_number"]) != 10:
            raise serializers.ValidationError("Account number must be ten digits")
        try:
            account = int(attrs["account_number"])
        except ValueError:
            raise serializers.ValidationError("Account number must digits only")
        return attrs

class CoporativeDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoporativeMembership
        fields = ["balance", "date_joined", "membership_id"]

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
        if amount < 0:
            raise serializers.ValidationError("Amount must be a positive number")
        g1 = User.objects.filter(email=guarantor1).first()
        g2 = User.objects.filter(email=guarantor2).first()
        if not g1:
            raise serializers.ValidationError("Guarantor1 not found")
        if not g2:
            raise serializers.ValidationError("Guarantor2 not found")
        g1_member = CoporativeMembership.objects.filter(user=g1).first()
        g2_member = CoporativeMembership.objects.filter(user=g2).first()
        if not g1_member:
            raise serializers.ValidationError("Guarantor1 not a valid cooporative member")
        if not g2_member:
            raise serializers.ValidationError("Guarantor2 not a valid cooporative member")
        return attrs