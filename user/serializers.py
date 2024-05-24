from rest_framework import serializers
from .models import Activities, User, InvestmentPlan, UserInvestments


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


class UpdateDP(serializers.Serializer):
    image = serializers.ImageField()
# class SetPinSerializer(serializers.Field):
#     def to_internal_value(self, data):
#         try:
#             value = int(data)
#             if len(str(value)) != 4:
#                 raise serializers.ValidationError("Field must be a four-digit integer.")
#             return value
#         except ValueError:
#             raise serializers.ValidationError("Invalid integer value.")

#     def to_representation(self, value):
#         return value
'''
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE2NjIyMTk2LCJpYXQiOjE3MTY1MzU3OTYsImp0aSI6Ijg0OTZhODhlNWExZDQyM2RhNDgyNWViNTllNmQ2M2VlIiwidXNlcl9pZCI6Mn0.wKKZ3XLU8iij_XuuNepIFTSYUxCHttpBIvQBm5DQ93g
'''