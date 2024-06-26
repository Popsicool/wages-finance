from rest_framework import (permissions, generics, views, filters)
from authentication.permissions import IsAdministrator
from rest_framework.response import Response
from user.models import (User,
                         Withdrawal,
                         CoporativeMembership,
                         UserSavings)
from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_auto_schema
from notification.models import Notification
from django.db.models import Sum, Count, Case, When, Value, BooleanField, Q
from drf_yasg import openapi
from utils.pagination import CustomPagination
from .serializers import (
    AdminLoginSerializer,
    AdminInviteSerializer,
    AdminCreateInvestmentSerializer,
    GetUsersSerializers,
    GetWithdrawalSerializers,
    RejectionReason,
    RequestPasswordResetEmailSerializer,
    EmailCodeVerificationSerializer,
    GetSingleUserSerializer,
    GetCooperativeUsersSerializer,
    SavingsTypeSerializer,
    SingleSavingsSerializer
)
import random
import string
from utils.email import SendMail
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
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



class AdminLoginView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        return Response(validated_data, status=status.HTTP_200_OK)

class RequestPasswordResetEmailView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetEmailSerializer

    def post(self, request):
        # validate request body
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # serializer validated_data retuns custom "False" value if encounters error
        if serializer.validated_data:

            # send mail
            SendMail.send_password_reset_mail(serializer.data)

        return Response({
            'message': 'we have sent you a link to reset your password'
        }, status=status.HTTP_200_OK)

class VerifyEmailResetCode(generics.GenericAPIView):
    serializer_class = EmailCodeVerificationSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(data=data, status=status.HTTP_200_OK)

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
class GetSingleUserView(generics.GenericAPIView):
    serializer_class = GetSingleUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        user = get_object_or_404(User, pk=id)
        serializer = self.serializer_class(instance=user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

class GetUsersView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = GetUsersSerializers
    filter_backends = [filters.SearchFilter]
    search_fields = ["id", "firstname", "lastname", "email"]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by subscription status', type=openapi.TYPE_STRING, enum=['active', 'inactive'], required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        param1 = self.request.query_params.get('status', None)
        queryset = User.objects.filter(role="USERS").order_by('-created_at')
        if param1:
            param1 = param1.strip().lower()
            if param1 == 'active':
                queryset = queryset.filter(is_subscribed=True)
            elif param1 == 'inactive':
                queryset = queryset.filter(is_subscribed=False)
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
            new_notification = Notification.objects.create(
                user = withdraw.user,
                title = "Withdrawal Approved",
                text = f"Your withdrawal request of {withdraw.amount} has been approved"
            )
            new_notification.save()
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
            new_notification = Notification.objects.create(
                user = withdraw_user,
                title = "Withdrawal request rejected",
                text = f"Your withdrawal request of {withdraw.amount} as been rejected because {reason}"
            )
            new_notification.save()
            withdraw.save()
            withdraw_user.save()
            return Response(data={"message":"success"}, status=status.HTTP_200_OK)

class SuspendAccount(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        user = get_object_or_404(User, pk=id)
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
class UnSuspendAccount(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        user = get_object_or_404(User, pk=id)
        user.is_active = True
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GetCooperativeUsersView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = GetCooperativeUsersSerializer
    filter_backends = [filters.SearchFilter]
    queryset = CoporativeMembership.objects.filter(is_active=True).order_by('-date_joined')
    search_fields = ["user__firstname", "user__lastname", "user__email"]

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminCoporateSavingsDashboard(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request):
        coporative_members = CoporativeMembership.objects.filter(is_active=True)
        total_balance = coporative_members.aggregate(total=Sum('balance'))['total'] or 0
        active_members_count = coporative_members.count()

        resp = {
            "total": total_balance,
            "count": active_members_count
        }

        return Response(resp, status=status.HTTP_200_OK)

class AdminSavingsStatsView(views.APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        # Aggregating data
        savings_data = UserSavings.objects.aggregate(
            unique_users_active_savings=Count('user', distinct=True, filter=Q(is_active=True)),
            total_saved_active=Sum('saved', filter=Q(is_active=True)),
            total_saved_all=Sum('saved'),
            savings_count_per_title=Count('id', distinct=True),
            unique_users_per_title=Count('user', distinct=True),
            total_saved_per_title=Sum('saved')
        )

        # Separate query to get counts and sums grouped by title
        title_aggregates = UserSavings.objects.values('title').annotate(
            savings_count_per_title=Count('id'),
            unique_users_per_title=Count('user', distinct=True),
            total_saved_per_title=Sum('saved')
        )

        # Formatting the title aggregates into a dictionary
        title_data = {}
        for item in title_aggregates:
            title_data[item['title']] = {
                'savings_count': item['savings_count_per_title'],
                'unique_users': item['unique_users_per_title'],
                'total_saved': item['total_saved_per_title']
            }

        data = {
            'unique_users_active_savings': savings_data['unique_users_active_savings'],
            'total_saved_active': savings_data['total_saved_active'],
            'total_saved_all': savings_data['total_saved_all'],
            'title_data': title_data
        }

        return Response(data)

class SavingsType(generics.GenericAPIView):
    serializer_class = SavingsTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination
    def get(self, request, name):
        queryset = UserSavings.objects.filter(title=name.strip().upper()).order_by("-created_at")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

class AdminSingleSavings(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = SingleSavingsSerializer
    def get(self, request, id):
        queryset = get_object_or_404(UserSavings, pk=id)
        serializer = self.serializer_class(queryset)
        return Response(data=serializer.data, status=status.HTTP_200_OK)