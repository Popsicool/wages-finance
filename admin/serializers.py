from rest_framework import serializers
from user.models import InvestmentPlan, User
# from user.models import User

class AdminInviteSerializer(serializers.Serializer):
    def validate(self, attrs):
        if not 'email' in attrs.keys():
            raise serializers.ValidationError(
                "Email must be provided")
        if not 'role' in attrs.keys():
            raise serializers.ValidationError(
                "Role must be provided")
        return attrs
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=["administrator", "member"])

class AdminCreateInvestmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=255)
    image  = serializers.ImageField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    quota = serializers.IntegerField()
    interest_rate = serializers.IntegerField()
    unit_share = serializers.IntegerField()

    class Meta:
        model = InvestmentPlan
        fields = ["title", "image", "start_date", "end_date", "quota", "interest_rate", "unit_share"]


class GetUsersSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "firstname", "lastname", "email",
                  "profile_picture", "phone", "wallet_balance",
                  "wages_point", "tier", "created_at"]