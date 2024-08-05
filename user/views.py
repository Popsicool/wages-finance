from user.consumers import send_socket_user_notification
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
import random
from django.utils import timezone
from datetime import timedelta, date
from itertools import chain
from operator import attrgetter
from notification.models import Notification
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
    ChangePinSerializer
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
                     BANK_LISTS
                     )
from utils.pagination import CustomPagination
from django.db import transaction
from utils.sms import SendSMS

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

        combined_qs = sorted(
            chain(activities_qs, savings_activities_qs,
                  coporative_activities_qs),
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
    # permission_classes = [permissions.IsAuthenticated]
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
            user.tier = "T1"
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
                "balance": user.wallet_balance,
                "is_subscribed": user.is_subscribed,
                "activity": {
                    "title": new_activity.title,
                    "amount": new_activity.amount,
                    "activity_type": new_activity.activity_type,
                    "created_at": new_activity.created_at
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

        option_types = {1: "BIRTHDAY", 2: "CAR-PURCHASE",
                        3: "VACATION", 4: "GADGET-PURCHASE", 5: "MISCELLANEOUS"}
        user_option = option_types.get(id)
        user = request.user

        savings_filter = UserSavings.objects.filter(
            user=user, type=user_option).first()
        if not savings_filter:
            serializer = self.serializer_class(data=request.data)
        else:
            serializer = self.serializer_class(
                instance=savings_filter, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if not savings_filter:
                if not serializer.validated_data.get("frequency"):
                    return Response(data={"message": "frequency is compulsory"},  status=status.HTTP_400_BAD_REQUEST)
                serializer.save(user=user, type=user_option,
                                start_date=date.today())
            else:
                if not savings_filter.start_date:
                    serializer.save(start_date=date.today())
                else:
                    serializer.save()

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
            user=user).order_by("-created_at")
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
            coop.save()
            new_coop_activity = CoporativeActivities.objects.create(
                user_coop=coop, amount=amount)
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
            user.save()
            savings.saved += amount
            if savings.saved >= savings.amount:
                savings.goal_met = True
            savings.save()
            new_savings_activity = SavingsActivities.objects.create(savings=savings, amount=amount,
                                                                    user=user)
            new_savings_activity.save()
            return Response(data={"message": "success"}, status=status.HTTP_202_ACCEPTED)


class WithdrawalView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSeializer

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
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
            serializer.save(user=request.user, bank_name=matching_bank["name"])
            user.wallet_balance -= amount
            user.save()
            new_activity = Activities.objects.create(
                title="Fund withdrawal",
                amount=amount,
                user=user
            )
            new_activity.save()
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
        memberships_joined = now - timedelta(days=2)
        if membership.date_joined < memberships_joined:
            return Response(data={"message": "Not up to 6 months as a coporative member"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(user=user)
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
        if UserInvestments.objects.filter(user=user, investment=investment).exists():
            return Response(data={"message": "You are already an investor"}, status=status.HTTP_400_BAD_REQUEST)
        if not investment.is_active:
            return Response(data={"message": "investment no more active"}, status=status.HTTP_400_BAD_REQUEST)
        if investment.investors >= investment.quota:
            return Response(data={"message": "investment no more active"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        pin = serializer.validated_data["pin"]
        if user.pin != pin:
            return Response(data={"message": "invalid pin"}, status=status.HTTP_401_UNAUTHORIZED)
        unit = serializer.validated_data["unit"]
        amount = unit * investment.unit_share
        if user.wallet_balance < amount:
            return Response(data={"message": "insufficient fund"}, status=status.HTTP_400_BAD_REQUEST)
        user_coporative_balance = CoporativeMembership.objects.get(
            user=user).balance
        if (amount * 0.2) > user_coporative_balance:
            return Response(data={"message": "You must have more than 20 percent of the amount in your coporative balance"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            investment.investors += 1
            user.wallet_balance -= amount
            user.save()
            new_user_investment = UserInvestments.objects.create(
                investment=investment,
                user=user,
                shares=unit,
                amount=amount,
                due_date=investment.end_date
            )
            new_user_investment.save()
            if investment.quota == investment.investors:
                # TODO
                pass
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
            length=4, allowed_chars=f'0123456789')
        token_obj = ForgetPasswordToken.objects.filter(user=user).first()
        token_expiry = timezone.now() + timedelta(minutes=6)
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




class Get_Banks(views.APIView):
    def get(self, request):
        return Response(data=BANK_LISTS, status=status.HTTP_200_OK)



'''
{"message": 
    {
        "balance": 37300.0,
        "activity": 
            {
                "title": "N300 Deposit",
                "amount": 300.0,
                "activity_type": "CREDIT",
                "created_at": "2024-08-02T14:11:16.112158+00:00"
            }
        }
}


'''