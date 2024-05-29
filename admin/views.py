from rest_framework import (permissions, generics, views, filters)
from authentication.permissions import IsAdministrator
from rest_framework.response import Response
from user.models import User, Withdrawal
from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    AdminInviteSerializer,
    AdminCreateInvestmentSerializer,
    GetUsersSerializers,
    GetWithdrawalSerializers,
    RejectionReason
)
import random
import string
from utils.email import SendMail
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.shortcuts import get_object_or_404
import re
# Create your views here.

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

def is_valid_date_format(date_string):
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    return bool(pattern.match(date_string))
class AdminInviteView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = AdminInviteSerializer
    queryset = User.objects.filter()
    def post(self, request):
        serializer = AdminInviteSerializer(data=request.data, many=True)
        if serializer.is_valid():
            created = []
            administrators = Group.objects.get(name="administrator")
            accountant = Group.objects.get(name="accountant")
            customer_support = Group.objects.get(name="customer-support")
            loan_managers = Group.objects.get(name="loan-managers")
            for data in serializer.validated_data:
                email = data['email']
                role = data['role'].strip().lower()
                user_exists = User.objects.filter(email=email).exists()
                if user_exists:
                    continue
                password = generate_random_password()
                name = email.split('@')
                new_admin = User.objects.create(email=email, firstname=name[0], lastname=name[0],role="ADMIN")
                new_admin.set_password(password)
                new_admin.is_staff = True
                new_admin.is_verified = True
                if role == 'administrator':
                    new_admin.groups.add(administrators)
                elif role == 'accountant':
                    new_admin.groups.add(accountant)
                elif role == 'customer-support':
                    new_admin.groups.add(customer_support)
                elif role == 'loan-managers':
                    new_admin.groups.add(loan_managers)
                new_admin.save()
                created.append(email)
                data = {"email": email, "password": password, "role": role}
                SendMail.send_invite_mail(data)
            return Response(f"The following accounts were created {created}", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCreateInvestment(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = AdminCreateInvestmentSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            return Response(data=serializer.data, status= status.HTTP_201_CREATED)

class GetUsersView(generics.ListAPIView):
    # permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = GetUsersSerializers
    filter_backends = [filters.SearchFilter]
    search_fields = ["id", "name", "agent", "company", "amount"]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by subscription status', type=openapi.TYPE_STRING, enum=['subscribed', 'unsubscribed'], required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    def list(self, request, *args, **kwargs):
        param2 = self.request.query_params.get('start_date', None)
        param3 = self.request.query_params.get('end_date', None)
        if param2 and not is_valid_date_format(param2):
            return Response(data = {'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if param3 and not is_valid_date_format(param3):
            return Response(data = {'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        param1 = self.request.query_params.get('status', None)
        param2 = self.request.query_params.get('start_date', None)
        param3 = self.request.query_params.get('end_date', None)
        queryset = User.objects.filter(role="USERS").order_by('-created_at')
        if param1:
            param1 = param1.strip().lower()
            if param1 == 'subscribed':
                queryset = queryset.filter(is_subscribed=True)
            elif param1 == 'unsubscribed':
                queryset = queryset.filter(is_subscribed=False)
        if param2:
            start_date = datetime.strptime(param2, '%Y-%m-%d')
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date, timezone.get_default_timezone())
            queryset = queryset.filter(created_at__gte=start_date)
        if param3:
            end_date = datetime.strptime(param3, '%Y-%m-%d')
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date, timezone.get_default_timezone())
            queryset = queryset.filter(created_at__lte=end_date)
        # search_param = self.request.query_params.get('search', None)
        return queryset

class GetWithdrawals(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = GetWithdrawalSerializers
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by status', type=openapi.TYPE_STRING, enum=['PENDING', 'REJECTED', 'PROCESSING', 'SUCCESS', 'FAILED'], required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    def list(self, request, *args, **kwargs):
        param2 = self.request.query_params.get('start_date', None)
        param3 = self.request.query_params.get('end_date', None)
        if param2 and not is_valid_date_format(param2):
            return Response(data = {'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if param3 and not is_valid_date_format(param3):
            return Response(data = {'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        param1 = self.request.query_params.get('status', None)
        param2 = self.request.query_params.get('start_date', None)
        param3 = self.request.query_params.get('end_date', None)
        queryset = Withdrawal.objects.all().order_by('-created_at')
        if param1:
            param1 = param1.strip().upper()
            queryset = queryset.filter(status=param1)
        if param2:
            start_date = datetime.strptime(param2, '%Y-%m-%d')
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date, timezone.get_default_timezone())
            queryset = queryset.filter(created_at__gte=start_date)
        if param3:
            end_date = datetime.strptime(param3, '%Y-%m-%d')
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date, timezone.get_default_timezone())
            queryset = queryset.filter(created_at__lte=end_date)
        # search_param = self.request.query_params.get('search', None)
        return queryset

class ApproveWithdrawal(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        user = request.user
        withdraw = get_object_or_404(Withdrawal, pk=id)
        if withdraw.status != "PENDING":
            return Response(data={"message": "Withdrawal not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            #TODO call safehaven api
            withdraw.status = "PROCESSING"
            withdraw.admin_user = user
            withdraw.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)

class RejectWithdrawal(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = RejectionReason
    def post(self, request, id):
        user = request.user
        withdraw = get_object_or_404(Withdrawal, pk=id)
        if withdraw.status != "PENDING":
            return Response(data={"message": "Withdrawal not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            reason = serializer.validated_data["reason"]
            withdraw.status = "REJECTED"
            withdraw.message = reason
            withdraw.admin_user = user
            withdraw_user = withdraw.user
            withdraw_user.wallet_balance += withdraw.amount
            #TODO add a notification
            withdraw.save()
            withdraw_user.save()
            return Response(data={"message":"success"}, status=status.HTTP_200_OK)




        