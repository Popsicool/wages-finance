from rest_framework import serializers
from .models import Activities, User, InvestmentPlan, UserInvestments


class UserActivitiesSerializer(serializers.ModelSerializer):


    class Meta:
        model = Activities
        excludes = ["user"]
        fields = "__all__"

class UserDashboardSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [ "name", "wallet", "notifications"]
    def get_name(self, obj):
        return self.lastname
    def get_wallet(self, obj):
        return self.wallet_balance
    def get_notifications(self, obj):
        return None

class InvestmentPlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = InvestmentPlan
        fields = ["title",  "unit_share", "interest_rate", "end_date"]
