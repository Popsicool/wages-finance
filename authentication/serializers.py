from django.utils import timezone
import re
from rest_framework import serializers
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ParseError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, smart_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from user.models import User, EmailVerification, USER_ROLES
import random
import string
from utils.email import SendMail
import re



class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=8, max_length=68, write_only=True)
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ['firstname', 'lastname', 'password', 'email', 'phone']

    def validate(self, attrs):
        firstname = attrs.get('firstname', '')
        lastname = attrs.get('lastname', '')
        password = attrs.get('password', '')
        email = attrs.get('email', "")
        phone = attrs.get('phone', "")

        if not firstname.isalpha():
            raise serializers.ValidationError("firstname must contain alphabets only")

        if not lastname.isalpha():
            raise serializers.ValidationError("lastname must contain alphabets only")

        if re.search('[A-Z]', password) is None:
            raise serializers.ValidationError("password must contain One Uppercase Alphabet")

        if re.search('[a-z]', password) is None:
            raise serializers.ValidationError("password must contain One Lowercase Alphabet")

        if re.search('[0-9]', password) is None:
            raise serializers.ValidationError("password must contain One Numeric Character")

        if re.search(r"[@$!%*#?&]", password) is None:
            raise serializers.ValidationError("password must contain One Special Character")
        if not phone.startswith("+"):
            raise serializers.ValidationError("Phone number is expected in international format.")


        return attrs

    def create(self, validated_data):
        all_chars = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(all_chars) for _ in range(6))
        while User.objects.filter(referal_code = random_string).first():
            random_string = ''.join(random.choice(all_chars) for _ in range(6))
        validated_data["referal_code"] = random_string.upper()
        return User.objects.create_user(**validated_data)

class PhoneVerificationSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=6, min_length=4, write_only=True)
    phone = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['token', 'phone']

    def validate(self, attrs):
        phone = attrs.get('phone', '')
        token = attrs.get('token', '')

        user = User.objects.filter(phone=phone).first()
        if not user:
            raise ParseError('user not found')
        verificationObj = EmailVerification.objects.filter(user=user).first()

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
        user.is_verified = True
        user.save()
        return True


class ResendVerificationMailSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get('phone')
        user = User.objects.filter(phone=phone, is_verified=False).first()
        if user:
            verification_obj = EmailVerification.objects.filter(user=user, is_verified=False).first()
            return verification_obj

        return False


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=255, min_length=3)
    password = serializers.CharField(
        max_length=68, min_length=8, write_only=True)
    firstname = serializers.CharField(
        max_length=255, min_length=3, read_only=True)
    lastname = serializers.CharField(
        max_length=255, min_length=3, read_only=True)
    role = serializers.CharField(
        max_length=255, min_length=3, read_only=True)
    pin = serializers.SerializerMethodField(read_only=True)
    is_subscribed = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id','email', 'password', 'tokens', 'firstname', 'lastname', 'role', 'pin', 'is_subscribed', 'is_verified']

    def validate(self, attrs):
        email = attrs.get('email', '')
        password = attrs.get('password', '')
        valid_user = User.objects.filter(email = email).first()
        if not valid_user:
            valid_user = User.objects.filter(phone = email).first()
            if valid_user:
                email = valid_user.email
        if not valid_user:
            raise AuthenticationFailed('invalid credentials, try again')
        if not valid_user.is_active:
            raise AuthenticationFailed('account disabled, contact admin')
        user = auth.authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed('invalid credentials, try again')
        if not user.is_verified:
            raise AuthenticationFailed('please verify your account')
        role = user.role
        return {
            'id': user.id,
            'email': user.email,
            'firstname': user.firstname,
            'lastname': user.lastname,
            'role': role,
            'tokens': user.tokens,
            'pin': user.pin,
            'is_subscribed': user.is_subscribed,
            'is_verified': user.is_verified
        }
    def get_pin(self, obj):
        return True if obj['pin'] else False


class RequestPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)
    token = serializers.CharField(min_length=1, read_only=True)
    uid64 = serializers.CharField(min_length=1, read_only=True)
    redirect_url = serializers.CharField(max_length=500)

    class Meta:
        fields = ['email', 'uid64', 'token']

    def validate(self, attrs):
        email = attrs.get('email', '')
        redirect_url = attrs.get("redirect_url", "")
        user = User.objects.filter(email=email).first()

        if not user:
            # if user account not found, don't throw error
            return False


        # encode userId as base64 uuid
        uid64 = urlsafe_base64_encode(smart_bytes(user.id))

        # generate reset token
        token = PasswordResetTokenGenerator().make_token(user)

        return {"uid64": uid64, "token": token, "email": user.email, "redirect_url":redirect_url}


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        min_length=6, max_length=68, write_only=True)
    token = serializers.CharField(
        min_length=1, write_only=True)
    uid64 = serializers.CharField(
        min_length=1, write_only=True)

    class Meta:
        fields = ['password', 'token', 'uid64']

    def validate(self, attrs):

        password = attrs.get('password')
        token = attrs.get('token')
        uid64 = attrs.get('uid64')

        # Decode base64 string
        try:
            id = force_str(urlsafe_base64_decode(uid64))
            user = User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('The reset link is invalid', 401)
        except Exception as e:
            raise AuthenticationFailed('The reset link is invalid', 401)

        # Validate password

        if re.search('[A-Z]', password) is None:
            raise serializers.ValidationError(
                "Password must contain One Uppercase Alphabet")

        if re.search('[a-z]', password) is None:
            raise serializers.ValidationError(
                "Password must contain One Lowercase Alphabet")

        if re.search('[0-9]', password) is None:
            raise serializers.ValidationError(
                "Password must contain One Numeric Character")

        if re.search(r"[@$!%*#?&]", password) is None:
            raise serializers.ValidationError(
                "Password must contain One Special Character")

        # Update password
        user.set_password(password)
        user.save()

        return (user)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        min_length=6, max_length=68, write_only=True)
    new_password = serializers.CharField(
        min_length=6, max_length=68, write_only=True)

    class Meta:
        fields = ['current_password', 'new_password']

    def validate(self, attrs):

        user = self.instance
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')

        # validate old password
        isCorrectPassword = user.check_password(current_password)
        if not isCorrectPassword :
            raise serializers.ValidationError("current password not correct")
        # Validate new password

        if re.search('[A-Z]', new_password) is None:
            raise serializers.ValidationError(
                "Password must contain One Uppercase Alphabet")

        if re.search('[a-z]', new_password) is None:
            raise serializers.ValidationError(
                "Password must contain One Lowercase Alphabet")

        if re.search('[0-9]', new_password) is None:
            raise serializers.ValidationError(
                "Password must contain One Numeric Character")

        if re.search(r"[@$!%*#?&]", new_password) is None:
            raise serializers.ValidationError(
                "Password must contain One Special Character")

        user.set_password(new_password)
        user.save()
        return user

class UpdateBvnSerializer(serializers.Serializer):
    bvn = serializers.IntegerField()
    class Meta:
        fields = ["bvn"]
    def validate(self, attrs):
        bvn = attrs["bvn"]
        if len(str(bvn)) != 11:
            raise serializers.ValidationError(
                "BVN must be 11 digits long")
        return super().validate(attrs)
class UpdateNinSerializer(serializers.Serializer):
    nin = serializers.IntegerField()
    class Meta:
        fields = ["nin"]
    def validate(self, attrs):
        bvn = attrs["nin"]
        if len(str(bvn)) != 11:
            raise serializers.ValidationError(
                "NIN must be 11 digits long")
        return super().validate(attrs)
class VerifyBVNSerializer(serializers.Serializer):
    code = serializers.CharField()
class VerifyNINSerializer(serializers.Serializer):
    _id = serializers.CharField()
    code = serializers.CharField()
    nin = serializers.IntegerField()