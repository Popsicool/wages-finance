from rest_framework import (permissions, generics, views, filters)
from authentication.permissions import IsAdministrator
from rest_framework.response import Response
from user.models import (User,
                         Withdrawal,
                         CoporativeMembership,
                         UserSavings,
                         InvestmentPlan,
                         UserInvestments,
                         Loan,
                         CoporativeActivities,
                         SavingsActivities,
                         Activities,
                         InvestmentCancel,
                         SavingsCancel
                         )
from django.contrib.auth.models import Group
from django.utils.dateparse import parse_date
from drf_yasg.utils import swagger_auto_schema
from notification.models import Notification
from django.db.models import Sum, Count, Case, When, Value, BooleanField, Q
from drf_yasg import openapi
from utils.pagination import CustomPagination
from datetime import timedelta
from django.utils.timezone import make_aware
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
    SingleSavingsSerializer,
    AdminLoanList,
    UpdateAdminSerializer,
    GetAdminMembersSerializer,
    AdminTransactionSerializer,
    CustomReferal,
    AdminSingleUserCoporativeDetails,
    AdminUserInvestmentSerializer,
    AdminUserInvestmentSerializerHistory,
    AdminUserSavingsDataSerializers,
    AdminUserSavingsBreakdownSerializer,
    AdminUserCoporativeBreakdownSerializer,
    AdminReferralList,
    AdminSingleInvestment,
    SingleInvestmentInvestors,
    AdminUserSavingsInterestSerializer
)
from transaction.models import Transaction
import random
import string
from utils.email import SendMail
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Subquery, OuterRef
from datetime import datetime, date
from django.shortcuts import get_object_or_404
import re
from django.utils.timezone import now
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


class CustomeUserView(generics.GenericAPIView):
    serializer_class = CustomReferal
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def post(self, request, id):
        user = get_object_or_404(User, pk=id)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        ref_code = serializer.validated_data["referal_code"].upper()
        already_exists = User.objects.filter(referal_code=ref_code).first()
        if already_exists:
            return Response(data={"message": "reference code already exist"}, status=status.HTTP_400_BAD_REQUEST)
        user.referal_code = ref_code.upper()
        user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)


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
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        role_groups = {
            "administrator": "Administrator",
            "accountant": "Accountant",
            "customer-support": "Customer-support",
            "loan-manager": "Loan-manager"
        }

        email = serializer.validated_data['email']
        first_name = serializer.validated_data['firstname']
        last_name = serializer.validated_data['lastname']
        role = serializer.validated_data.get('role')
        if role:
            role = role.strip().lower()

        user_exists = User.objects.filter(email=email).exists()
        if user_exists:
            return Response(data={"message": "user already exists"}, status=status.HTTP_400_BAD_REQUEST)

        password = generate_random_password()
        new_admin = User.objects.create(
            email=email, firstname=first_name, lastname=last_name, role="ADMIN")
        new_admin.set_password(password)
        new_admin.is_staff = True
        new_admin.is_verified = True

        # Add user to the appropriate group based on role
        group_name = role_groups.get(role, "Customer-support")
        group, created = Group.objects.get_or_create(name=group_name)
        new_admin.groups.add(group)

        new_admin.save()

        data = {"email": email, "password": password, "role": role}
        SendMail.send_invite_mail(data)

        return Response(data={"message": "Account created successfully"}, status=status.HTTP_201_CREATED)


