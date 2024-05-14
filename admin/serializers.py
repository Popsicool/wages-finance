from rest_framework import serializers

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