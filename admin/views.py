from rest_framework import (permissions, generics, views, filters)
from authentication.permissions import IsAdministrator
from rest_framework.response import Response
from user.models import (User,
                         Withdrawal,
                         CoporativeMembership,
                         UserSavings,
                         InvestmentPlan,
                         UserInvestments,
                         Loan
                         )
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
    SingleSavingsSerializer,
    AdminLoanList,
    UpdateAdminSerializer,
    GetAdminMembersSerializer,
    AdminTransactionSerializer,
    CustomReferal
)
from transaction.models import Transaction
import random
import string
from utils.email import SendMail
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
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
            role_groups = {
                "administrator": "Administrators",
                "accountant": "Accountants",
                "customer-support": "Customer Support",
                "loan-managers": "Loan Managers"
            }

            # Remove user from all groups
            member.groups.clear()

            # Add user to the new group
            new_group_name = role_groups.get(new_role)
            if new_group_name:
                new_group, created = Group.objects.get_or_create(name=new_group_name)
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
        return Transaction.objects.all().order_by("-created_date")

class AdminOverview(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY, description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now().date()

        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = start_date or today
        end_date = end_date or today

        transactions = Transaction.objects.all()
        
        # Sum of all transaction amounts
        total_sum = transactions.aggregate(Sum('revenue'))['revenue__sum'] or 0

        # Filtered transactions for the given period
        filtered_transactions = transactions.filter(created_date__range=[start_date, end_date])
        filtered_sum = filtered_transactions.aggregate(Sum('revenue'))['revenue__sum'] or 0
        
        
        # Sum of all transaction amounts
        savings = transactions.filter(nature="SAVINGS")
        total_savings = savings.aggregate(Sum('amount'))['amount__sum'] or 0

        # Filtered transactions for the given period
        filtered_saving = savings.filter(created_date__range=[start_date, end_date])
        filtered_savings_sum = filtered_saving.aggregate(Sum('amount'))['amount__sum'] or 0
        all_users = User.objects.all()
        all_users_count = all_users.count()
        filter_user_count = all_users.filter(created_at__range=[start_date, end_date]).count()
        active_user = all_users.filter(is_active = True).count()

        return Response({
            'total_revenue': total_sum,
            'filtered_revenue': filtered_sum,
            'total_savings': total_savings,
            'filtered_savings_sum':filtered_savings_sum,
            'all_user_count': all_users_count,
            'filter_user_count': filter_user_count,
            'active_user':active_user,
            'inactive_user': all_users_count - active_user,
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
        serializer = self.serializer_class(instance=plan, data=request.data, partial=True)
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
            withdraw.status = "PROCESSING"
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
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        # Aggregating data
        savings_data = UserSavings.objects.aggregate(
            unique_users_active_savings=Count(
                'user', distinct=True, filter=Q(is_active=True)),
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
        queryset = UserSavings.objects.filter(
            title=name.strip().upper()).order_by("-created_at")
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


class AdminInvestmentDashboards(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'filter',
                openapi.IN_QUERY,
                description='Filter by duration',
                type=openapi.TYPE_STRING,
                enum=['TODAY'],
                required=False
            )
        ]
    )
    def get(self, request):
        filter_param = request.query_params.get('filter', None)
        today = date.today()

        all_investments = UserInvestments.objects.all()

        total_investments = all_investments.aggregate(
            total_amount=Sum('amount'))['total_amount'] or 0
        count_of_investors = all_investments.count()

        if filter_param and filter_param.strip().upper() == 'TODAY':
            filter_investments = all_investments.filter(created_at=today)
        else:
            filter_investments = all_investments

        total_by_filter = filter_investments.aggregate(
            total_amount=Sum('amount'))['total_amount'] or 0
        count_by_filter = filter_investments.count()

        investment_plans = InvestmentPlan.objects.all()
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
            'plans': plans
        }

        return Response(data)

class AdminLoanDashboard(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY, description='Start date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description='End date (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):

        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        today = now().date()

        if start_date and not is_valid_date_format(start_date):
            return Response(data={'error': 'Invalid start date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date and not is_valid_date_format(end_date):
            return Response(data={'error': 'Invalid end date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = start_date or today
        end_date = end_date or today

        # Define the statuses
        approved_statuses = ['APPROVED', 'REPAYED', 'OVER-DUE']
        pending_status = 'PENDING'
        rejected_status = 'REJECTED'

        #sum of repaid

        # Calculate total amounts
        total_amount = Loan.objects.filter(status__in=approved_statuses).aggregate(Sum('amount'))['amount__sum'] or 0
        total_amount_filter = Loan.objects.filter(status__in=approved_statuses, date_approved__range=[start_date, end_date]).aggregate(Sum('amount'))['amount__sum'] or 0

        # Calculate unique loan beneficiaries
        loan_beneficiary = Loan.objects.filter(status__in=approved_statuses).values('user').distinct().count()
        loan_beneficiary_filter = Loan.objects.filter(status__in=approved_statuses, date_approved__range=[start_date, end_date]).values('user').distinct().count()

        # Count approved requests
        approved_request = Loan.objects.filter(status__in=approved_statuses).count()
        approved_filter = Loan.objects.filter(status__in=approved_statuses, date_approved__range=[start_date, end_date]).count()

        # Count pending requests
        pending_request = Loan.objects.filter(status=pending_status).count()
        pending_request_filter = Loan.objects.filter(status=pending_status, date_requested__range=[start_date, end_date]).count()

        # Count rejected requests
        rejected_request = Loan.objects.filter(status=rejected_status).count()
        rejected_request_filter = Loan.objects.filter(status=rejected_status, date_approved__range=[start_date, end_date]).count()

        # Prepare the response data
        response_data = {
            'total_amount': total_amount,
            'total_amount_filter': total_amount_filter,
            'loan_beneficiary': loan_beneficiary,
            'loan_beneficiary_filter': loan_beneficiary_filter,
            'approved_request': approved_request,
            'approved_filter': approved_filter,
            'pending_request': pending_request,
            'pending_request_filter': pending_request_filter,
            'rejected_request': rejected_request,
            'rejected_request_filter': rejected_request_filter,
        }

        return Response(response_data)

class AdminLoanOverview(generics.GenericAPIView):
    serializer_class = AdminLoanList
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    pagination_class = CustomPagination
    def get(self, request):
        queryset = Loan.objects.all().order_by("-date_requested")
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
            return Response({"message":"loan not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
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
            return Response({"message":"loan not in pending state"}, status=status.HTTP_400_BAD_REQUEST)
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