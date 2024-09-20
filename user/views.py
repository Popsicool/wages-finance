from transaction.models import Transaction
from user.consumers import send_socket_user_notification
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
import random
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from itertools import chain
from decimal import Decimal
from operator import attrgetter
from notification.models import Notification
from utils.email import SendMail
from .serializers import (
    UserActivitiesSerializer,
    UserDashboardSerializer,
    InvestmentPlanSerializer,
    SetPinSerializer,
    UpdateDP,
    NewSavingsSerializer,
    UserSavingsSerializers,
    AmountPinSerializer,
    CoporativeDashboardSerializer,
    WithdrawalSeializer,
    LoanRequestSerializer,
    ReferalSerializer,
    UserInvestment,
    UserInvestmentHistory,
    VerifyResetPinTokenSerializer,
    ChangePinSerializer,
    LoanDetailsSerializer,
    AllLoansSerializer,
    RepaymentSerializer,
)
from .models import (Activities,
                     User,
                     InvestmentPlan,
                     UserSavings,
                     CoporativeMembership,
                     UserInvestments,
                     ForgetPasswordToken,
                     SavingsActivities,
                     CoporativeActivities,
                     BANK_LISTS,
                     Loan,
                     InvestmentCancel,
                     SavingsCancel
                     )
from utils.pagination import CustomPagination
from django.db import transaction
from utils.sms import SendSMS
from datetime import datetime
from django.utils.encoding import smart_bytes, smart_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# Create your views here.


class UserActivitiesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserActivitiesSerializer
    pagination_class = CustomPagination

    def get(self, request):
        user = request.user
        activities_qs = Activities.objects.filter(
            user=user).order_by("-created_at")
        savings_activities_qs = SavingsActivities.objects.filter(
            user=user).order_by("-created_at")
        coporative_activities_qs = CoporativeActivities.objects.filter(
            user_coop__user=user).order_by("-created_at")
        transactions_qs = Transaction.objects.filter(user=user).order_by("-created_at")

        combined_qs = sorted(
            chain(activities_qs, savings_activities_qs,
                  coporative_activities_qs, transactions_qs),
            key=attrgetter('created_at'),
            reverse=True
        )

        page = self.paginate_queryset(combined_qs)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(combined_qs, many=True)
        return Response(serializer.data, status=200)