class AdminUpdateTeamView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = UpdateAdminSerializer

    def post(self, request, id):
        member = get_object_or_404(User, pk=id)
        if member.role != 'ADMIN':
            return Response(data={"message": "invalid admin user"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        # Update user status if provided
        user_status = validated_data.get("status")
        if user_status:
            user_status = user_status.strip().lower()
            if user_status == 'active':
                member.is_active = True
            elif user_status == 'inactive':
                member.is_active = False
            member.save()

        # Update user role if provided
        new_role = validated_data.get("role")
        if new_role:
            new_role = new_role.strip().lower()
            role_groups = {
                "administrator": "Administrator",
                "accountant": "Accountant",
                "customer-support": "Customer-support",
                "loan-manager": "Loan-manager"
            }

            # Remove user from all groups
            member.groups.clear()

            # Add user to the new group
            new_group_name = role_groups.get(new_role)
            if new_group_name:
                new_group, created = Group.objects.get_or_create(
                    name=new_group_name)
                member.groups.add(new_group)

        member.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)


class AdminTransactions(generics.GenericAPIView):
    serializer_class = AdminTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination

    def get(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        return Transaction.objects.all().order_by("-created_at")


class AdminOverview(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()

        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)

        transactions = Transaction.objects.all()
        all_withdrawals = Withdrawal.objects.filter(status="SUCCESS")
        filtered_withdrawal = all_withdrawals.filter(created_at__range=[start_date, end_date])
        total_withdrawal_amount = all_withdrawals.aggregate(Sum('amount'))['amount__sum'] or 0
        filtered_withdrawal_amount = filtered_withdrawal.aggregate(Sum('amount'))['amount__sum'] or 0



        # Sum of all transaction amounts
        total_sum = transactions.aggregate(Sum('revenue'))['revenue__sum'] or 0

        # Filtered transactions for the given period
        filtered_transactions = transactions.filter(
            created_at__range=[start_date, end_date])
        filtered_sum = filtered_transactions.aggregate(Sum('revenue'))[
            'revenue__sum'] or 0

        # Sum of all transaction amounts
        savings = transactions.filter(nature="SAVINGS")
        total_savings = savings.aggregate(Sum('amount'))['amount__sum'] or 0

        # Filtered transactions for the given period
        filtered_saving = savings.filter(
            created_at__range=[start_date, end_date])
        filtered_savings_sum = filtered_saving.aggregate(Sum('amount'))[
            'amount__sum'] or 0
        all_users = User.objects.all()
        all_users_count = all_users.count()
        filter_user_count = all_users.filter(
            created_at__range=[start_date, end_date]).count()
        active_user = all_users.filter(is_active=True).count()
        all_coop = CoporativeMembership.objects.filter(is_active=True)
        coop_count = all_coop.count()
        total_coop = all_coop.aggregate(Sum('balance'))['balance__sum'] or 0

        all_loans = Loan.objects.all()
        disbured = all_loans.filter(status__in = ["APPROVED","REPAYED","OVER-DUE"])
        total_repaid = disbured.filter(status="REPAYED").count()
        # amount
        loan_filter = disbured.filter(date_approved__range=[start_date, end_date])
        all_loan_amount = disbured.aggregate(Sum('amount'))['amount__sum'] or 0
        loan_filter_amount = loan_filter.aggregate(Sum('amount'))['amount__sum'] or 0
        percentage_repayed = (total_repaid / disbured.count()) * 100 if disbured.count() else 0

        repayment_activities = Activities.objects.filter(title="Loan Repayment")
        loan_total_repayment = repayment_activities.aggregate(Sum('amount'))['amount__sum'] or 0
        loan_filter_activities = repayment_activities.filter(created_at__range=[start_date, end_date])
        loan_filtered_repayment = loan_filter_activities.aggregate(Sum('amount'))['amount__sum'] or 0


        return Response({
            'total_revenue': total_sum,
            'filtered_revenue': filtered_sum,
            'total_savings': total_savings,
            'filtered_savings_sum': filtered_savings_sum,
            'all_user_count': all_users_count,
            'filter_user_count': filter_user_count,
            'active_user': active_user,
            'inactive_user': all_users_count - active_user,
            'total_coop_members': coop_count,
            'total_coop_saved': total_coop,
            'total_loan_amount': all_loan_amount,
            'filtered_loan_amount':loan_filter_amount,
            "percentage_loan_repaid": percentage_repayed,
            "total_loan_repayment":loan_total_repayment,
            "filtered_loan_repayment":loan_filtered_repayment,
            'total_withdrawal_amount':total_withdrawal_amount,
            'filtered_withdrawal_amount':filtered_withdrawal_amount
        })


class AdminCreateInvestment(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = AdminCreateInvestmentSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class AdminUpdateInvestment(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = AdminCreateInvestmentSerializer

    def post(self, request, id):
        plan = get_object_or_404(InvestmentPlan, pk=id)
        serializer = self.serializer_class(
            instance=plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class GetTeamMembers(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = GetAdminMembersSerializer

    def get(self, request):
        serializer = self.serializer_class(self.get_queryset(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        return User.objects.filter(
            role="ADMIN").order_by('-created_at')


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
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by subscription status',
                              type=openapi.TYPE_STRING, enum=['active', 'inactive'], required=False),
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
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by status', type=openapi.TYPE_STRING, enum=[
                              'PENDING', 'REJECTED', 'PROCESSING', 'SUCCESS', 'FAILED'], required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        param2 = self.request.query_params.get('start_date', None)
        param3 = self.request.query_params.get('end_date', None)
        if param2 and not is_valid_date_format(param2):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if param3 and not is_valid_date_format(param3):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
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
                start_date = timezone.make_aware(
                    start_date, timezone.get_default_timezone())
            queryset = queryset.filter(created_at__gte=start_date)
        if param3:
            end_date = datetime.strptime(param3, '%Y-%m-%d')
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(
                    end_date, timezone.get_default_timezone())
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
            # TODO call safehaven api
            withdraw.status = "SUCCESS"
            withdrawal_transaction = withdraw.transaction
            if withdrawal_transaction:
                withdrawal_transaction.status = "SUCCESS"
                withdrawal_transaction.save()

            withdraw.admin_user = user
            withdraw.save()
            new_notification = Notification.objects.create(
                user=withdraw.user,
                title="Withdrawal Approved",
                text=f"Your withdrawal request of {withdraw.amount} has been approved"
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
            withdrawal_transaction = withdraw.transaction
            if withdrawal_transaction:
                withdrawal_transaction.status = "FAILED"
                withdrawal_transaction.message = reason
                withdrawal_transaction.save()
            withdraw.status = "REJECTED"
            withdraw.message = reason
            withdraw.admin_user = user
            withdraw_user = withdraw.user
            withdraw_user.wallet_balance += withdraw.amount
            # TODO add a notification
            new_notification = Notification.objects.create(
                user=withdraw_user,
                title="Withdrawal request rejected",
                text=f"Your withdrawal request of {withdraw.amount} as been rejected because {reason}"
            )
            new_notification.save()
            withdraw.save()
            withdraw_user.save()
            return Response(data={"message": "success"}, status=status.HTTP_200_OK)


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
    queryset = CoporativeMembership.objects.filter(
        is_active=True).order_by('-date_joined')
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
        coporative_members = CoporativeMembership.objects.filter(
            is_active=True)
        total_balance = coporative_members.aggregate(
            total=Sum('balance'))['total'] or 0
        active_members_count = coporative_members.count()

        resp = {
            "total": total_balance,
            "count": active_members_count
        }

        return Response(resp, status=status.HTTP_200_OK)


class AdminSavingsStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request):
        # Aggregating data
        savings_data = UserSavings.objects.aggregate(
            unique_users_active_savings=Count(
                'user', distinct=True),
            total_saved_active=Sum('saved'),
            total_saved_all=Sum('saved'),
            savings_count_per_title=Count('id', distinct=True),
            unique_users_per_title=Count('user', distinct=True),
            total_saved_per_title=Sum('saved')
        )
        all_canceled_savings = SavingsCancel.objects.all()
        # cancelled_investment_filter = all_cancelled_investments.filter(created_at__range=[start_date, end_date])
        cancelled_savings_amount = all_canceled_savings.aggregate(
            total_amount=Sum('amount'))['total_amount'] or 0
        cancelled_penalty = all_canceled_savings.aggregate(
            total_amount=Sum('penalty'))['total_amount'] or 0
        

        # Separate query to get counts and sums grouped by title
        title_aggregates = UserSavings.objects.values('type').annotate(
            savings_count_per_title=Count('id'),
            unique_users_per_title=Count('user', distinct=True),
            total_saved_per_title=Sum('saved')
        )

        # Formatting the title aggregates into a dictionary
        title_data = {}
        for item in title_aggregates:
            title_data[item['type']] = {
                'savings_count': item['savings_count_per_title'],
                'unique_users': item['unique_users_per_title'],
                'total_saved': item['total_saved_per_title']
            }
        #TODO interest paid
        intered_paid = 0
        interest_paid_today = 0
        data = {
            'unique_users_active_savings': savings_data['unique_users_active_savings'],
            'total_saved_active': savings_data['total_saved_active'],
            'total_saved_all': savings_data['total_saved_all'],
            'cancelled_savings_amount':cancelled_savings_amount,
            'cancelled_penalty':cancelled_penalty,
            'intered_paid':intered_paid,
            'interest_paid_today':interest_paid_today,
            'title_data': title_data
        }

        return Response(data)


class SavingsType(generics.GenericAPIView):
    serializer_class = SavingsTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination

    def get(self, request, name):
        queryset = UserSavings.objects.filter(
            type=name.strip().upper(), withdrawal_date__isnull = False).order_by("-start_date")
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


class AdminSingleInvestmentInvestors(generics.ListAPIView):
    serializer_class = SingleInvestmentInvestors
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["user__id", "user__firstname", "user__lastname", "user__email"]
    def get(self, request, id):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        id = self.kwargs["id"]
        investment = get_object_or_404(InvestmentPlan, pk = id)
        all_investors = UserInvestments.objects.filter(investment=investment).order_by("-created_at")
        return all_investors


class AdminSingleInvestment(generics.GenericAPIView):
    serializer_class = AdminSingleInvestment
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request, id):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    def patch(self, request, id):
        queryset = self.get_queryset()
        serializer = self.serializer_class(instance=queryset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
    def get_queryset(self):
        id = self.kwargs["id"]
        queryset = get_object_or_404(InvestmentPlan, pk=id)
        return queryset

class AdminInvestmentDashboards(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='Filter by duration',
                type=openapi.TYPE_STRING,
                enum=['Active', 'Sold'],
                required=False
            ),
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()

        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        filter_status = request.query_params.get('status', None)

        all_investments = UserInvestments.objects.all()


        latest_investment_subquery = UserInvestments.objects.filter(
            user=OuterRef('user')
        ).order_by('-created_at').values('id')[:1]

        latest_investments = all_investments.filter(
            id__in=Subquery(latest_investment_subquery)
        )
        # Calculate the total amount from the latest investments
        total_investments = latest_investments.aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or 0

        # Count of unique investors
        count_of_investors = latest_investments.distinct('user').count()

        filter_investments = latest_investments.filter(
            created_at__range=[start_date, end_date]
        )

        # Calculate the total interest for the latest investments
        total_interest = latest_investments.annotate(
            interest=ExpressionWrapper(
                F('amount') * F('investment__interest_rate') / 100,
                output_field=DecimalField()
            )
        ).aggregate(
            total_interest=Sum('interest')
        )['total_interest'] or 0

        # Calculate the total amount from the latest filtered investments
        total_by_filter = filter_investments.aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or 0

        # Count of unique investors within the filtered investments
        count_by_filter = filter_investments.distinct('user').count()

        # Get the current time
        to_now = timezone.now()

        # Upcoming payout this month from the latest investments
        upcoming_payout_this_month = latest_investments.filter(
            status="ACTIVE",
            due_date__year=to_now.year,
            due_date__month=to_now.month
        ).annotate(
            payout=ExpressionWrapper(
                F('amount') + (F('amount') * F('investment__interest_rate') / 100),
                output_field=DecimalField()
            )
        ).aggregate(
            total_amount=Sum('payout')
        )['total_amount'] or 0

        # Upcoming payout today from the latest investments
        upcoming_payout_today = latest_investments.filter(
            status="ACTIVE",
            due_date=today
        ).annotate(
            payout=ExpressionWrapper(
                F('amount') + (F('amount') * F('investment__interest_rate') / 100),
                output_field=DecimalField()
            )
        ).aggregate(
            total_amount=Sum('payout')
        )['total_amount'] or 0

        # Count of active investments from the latest investments
        active_investments = latest_investments.filter(
            status="ACTIVE"
        ).count()
        all_cancelled_investments = InvestmentCancel.objects.all()
        cancelled_investment_filter = all_cancelled_investments.filter(created_at__range=[start_date, end_date])
        cancelled_investment_count = all_cancelled_investments.count()
        cancelled_investment_filter_count = cancelled_investment_filter.count()
        cancelled_investment_penalties = all_cancelled_investments.aggregate(
            total_amount=Sum('penalty'))['total_amount'] or 0
        cancelled_investment_filter_penalty = cancelled_investment_filter.aggregate(
            total_amount=Sum('penalty'))['total_amount'] or 0

        investment_plans = InvestmentPlan.objects.all().order_by("-start_date")
        if filter_status:
            filter_status = filter_status.strip().upper()
            if filter_status == "ACTIVE":
                investment_plans = investment_plans.filter(is_active=True)
            elif filter_status == "SOLD":
                investment_plans = investment_plans.filter(is_active=False)
        plans = []
        for plan in investment_plans:
            plan_data = {
                'id': plan.id,
                'name': plan.title,
                'interest_rate': plan.interest_rate,
                'quota': plan.quota,
                'image': plan.image.url,
                'start_date': plan.start_date,
                'end_date': plan.end_date,
                'unit_share': plan.unit_share,
                'user_investments_count': plan.investment_type.count(),
                'is_active': plan.is_active
            }
            plans.append(plan_data)

        data = {
            'total_investments': total_investments,
            'count_of_investors': count_of_investors,
            'total_by_filter': total_by_filter,
            'count_by_filter': count_by_filter,
            'upcoming_payout_this_month':upcoming_payout_this_month,
            'upcoming_payout_today':upcoming_payout_today,
            'total_interest':total_interest,
            'active_investments':active_investments,
            'cancelled_investment_count':cancelled_investment_count,
            'cancelled_investment_filter_count':cancelled_investment_filter_count,
            'cancelled_investment_penalties': cancelled_investment_penalties,
            'cancelled_investment_filter_penalty':cancelled_investment_filter_penalty,
            'plans': plans
        }

        return Response(data)


class AdminLoanDashboard(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):

        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()

        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)

        # Define the statuses
        approved_statuses = ['APPROVED', 'REPAYED', 'OVER-DUE', 'REPAYED']
        pending_status = 'PENDING'
        rejected_status = 'REJECTED'
        overdued_status = 'OVER-DUE'

        # Annotate loans with interest
        loans_with_interest = Loan.objects.annotate(
            loan_interest=ExpressionWrapper(
                F('amount_repayed') * F('interest_rate') / 100, output_field=DecimalField())
        )

        # Calculate total amounts
        total_amount = loans_with_interest.filter(
            status__in=approved_statuses).aggregate(Sum('amount'))['amount__sum'] or 0
        total_amount_filter = loans_with_interest.filter(status__in=approved_statuses, date_approved__range=[
                                                         start_date, end_date]).aggregate(Sum('amount'))['amount__sum'] or 0

        # Calculate total repayment
        total_repayment = loans_with_interest.aggregate(Sum('amount_repayed'))[
            'amount_repayed__sum'] or 0
        total_repayment_filter = loans_with_interest.filter(date_approved__range=[
                                                            start_date, end_date]).aggregate(Sum('amount_repayed'))['amount_repayed__sum'] or 0

        # Calculate loan interest
        loan_interest = loans_with_interest.filter(status__in=approved_statuses).aggregate(
            Sum('loan_interest'))['loan_interest__sum'] or 0
        loan_interest_filter = loans_with_interest.filter(status__in=approved_statuses, date_approved__range=[
                                                          start_date, end_date]).aggregate(Sum('loan_interest'))['loan_interest__sum'] or 0

        # Calculate unique loan beneficiaries
        loan_beneficiary = loans_with_interest.filter(
            status__in=approved_statuses).values('user').distinct().count()
        loan_beneficiary_filter = loans_with_interest.filter(status__in=approved_statuses, date_approved__range=[
                                                             start_date, end_date]).values('user').distinct().count()

        # Count approved requests
        approved_request = loans_with_interest.filter(
            status__in=approved_statuses).count()
        approved_filter = loans_with_interest.filter(
            status__in=approved_statuses, date_approved__range=[start_date, end_date]).count()

        # Count pending requests
        pending_request = loans_with_interest.filter(
            status=pending_status).count()
        pending_request_filter = loans_with_interest.filter(
            status=pending_status, date_requested__range=[start_date, end_date]).count()

        # Count rejected requests
        rejected_request = loans_with_interest.filter(
            status=rejected_status).count()
        rejected_request_filter = loans_with_interest.filter(
            status=rejected_status, date_approved__range=[start_date, end_date]).count()

        # Count overdue requests
        overdued_request = loans_with_interest.filter(
            status=overdued_status).count()
        overdued_request_filter = loans_with_interest.filter(
            status=overdued_status, date_approved__range=[start_date, end_date]).count()

        # Prepare the response data
        response_data = {
            'total_amount': total_amount,
            'total_amount_filter': total_amount_filter,
            'total_repayment': total_repayment,
            'total_repayment_filter': total_repayment_filter,
            'loan_interest': loan_interest,
            'loan_interest_filter': loan_interest_filter,
            'loan_beneficiary': loan_beneficiary,
            'loan_beneficiary_filter': loan_beneficiary_filter,
            'approved_request': approved_request,
            'approved_filter': approved_filter,
            'pending_request': pending_request,
            'pending_request_filter': pending_request_filter,
            'rejected_request': rejected_request,
            'rejected_request_filter': rejected_request_filter,
            'overdued_request': overdued_request,
            'overdued_request_filter': overdued_request_filter,
        }

        return Response(response_data)


class AdminLoanOverview(generics.GenericAPIView):
    serializer_class = AdminLoanList
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by approved, pending, rejected, overdue, repayed',
                              type=openapi.TYPE_STRING, enum=['approved', 'pending', 'rejected', 'overdue', 'repayed'], required=False),
        ]
    )
    def get(self, request):
        queryset = Loan.objects.all().order_by("-date_requested")
        filter_param = request.query_params.get('status', None)
        if filter_param:
            filter_param = filter_param.strip().upper()
            queryset = queryset.filter(status=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class AdminAcceptLoan(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request, id):
        loan = get_object_or_404(Loan, pk=id)
        if loan.status != "PENDING":
            return Response({"message": "loan not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            loan.status = "APPROVED"
            user = loan.user
            user.wallet_balance += loan.amount
            new_notification = Notification.objects.create(
                user=user, title="LOAN APPROVAL",
                text=f"Your loan request for {loan.amount} has been approved by an admin",
                type="LOAN-UPDATE"
            )
            new_notification.save()
            loan.date_approved = datetime.today().date()
            user.save()
            loan.save()
        return Response({"message": "success"}, status=status.HTTP_200_OK)


class AdminRejectLoan(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request, id):
        loan = get_object_or_404(Loan, pk=id)
        if loan.status != "PENDING":
            return Response({"message": "loan not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            loan.status = "REJECTED"
            loan.is_active = False
            loan.date_approved = datetime.today().date()
            loan.save()
            new_notification = Notification.objects.create(
                user=loan.user, title="LOAN REJECTED",
                text=f"Your loan request for {loan.amount} has been rejected by an admin",
                type="LOAN-UPDATE"
            )
            new_notification.save()
        return Response({"message": "success"}, status=status.HTTP_200_OK)


class AdminUserCoporativeBreakdown(generics.GenericAPIView):
    serializer_class = AdminSingleUserCoporativeDetails
    pagination_class = CustomPagination
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, id):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        id = self.kwargs['id']
        user = get_object_or_404(User, pk=id)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        return CoporativeActivities.objects.filter(user_coop__user=user, created_at__range=[start_date, end_date]).select_related('user_coop').order_by('-created_at')

class AdminUserInvestmentBreakdown(generics.GenericAPIView):
    serializer_class = AdminUserInvestmentSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        active_investment = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        total_roi = 0
        for itm in queryset:
            total_roi += (itm.investment.interest_rate / 100) * itm.amount
        active_investment_count = queryset.count()

        # Custom response data
        additional_data = {
            'active_investment_amount': active_investment,
            'acive_investment_roi': total_roi,
            'active_investment_count': active_investment_count,
        }
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'overview': additional_data,
                'investments': serializer.data
            }
            return self.get_paginated_response(response_data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        id = self.kwargs['id']
        user = get_object_or_404(User, pk=id)
        queryset = UserInvestments.objects.filter(user = user, status="ACTIVE").order_by('-due_date')
        return queryset

class AdminUserInvestmentHistory(generics.GenericAPIView):
    serializer_class = AdminUserInvestmentSerializerHistory
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('status', openapi.IN_QUERY, description='status - active, matured, withdrawn',
                              type=openapi.TYPE_STRING,enum=['active', 'matured', 'withdrawn'], required=False),
        ]
    )
    def get(self, request, id):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        inv_status = self.request.query_params.get('status', None)
        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset()
        active_investment = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        total_roi = 0
        for itm in queryset:
            total_roi += (itm.investment.interest_rate / 100) * itm.amount
        active_investment_count = queryset.count()
        if inv_status:
            inv_status = inv_status.strip().upper()
            queryset = queryset.filter(status=inv_status)
        page = self.paginate_queryset(queryset)


        # Custom response data
        additional_data = {
            'total_investment_amount': active_investment,
            'total_investment_roi': total_roi,
            'total_investment_count': active_investment_count,
        }
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'overview': additional_data,
                'investments': serializer.data
            }
            return self.get_paginated_response(response_data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        id = self.kwargs['id']
        user = get_object_or_404(User, pk=id)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        inv_status = self.request.query_params.get('status', None)
        today = now()
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        queryset = UserInvestments.objects.filter(user = user, created_at__range=[start_date, end_date]).order_by('-due_date')
        return queryset

class AdminUserSavingsData(generics.GenericAPIView):
    serializer_class = AdminUserSavingsDataSerializers
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    def get(self, request, id):
        queryset = self.get_queryset()
        total_cycle = 0
        total_savings = 0
        current_Savings = 0
        for sav in queryset:
            total_cycle += sav.cycle
            total_savings += sav.all_time_saved
            current_Savings += sav.saved
        additional_data = {
            'total_cycle': total_cycle,
            'total_savings': total_savings,
            'current_Savings': current_Savings,
        }
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'overview': additional_data,
                'investments': serializer.data
            }
            return self.get_paginated_response(response_data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        id = self.kwargs["id"]
        user = get_object_or_404(User, pk=id)
        queryset = UserSavings.objects.filter(user=user)
        return queryset

class AdminUserSavingsInterest(generics.GenericAPIView):
    serializer_class = AdminUserSavingsInterestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, id):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        id = self.kwargs['id']
        savings = get_object_or_404(UserSavings, pk=id)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        queryset = SavingsActivities.objects.filter(savings=savings, created_at__range=[start_date, end_date]).order_by('-created_at')
        return queryset

class AdminUserSavingsBreakdown(generics.GenericAPIView):
    serializer_class = AdminUserSavingsBreakdownSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    # @swagger_auto_schema(
    #     manual_parameters=[
    #         openapi.Parameter('start_date', openapi.IN_QUERY,
    #                           description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
    #         openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
    #                           type=openapi.TYPE_STRING, required=False),
    #     ]
    # )
    def get(self, request, id):
        # start_date = self.request.query_params.get('start_date', None)
        # end_date = self.request.query_params.get('end_date', None)
        # if start_date and not is_valid_date_format(start_date):
        #     return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        # if end_date and not is_valid_date_format(end_date):
        #     return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.serializer_class(page, many=True)
        #     return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        id = self.kwargs['id']
        queryset = get_object_or_404(UserSavings, pk=id)
        # start_date = self.request.query_params.get('start_date', None)
        # end_date = self.request.query_params.get('end_date', None)
        # today = now()
        # start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        # start_date = start_date.replace(hour=0, minute=0, second=0)
        # if end_date:
        #     end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        # end_date = end_date or today
        # end_date += timedelta(days=1)
        # queryset = SavingsActivities.objects.filter(user = user, created_at__range=[start_date, end_date]).order_by('-created_at')
        return queryset


class AdminUserCoporativeBreakdown(generics.GenericAPIView):
    serializer_class = AdminUserCoporativeBreakdownSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, id):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        id = self.kwargs['id']
        user = get_object_or_404(User, pk=id)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now()
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        queryset = CoporativeActivities.objects.filter(user_coop__user = user, created_at__range=[start_date, end_date]).order_by('-created_at')
        return queryset


class AdminListReferal(generics.GenericAPIView):
    # pagination_class = []
    serializer_class = AdminReferralList
    pagination_class = CustomPagination
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY,
                              description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)',
                              type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request):
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        today = now()
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else today
        start_date = start_date.replace(hour=0, minute=0, second=0)
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        end_date = end_date or today
        end_date += timedelta(days=1)
        queryset = self.get_queryset()

        # Total number of referrals where is_subscribed=True
        total_referrals = queryset.filter(user__is_subscribed=True).count()

        # Total number of referrals where is_subscribed=True within the filtered period
        filtered_referrals = queryset.filter(user__is_subscribed=True).filter(created_at__range=[start_date, end_date]).count()

        # Sum of total_referal_balance
        total_referral_balance_sum = queryset.aggregate(Sum('total_referal_balance'))['total_referal_balance__sum']

        # Filter users who have referred at least one person with is_subscribed=True
        users_with_referals = queryset.annotate(
            referral_count=Count('user__is_subscribed')
        ).filter(referral_count__gte=1)
        page = self.paginate_queryset(users_with_referals)

        # Paginate the filtered users
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            response_data = {
                'total_referrals': total_referrals,
                'filtered_referrals': filtered_referrals,
                'total_referral_balance_sum': total_referral_balance_sum,
                'users': serializer.data
            }
            return self.get_paginated_response(response_data)
        serializer = self.serializer_class(users_with_referals, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        return User.objects.all()
    