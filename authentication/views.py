from decouple import config
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import HttpResponsePermanentRedirect, HttpResponse
from django.db import transaction

from user.models import User, EmailVerification, TIERS_CHOICE, ForgetPasswordToken
from .serializers import (
    SignupSerializer,
    ResendVerificationMailSerializer,
    LoginSerializer,
    PhoneVerificationSerializer,
    RequestPasswordResetPhoneSerializer,
    SetNewPasswordSerializer,
    ChangePasswordSerializer,
    UpdateBvnSerializer,
    VerifyBVNSerializer,
    UpdateNinSerializer,
    VerifyNINSerializer,
    PhoneCodeVerificationSerializer,
)
from utils.email import SendMail
from utils.sms import SendSMS
from utils.safehaven import safe_validate, safe_initiate, create_safehaven_account
from .permissions import IsUser
from user.consumers import send_socket_user_notification


class SignupView(generics.GenericAPIView):
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # check that user doesn't exist
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if user:
            return Response({
                "status_code": 400,
                "error": "User with email already exists",
                "payload": []
            }, status.HTTP_400_BAD_REQUEST)
        phone = User.objects.filter(phone=serializer.validated_data['phone']).first()
        if phone:
            return Response({
                "status_code": 400,
                "error": "User with phone number already exists",
                "payload": []
            }, status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # persist user in db
            user = serializer.save()
            # generate email verification token
            # token = User.objects.make_random_password(length=4, allowed_chars=f'0123456789')
            token = "1234"
            token_expiry = timezone.now() + timedelta(minutes=6)
            EmailVerification.objects.create(user=user, token=token, token_expiry=token_expiry)
            # data = {"token": token, 'number': user.phone}
            # SendSMS.sendVerificationCode(data)
        return Response({
            "message": "Registration successful"
        }, status=status.HTTP_201_CREATED)


class ResendVerificationMail(generics.GenericAPIView):
    serializer_class = ResendVerificationMailSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification_obj = serializer.validated_data

        with transaction.atomic():
            if verification_obj:
                # generate email verification token
                token = User.objects.make_random_password(length=4, allowed_chars=f'0123456789')
                token_expiry = timezone.now() + timedelta(minutes=6)

                verification_obj.token = token
                verification_obj.token_expiry = token_expiry
                verification_obj.save()
                data = {"token": token, 'number': verification_obj.user.phone}
                SendSMS.sendVerificationCode(data)

        return Response({
            "message": "check phone for verification code",
        }, status=200)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response( serializer.data, status=status.HTTP_200_OK)


class VerifyPhone(generics.GenericAPIView):
    serializer_class = PhoneVerificationSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({"message": "success"}, status=status.HTTP_200_OK)





class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = ['http', 'https']


class RequestPasswordResetPhoneView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetPhoneSerializer

    def post(self, request):
        # validate request body
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        # serializer validated_data retuns custom "False" value if encounters error
        if serializer.validated_data:
            # send sms
            data = {"token": serializer.validated_data["token"], 'number': serializer.validated_data["phone"]}
            SendSMS.sendVerificationCode(data)
        return Response({
            'message': 'we have sent you a code to reset your password'
        }, status=status.HTTP_200_OK)
# class PasswordTokenCheckAPI(generics.GenericAPIView):
#     serializer_class = SetNewPasswordSerializer

#     def get(self, request, uid64, token):
#         try:
#             frontend_url = config('FRONTEND_URL', '')
#             redirect_url = f'{frontend_url}?reset=true'
#             user_id = smart_str(urlsafe_base64_decode(uid64))
#             user = User.objects.get(id=user_id)

#             if not PasswordResetTokenGenerator().check_token(user, token):
#                 return HttpResponse('<p>Invalid Token. Request a new one</p>', status=400)

#             if redirect_url and len(redirect_url) > 3:
#                 return CustomRedirect(redirect_url + f'&token_valid=True&uid64={uid64}&token={token}')
#             return HttpResponse('<p>Contact Admin. Page Not found</p>', status=400)
#         except Exception:
#             return HttpResponse('<p>Invalid Token. Request a new one</p>', status=400)

class VerifyPasswordResetCode(generics.GenericAPIView):
    serializer_class = PhoneCodeVerificationSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(data=data, status=status.HTTP_200_OK)
class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer
    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'message': 'Password reset successful'}, status=status.HTTP_200_OK)


class ChangePasswordAPIView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        serializer = self.serializer_class(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({'message': 'password change successful'}, status=status.HTTP_200_OK)


class SetBvnView(generics.GenericAPIView):
    serializer_class = UpdateBvnSerializer
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        if user.bvn:
            return Response({"message": "bvn already captured"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        # call safehaven endpoint
        numn = serializer.validated_data["bvn"]
        data = {'type':"BVN", "number": numn}
        safe_status, resp = safe_initiate(data)
        if safe_status:
            user.bvn_verify_details = resp
            user.save()
            return Response(data={"message": "success"}, status=status.HTTP_200_OK)
        return Response(data={"message": resp}, status=status.HTTP_400_BAD_REQUEST)


class VerifyBVNView(generics.GenericAPIView):
    serializer_class = VerifyBVNSerializer
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        if user.bvn:
            return Response({"message": "bvn already captured"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.bvn_verify_details:
            return Response({"message":"Use BVN initialization endpoint first"}, status=status.HTTP_400_BAD_REQUEST)
        user_det = dict(user.bvn_verify_details)
        _id = user_det["_id"]
        code = user_det["otpId"]
        # code = serializer.validated_data["code"]
        data = {"_id":_id, "otp":code, "type":"BVN"}
        # call safehaven verification endpoint
        verify_status, verify_message = safe_validate(data)
        if not verify_status:
            return Response(data={"message": verify_message}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            user.bvn = verify_message["bvn"]
            user.bvn_verify_details = verify_message
            user.tier = TIERS_CHOICE[1][0]
            user.is_verified = True
            acc_data = {
                "phone": user.phone,
                "email": user.email,
                "bvn": verify_message["bvn"],
                "_id": user_det["_id"],
                "otp": user_det["otpId"]
                }
            account_number, account_name = create_safehaven_account(acc_data)
            user.account_number = account_number
            user.account_name = account_name
            data = {
                "account_number": user.account_number,
                "account_name":user.account_name,
                'bvn_verified': True
            }
            send_socket_user_notification(user.id,data)
            user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)

class SetNinView(generics.GenericAPIView):
    serializer_class = UpdateNinSerializer
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        if user.nin:
            return Response({"message": "nin already captured"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        # call safehaven endpoint
        numn = serializer.validated_data["nin"]
        data = {'type':"NIN", "number": numn}
        safe_status, _id = safe_initiate(data)
        if safe_status:
            return Response(data=_id, status=status.HTTP_200_OK)
        return Response(data=_id, status=status.HTTP_400_BAD_REQUEST)

class VerifyNINView(generics.GenericAPIView):
    serializer_class = VerifyNINSerializer
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        if user.nin:
            return Response({"message": "nin already captured"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        _id = serializer.validated_data["_id"]
        code = serializer.validated_data["code"]
        data = {"_id":_id, "token":code, "type":"NIN"}
        # call safehaven verification endpoint
        verify_status, verify_message = safe_validate(data)
        if not verify_status:
            return Response(data={"message": verify_message}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            user.nin = serializer.validated_data["nin"]
            user.tier = TIERS_CHOICE[2][0]
            user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)
