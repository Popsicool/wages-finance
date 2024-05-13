from decouple import config
import json
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import HttpResponsePermanentRedirect, HttpResponse
from django.db import transaction

from user.models import User, EmailVerification
from .serializers import (
    SignupSerializer,
    ResendVerificationMailSerializer,
    LoginSerializer,
    EmailVerificationSerializer,
    RequestPasswordResetEmailSerializer,
    SetNewPasswordSerializer,
    ChangePasswordSerializer
)
from utils.email import SendMail
from .permissions import IsUser


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
            token = User.objects.make_random_password(length=6, allowed_chars=f'0123456789')
            token_expiry = timezone.now() + timedelta(minutes=6)

            EmailVerification.objects.create(user=user, token=token, token_expiry=token_expiry)

            # Send Mail
            data = {"token": token, "firstname": user.firstname, "lastname": user.lastname, 'user': user.email}
            SendMail.send_email_verification_mail(data)

        return Response({
            "message": "Registration successful. Check email for verification code"
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
                token = User.objects.make_random_password(length=6, allowed_chars=f'0123456789')
                token_expiry = timezone.now() + timedelta(minutes=6)

                verification_obj.token = token
                verification_obj.token_expiry = token_expiry
                verification_obj.save()

                # Send Mail
                data = {
                    "token": token,
                    "firstname": verification_obj.user.firstname,
                    "lastname": verification_obj.user.lastname,
                    'user': verification_obj.user.email
                    }

                SendMail.send_email_verification_mail(data)

        return Response({
            "message": "check email for verification code",
        }, status=200)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response( serializer.data, status=status.HTTP_200_OK)


class VerifyEmail(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({"message": "success"}, status=status.HTTP_200_OK)


class RequestPasswordResetEmail(generics.GenericAPIView):
    serializer_class = RequestPasswordResetEmailSerializer

    def post(self, request):
        # validate request body
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # serializer validated_data retuns custom "False" value if encounters error
        if serializer.validated_data:
            redirect_url = serializer.validated_data['redirect_url']
            # send mail
            SendMail.send_password_reset_mail(serializer.data, request=request, redirect_url= redirect_url)

        return Response({
            'message': 'we have sent you a link to reset your password'
        }, status=status.HTTP_200_OK)



class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = ['http', 'https']


class PasswordTokenCheckAPI(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def get(self, request, uid64, token):
        try:
            frontend_url = config('FRONTEND_URL', '')
            redirect_url = f'{frontend_url}?reset=true'
            user_id = smart_str(urlsafe_base64_decode(uid64))
            user = User.objects.get(id=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return HttpResponse('<p>Invalid Token. Request a new one</p>', status=400)

            if redirect_url and len(redirect_url) > 3:
                return CustomRedirect(redirect_url + f'&token_valid=True&uid64={uid64}&token={token}')
            return HttpResponse('<p>Contact Admin. Page Not found</p>', status=400)
        except Exception:
            return HttpResponse('<p>Invalid Token. Request a new one</p>', status=400)


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