class UserDashboard(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDashboardSerializer

    def get(self, request):
        user = request.user
        serializer = self.serializer_class(user)
        return Response(serializer.data, status=200)


class GetInvestmentPlans(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InvestmentPlanSerializer
    pagination_class = CustomPagination

    def get(self, request):
        investments = InvestmentPlan.objects.filter(
            is_active=True).order_by('-end_date')
        serializer = self.serializer_class(investments, many=True)
        return Response(serializer.data, status=200)


class OneTimeSubscription(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SetPinSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.pin:
            return Response({"message": "Set transaction pin first"}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_subscribed:
            return Response({"message": "You are already subscribed"}, status=status.HTTP_400_BAD_REQUEST)
        if serializer.validated_data["pin"] != user.pin:
            return Response({"message": "Invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        if user.wallet_balance < 5000:
            return Response({"message": "Insufficient fund"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user.is_subscribed = True
            user.wallet_balance -= 5000
            mem_id = 'WF-' + ''.join(random.sample('0123456789', 9))
            new_coop = CoporativeMembership.objects.create(
                user=user, membership_id=mem_id)
            new_coop.save()
            new_activity = Activities.objects.create(
                title="Membership Fee", amount=5000, user=user)
            new_activity.save()
            referal = user.referal
            if referal:
                referal.referal_balance += 2000
                referal.total_referal_balance += 2000
                ref_notification = Notification.objects.create(
                    user=referal,
                    title="Referal bonus",
                    text=f"N2000 Referal bonus for referring {user.firstname} {user.lastname}"
                )
                ref_notification.save()
                referal.save()
            user.save()
            data = {
                "balance": float(user.wallet_balance),
                "is_subscribed": user.is_subscribed,
                "activity": {
                    "title": new_activity.title,
                    "amount": float(new_activity.amount),
                    "activity_type": new_activity.activity_type,
                    "created_at": str(new_activity.created_at)
                }
            }
            send_socket_user_notification(user.id, data)
            return Response(data={"message": "success"}, status=status.HTTP_200_OK)


class SetPin(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SetPinSerializer

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.pin = serializer.validated_data["pin"]
        user.save()
        return Response(data={"message": "success"}, status=status.HTTP_201_CREATED)


class UpdateDPView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UpdateDP

    def post(self, request):
        user = request.user
        serialzer = self.serializer_class(data=request.data)
        serialzer.is_valid(raise_exception=True)
        with transaction.atomic():
            user.profile_picture = serialzer.validated_data["image"]
            user.save()
            return Response(status=status.HTTP_200_OK)


class NewSavingsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NewSavingsSerializer
    pagination_class = CustomPagination

    def post(self, request, id):
        if id not in [1, 2, 3, 4, 5]:
            return Response(data={"message": "invalid option"}, status=status.HTTP_400_BAD_REQUEST)
        
        option_types = {1: "BIRTHDAY", 2: "CAR-PURCHASE", 3: "VACATION", 4: "GADGET-PURCHASE", 5: "MISCELLANEOUS"}
        user_option = option_types.get(id)
        user = request.user
        savings_filter = UserSavings.objects.filter(user=user, type=user_option).first()

        serializer = self.serializer_class(
            instance=savings_filter, data=request.data, partial=bool(savings_filter)
        )

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if not savings_filter:
                if not serializer.validated_data.get("frequency"):
                    return Response(data={"message": "frequency is compulsory"}, status=status.HTTP_400_BAD_REQUEST)
                new_savings = serializer.save(user=user, type=user_option)
                new_savings.calculate_payment_details()
                new_savings.save()
            else:
                if not savings_filter.start_date:
                    n_save = serializer.save(start_date=date.today(), cycle=savings_filter.cycle + 1)
                else:
                    n_save = serializer.save(cycle=savings_filter.cycle + 1)
                n_save.calculate_payment_details()

            return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class UserSavingsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSavingsSerializers
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        queryset = UserSavings.objects.filter(
            user=user, withdrawal_date__isnull=False).order_by("-created_at")
        return queryset


class FundCoporative(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AmountPinSerializer

    def post(self, request):
        user = request.user
        coop = CoporativeMembership.objects.filter(user=user).first()
        if not coop:
            return Response(data={"message": "Not yet a coporative member"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            pin = serializer.validated_data["pin"]
            amount = serializer.validated_data["amount"]
            # if amount < 100:
            #     return Response(data={"message": "Amount must be a minimum of N100"}, status=status.HTTP_403_FORBIDDEN)
            if user.pin != pin:
                return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
            if user.wallet_balance < amount:
                return Response(data={"message": "Insufficent amount in wallet"}, status=status.HTTP_403_FORBIDDEN)
            user.wallet_balance -= amount
            user.save()
            coop.balance += amount
            current_date = date.today()
            last_day_of_year = date(current_date.year, 12, 31)
            days_left = (last_day_of_year - current_date).days
            dividends = days_left * 0.0004658 * amount
            coop.dividend += int(dividends)
            coop.save()
            new_coop_activity = CoporativeActivities.objects.create(
                user_coop=coop, amount=amount, balance=coop.balance)
            new_coop_activity.save()
            return Response(data={"message": "success"}, status=status.HTTP_202_ACCEPTED)


class FundSavings(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AmountPinSerializer

    def post(self, request, id):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if id not in [1, 2, 3, 4, 5]:
            return Response(data={"message": "invalid option"}, status=status.HTTP_400_BAD_REQUEST)

        option_types = {1: "BIRTHDAY", 2: "CAR-PURCHASE",
                        3: "VACATION", 4: "GADGET-PURCHASE", 5: "MISCELLANEOUS"}
        user_option = option_types.get(id)
        savings = UserSavings.objects.filter(
            user=user, type=user_option).first()
        serializer = self.serializer_class(data=request.data)
        if not savings:
            return Response(data={"message": "Set savings option first"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.is_valid(raise_exception=True)
        today = datetime.now().date()
        days_to_withdrawal = (savings.withdrawal_date - today).days

        with transaction.atomic():
            pin = serializer.validated_data["pin"]
            amount = serializer.validated_data["amount"]
            if amount < 100:
                return Response(data={"message": "Amount must be a minimum of N100"}, status=status.HTTP_403_FORBIDDEN)
            if user.pin != pin:
                return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
            if user.wallet_balance < amount:
                return Response(data={"message": "Insufficent amount in wallet"}, status=status.HTTP_403_FORBIDDEN)
            user.wallet_balance -= amount
            interest = days_to_withdrawal * 0.000329 * amount
            savings.all_time_saved += interest
            savings.interest += interest
            user.save()
            savings.mark_payment_as_made(timezone.now(), int(amount))
            savings.save()
            new_savings_activity = SavingsActivities.objects.create(savings=savings, amount=amount,
                                                                    balance = savings.saved, interest=interest,
                                                                    user=user)
            new_savings_activity.save()
            return Response(data={"message": "success"}, status=status.HTTP_202_ACCEPTED)

class CancelSavings(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SetPinSerializer
    def post(self, request, id):
        user = request.user
        if id not in [1, 2, 3, 4, 5]:
            return Response(data={"message": "invalid option"}, status=status.HTTP_400_BAD_REQUEST)

        option_types = {1: "BIRTHDAY", 2: "CAR-PURCHASE",
                        3: "VACATION", 4: "GADGET-PURCHASE", 5: "MISCELLANEOUS"}
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        pin = serializer.validated_data["pin"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
            
        user_option = option_types.get(id)
        savings = UserSavings.objects.filter(
            user=user, type=user_option).first()
        if not savings:
            return Response(data={"message": "Set savings option first"}, status=status.HTTP_400_BAD_REQUEST)
        if not savings.withdrawal_date:
            return Response(data={"message": "You don't have a savings of this type"}, status=status.HTTP_400_BAD_REQUEST)
        # if savings.withdrawal_date > date.today():
        penalty = savings.saved * 0.02
        refund = savings.saved - penalty
        amt = savings.saved
        with transaction.atomic():
            user.wallet_balance += Decimal(refund)
            savings.amount = 0
            savings.saved = 0
            savings.withdrawal_date = None
            savings.start_date = None
            savings.target_amount = None
            savings.cancel_date = date.today()
            savings.goal_met = False
            savings.payment_details = None
            savings.interest = 0
            savings.time = None
            savings.day_week = None
            savings.day_month = None
            Activities.objects.create(title="Savings Payment", amount=refund, user=user, activity_type="CREDIT")
            SavingsCancel.objects.create(savings=savings,penalty=penalty, amount=amt)
            savings.save()
            user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)
        
        
class CancelInvestment(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SetPinSerializer
    def post(self, request, id):
        user = request.user
        investment_plan = get_object_or_404(UserInvestments, pk=id)
        if investment_plan.user != user:
            return Response({"message": "Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)
        if investment_plan.status != "ACTIVE":
            return Response({"message": "Investment not active"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        pin = serializer.validated_data["pin"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
        penalty = investment_plan.amount * 0.02
        refund = investment_plan.amount - penalty
        with transaction.atomic():
            user.wallet_balance += Decimal(refund)
            Activities.objects.create(title="Investment withdrawal", amount=refund, user=user, activity_type="CREDIT")
            investment_plan.status = "WITHDRAWN"
            investment_plan.amount = refund
            investment = investment_plan.investment
            investment.quota += investment_plan.shares
            investment.save()
            investment_plan.save()
            InvestmentCancel.objects.create(investment=investment_plan, penalty = penalty)
            user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)

class WithdrawInvestment(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SetPinSerializer
    def post(self, request, id):
        user = request.user
        investment_plan = get_object_or_404(UserInvestments, pk=id)
        if investment_plan.user != user:
            return Response({"message": "Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)
        if investment_plan.status != "MATURED":
            return Response({"message": "Investment not in matured state"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        pin = serializer.validated_data["pin"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
        refund = investment_plan.amount + investment_plan.interest
        with transaction.atomic():
            user.wallet_balance += Decimal(refund)
            Activities.objects.create(title="Investment withdrawal", amount=refund, user=user, activity_type="CREDIT")
            investment_plan.status = "WITHDRAWN"
            # investment = investment_plan.investment
            #TODO ask for clarification
            # investment.quota += investment_plan.shares
            # investment.save()
            investment_plan.save()
            user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)
         


class WithdrawalView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSeializer

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        account_number = serializer.validated_data["account_number"]
        if amount < 100:
            # TODO ask clarification
            return Response(data={"message": "Amount must be at least N1000"}, status=status.HTTP_401_UNAUTHORIZED)
         
        pin = serializer.validated_data["pin"]
        bank_code = serializer.validated_data["bank_code"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        if user.wallet_balance < amount:
            return Response(data={"message": "Insufficient Fund"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.validated_data.pop("pin", None)
        matching_bank = list(filter(lambda bank: bank["bankCode"] == bank_code, BANK_LISTS))
        if not matching_bank:
            return Response(data={"message": "invalid bank code"}, status=status.HTTP_400_BAD_REQUEST)
        matching_bank = matching_bank[0]
        with transaction.atomic():
            new_transaction = Transaction.objects.create(
                user = user,
                amount = amount,
                type = "Withdrawal",
                description = f'N{amount} withdrawal',
                source = f'{matching_bank["name"]}/{account_number}'
            )
            new_transaction.save()
            serializer.save(user=user, bank_name=matching_bank["name"], transaction=new_transaction)
             
            user.wallet_balance -= amount
            user.save()
            # new_activity = Activities.objects.create(
            #     title="Fund withdrawal",
            #     amount=amount,
            #     user=user
            # )
            # new_activity.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)


class Coporative_dashboard(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CoporativeDashboardSerializer

    def get(self, request):
        user = request.user
        if not user.is_subscribed:
            return Response({"message": "Not yet a cooporative member"}, status=status.HTTP_401_UNAUTHORIZED)
        queryset = CoporativeMembership.objects.filter(user=user).first()
        serializer = self.serializer_class(queryset)
        return Response(serializer.data, status=200)


class LoanRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoanRequestSerializer

    def post(self, request):
        user = request.user
        membership = CoporativeMembership.objects.filter(user=user).first()
        if not membership:
            return Response(data={"message": "Not a member of coporative"}, status=status.HTTP_403_FORBIDDEN)
        now = timezone.now()

        memberships_joined = now - timedelta(days=5)
        if membership.date_joined >= memberships_joined:

            return Response(data={"message": "Not up to 6 months as a coporative member"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data)
        active_loan = Loan.objects.filter(user=user, is_active=True).first()
        if active_loan:
            return Response(data={"message": "You have an outstanding loan"}, status=status.HTTP_403_FORBIDDEN)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        g1 = serializer.validated_data["guarantor1"]
        g2 = serializer.validated_data["guarantor2"]
        if user == g1 or user == g2:
            return Response(data={"message": "You can not be your guarantor"}, status=status.HTTP_403_FORBIDDEN)
        if amount > (membership.balance * 2):
            return Response(data={"message": "You are not eligible for this amount"}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            loan_obj = serializer.save(user=user)
            accept_link1 = urlsafe_base64_encode(smart_bytes(f"{loan_obj.id}-{1}-{urlsafe_base64_encode(smart_bytes(g1.email))}"))
            reject_link1 = urlsafe_base64_encode(smart_bytes(f"{loan_obj.id}-{0}-{urlsafe_base64_encode(smart_bytes(g1.email))}"))
            accept_link2 = urlsafe_base64_encode(smart_bytes(f"{loan_obj.id}-{1}-{urlsafe_base64_encode(smart_bytes(g2.email))}"))
            reject_link2 = urlsafe_base64_encode(smart_bytes(f"{loan_obj.id}-{0}-{urlsafe_base64_encode(smart_bytes(g2.email))}"))
            data = {}
            data["amount"] = amount
            data["duration"] = loan_obj.duration_in_months
            data["user_name"] = f"{user.firstname} {user.lastname}"
            data["guarantor_name"] = f"{g1.firstname} {g1.lastname}"
            data["email"] = g1.email
            data["accept_link"]= accept_link1
            data["reject_link"]= reject_link1
            SendMail.send_loan_notification_email(data)
            data["guarantor_name"] = f"{g2.firstname} {g2.lastname}"
            data["email"] = g2.email
            data["accept_link"]= accept_link2
            data["reject_link"]= reject_link2
            SendMail.send_loan_notification_email(data)
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class ReferalViews(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReferalSerializer

    def get(self, request):
        # TODO order
        user = request.user
        serializer = self.serializer_class(user)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class WithdrawReferalBonus(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(Self, request):
        user = request.user
        if user.referal_balance <= 0:
            return Response(data={"message": "No fund in referal balance"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            new_activity = Activities.objects.create(
                user=user,
                title="Referal bonus withdrawal",
                activity_type="CREDIT",
                amount=user.referal_balance)
            new_activity.save()
            user.wallet_balance += user.referal_balance
            user.referal_balance = 0
            user.save()
            return Response(data={"message": "success"}, status=status.HTTP_200_OK)


class UserInvest(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserInvestment

    def post(self, request, id):
        user = request.user
        investment = get_object_or_404(InvestmentPlan, pk=id)
        if UserInvestments.objects.filter(user=user, investment=investment, status="ACTIVE").exists():
            return Response(data={"message": "You are already an active investor"}, status=status.HTTP_400_BAD_REQUEST)
        incr = False
        if UserInvestments.objects.filter(user=user, investment=investment, status__in=["MATURED", "WITHDRAWN"]).exists():
            incr = True
        if not investment.is_active:
            return Response(data={"message": "investment no more active"}, status=status.HTTP_400_BAD_REQUEST)
        if investment.quota <= 0:
            return Response(data={"message": "investment no more active"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        pin = serializer.validated_data["pin"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        unit = serializer.validated_data["unit"]
        if unit > investment.quota:
            return Response(data={"message": "Unit more than available quota"}, status=status.HTTP_400_BAD_REQUEST)
        amount = unit * investment.unit_share
        if user.wallet_balance < amount:
            return Response(data={"message": "insufficient fund"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_subscribed:
            return Response(data={"message": "Subscribe to coporative before investing"}, status=status.HTTP_400_BAD_REQUEST)
        user_coporative_balance = CoporativeMembership.objects.get(
            user=user).balance
        if (amount * 0.2) > user_coporative_balance:
            return Response(data={"message": "You must have more than 20 percent of the amount in your coporative balance"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            if not incr:
                investment.investors += 1
            user.wallet_balance -= amount
            user.save()
            due_date = date.today() + relativedelta(months=investment.duration)
            new_user_investment = UserInvestments.objects.create(
                investment=investment,
                user=user,
                shares=unit,
                amount=amount,
                due_date=due_date
            )
            new_activity = Activities.objects.create(
                title=f"Investment on {investment.title}", amount=amount, user=user)
            new_activity.save()
            investment.quota -= unit
            new_user_investment.save()
            if investment.quota <= 0:
                investment.is_active = False
                # TODO
                # pass
            investment.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class UserInvestmentHistory(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserInvestmentHistory

    def get(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        queryset = UserInvestments.objects.filter(
            user=user).order_by("-created_at")
        return queryset


class ResetPinToken(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        token = User.objects.make_random_password(
            length=6, allowed_chars=f'0123456789')
        token_obj = ForgetPasswordToken.objects.filter(user=user).first()
        token_expiry = timezone.now() + timedelta(minutes=10)
        if not token_obj:
            token_obj = ForgetPasswordToken.objects.create(
                user=user, token=token, token_expiry=token_expiry)
        else:
            token_obj.is_used = False
            token_obj.token = token
            token_obj.token_expiry = token_expiry
        token_obj.save()
        data = {"token": token, 'number': user.phone}
        SendSMS.sendVerificationCode(data)
        return Response({
            'message': 'we have sent you a code to reset your pin'
        }, status=status.HTTP_200_OK)


class VerifyResetPin(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifyResetPinTokenSerializer

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        verificationObj = ForgetPasswordToken.objects.filter(user=user).first()

        if not verificationObj:
            return Response(data={"message": "request for token first"}, status=status.HTTP_400_BAD_REQUEST)

        if verificationObj.token != token:
            return Response(data={"message": "Wrong token"}, status=status.HTTP_400_BAD_REQUEST)

        if verificationObj.is_used:
            return Response(data={"message": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        if verificationObj.token_expiry < timezone.now():
            return Response(data={"message": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        verificationObj.is_used = True
        verificationObj.token_expiry = timezone.now()
        verificationObj.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)


class ChangePinView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePinSerializer

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        current_pin = serializer.validated_data["current_pin"]
        if user.pin != current_pin:
            return Response(data={"message": "invalid pin"})
        new_pin = serializer.validated_data["new_pin"]
        user.pin = new_pin
        user.save()
        return Response(data={"message": "success"}, status=status.HTTP_200_OK)


def test_socket(request, id):
    data = {
        "balance": 38900.0,
        "activity": 
            {
                "title": "N300 Deposit",
                "amount": 300.0,
                "activity_type": "CREDIT",
                "created_at": "2024-08-02T14:11:16.112158+00:00"
            }
        }
    send_socket_user_notification(id, data)
    return JsonResponse(data={"message": "success"}, status=status.HTTP_200_OK)


class LoanDetailsSerializer(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoanDetailsSerializer
    def get(self, request, id):
        loan = get_object_or_404(Loan, pk=id)
        user = request.user
        if loan.user != user:
            return Response({"message": "Invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.serializer_class(loan)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

class UserLoanHistory(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AllLoansSerializer
    def get(self, request):
        user = request.user
        loan = Loan.objects.filter(user=user).order_by("-date_requested")
        serializer = self.serializer_class(loan, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)





class UserRepayLoan(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RepaymentSerializer
    def post(self, request, id):
        loan = get_object_or_404(Loan, pk=id)
        user = request.user
        
        # Ensure the user is authorized to make this request
        if loan.user != user:
            return Response({"message": "Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate the request data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        repayment_indices = serializer.validated_data['repayment_indices']
        
        # Check the PIN
        if serializer.validated_data["pin"] != user.pin:
            return Response({"message": "Invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        
        repayment_details = loan.repayment_details

        # Sort repayments by date
        sorted_repayments = sorted(
            repayment_details.items(), 
            key=lambda x: datetime.strptime(x[0], "%d/%m/%Y")
        )

        amounts_to_repay = []
        keys = [item[0] for item in sorted_repayments]

        # Validate repayment indices and calculate total amount
        for index in repayment_indices:
            if index - 1 < 0 or index - 1 >= len(keys):
                return Response(
                    {"message": f"Index {index} is out of range."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            key = keys[index - 1]  # -1 for zero-based index
            repayment = repayment_details.get(key)
            
            if repayment['paid_status']:
                return Response(
                    {"message": f"Repayment for date {key} has already been paid."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            amounts_to_repay.append(repayment['amount'])

        total_amount = sum(amounts_to_repay)

        # Check if the user has sufficient funds
        if user.wallet_balance < total_amount:
            return Response({"message": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)

        # Process the repayment
        with transaction.atomic():
            user.wallet_balance -= total_amount
            
            for index in repayment_indices:
                key = keys[index - 1]  # -1 for zero-based index
                repayment_details[key]['paid_status'] = True
            
            loan.repayment_details = repayment_details
            
            # Check if all repayments are completed
            all_repaid = all(detail['paid_status'] for detail in repayment_details.values())
            if all_repaid:
                loan.is_active = False
                loan.status = "REPAYED"
                loan.balance = 0
            else:
                loan.balance -= total_amount
            loan.amount_repayed += total_amount
            
            # Log the activity
            Activities.objects.create(title="Loan Repayment", amount=total_amount, user=user)
            
            # Save changes
            loan.save()
            user.save()

        return Response(data={"message": "Success"}, status=status.HTTP_200_OK)

class Get_Banks(views.APIView):
    def get(self, request):
        return Response(data=BANK_LISTS, status=status.HTTP_200_OK)


class LiquidateLoan(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class =  SetPinSerializer
    def post(self, request, id):
        loan = get_object_or_404(Loan, pk=id)
        user = request.user
        if loan.user != user:
            return Response({"message": "Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Check the PIN
        if serializer.validated_data["pin"] != user.pin:
            return Response({"message": "Invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        repayment_details = loan.repayment_details
        total_amount_due = sum(
            repayment['amount'] for repayment in repayment_details.values() if not repayment['paid_status']
        )
        # Check if the user has sufficient funds
        if user.wallet_balance < total_amount_due:
            return Response({"message": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)

        # Mark all repayments as paid
        with transaction.atomic():
            for repayment in repayment_details.values():
                repayment['paid_status'] = True
            loan.repayment_details = repayment_details
            loan.is_active = False
            loan.status = "REPAYED"
            loan.amount_repayed += total_amount_due
            loan.balance = 0
            # Deduct the total amount from the user's wallet balance
            user.wallet_balance -= total_amount_due
            # Log the activity
            Activities.objects.create(title="Loan liquidation", amount=total_amount_due, user=user)

            # Save changes
            loan.save()
            user.save()

        return Response(data={"message": "All repayments marked as paid"}, status=status.HTTP_200_OK)



class GuarantorResponse(views.APIView):
    def get(self, request):
        q_param = request.query_params.get('q', None)
        if not q_param:
            return Response(data={"message":"invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        decoded_bytes = urlsafe_base64_decode(q_param)
        decoded_str = smart_str(decoded_bytes)
        parts = decoded_str.split('-', 3)
        loan_id = parts[0]
        req_status = parts[1]
        if req_status not in ["1", "0"]:
            return Response(data={"message":"invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        email_part = parts[2]
        email = smart_str(urlsafe_base64_decode(email_part))
        loan = get_object_or_404(Loan, pk=loan_id)
        if loan.status != "PENDING":
            return Response(data={"message":"invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            if loan.guarantor1.email == email:
                if req_status == "1":
                    loan.guarantor1_agreed = "APPROVED"
                    new_notification = Notification.objects.create(
                        user=loan.user,
                        title="Guarantor request Approved",
                        text=f"{loan.guarantor1.firstname} {loan.guarantor1.lastname} has accepted to be your Guarantor"
                    )
                else:
                    loan.guarantor1_agreed = "REJECTED"
                    new_notification = Notification.objects.create(
                        user=loan.user,
                        title="Guarantor request Declined",
                        text=f"{loan.guarantor1.firstname} {loan.guarantor1.lastname} has declined to be your Guarantor"
                    )
            elif loan.guarantor2.email == email:
                if req_status == "1":
                    loan.guarantor2_agreed = "APPROVED"
                    new_notification = Notification.objects.create(
                        user=loan.user,
                        title="Guarantor request Approved",
                        text=f"{loan.guarantor2.firstname} {loan.guarantor2.lastname} has accepted to be your Guarantor"
                    )
                else:
                    loan.guarantor2_agreed = "REJECTED"
                    new_notification = Notification.objects.create(
                        user=loan.user,
                        title="Guarantor request Declined",
                        text=f"{loan.guarantor2.firstname} {loan.guarantor2.lastname} has declined to be your Guarantor"
                    )
            else:
                return Response(data={"message":"invalid request"}, status=status.HTTP_400_BAD_REQUEST)
            new_notification.save()
            loan.save()
        return Response(data={"msg":"success"})


# from django.http import JsonResponse
# def test_email(request):
#     data = {}
#     all_loans = Loan.objects.all()
#     for l in all_loans:
#         l.populate_repayment_details()
#         l.balance = l.amount + l.calculate_total_interest()
#         l.save()
#     data["amount"] = 5000
#     data["duration"] = 6
#     data["user_name"] = "Akinola Samson"
#     data["guarantor_name"] = "Oluwa Popsicool"
#     data["email"] = "akinolasamson1234@gmail.com"
#     data["accept_link"]= "https://fb.com"
#     data["reject_link"]= "https://fb.com"
#     SendMail.send_loan_notification_email(data)
    # return JsonResponse({"msg":"success"})
