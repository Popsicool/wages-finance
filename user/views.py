from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
import random
from django.utils import timezone
from datetime import timedelta
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
)
from .models import (Activities,
                     User,
                     InvestmentPlan,
                     UserSavings,
                     CoporativeMembership
                     )
from utils.pagination import CustomPagination
from django.db import transaction

# Create your views here.

class UserActivitiesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserActivitiesSerializer
    queryset = Activities.objects.all()
    pagination_class = CustomPagination
    def get(self, request):
        user = request.user
        queryset = self.queryset.filter(user=user).order_by("-created_at")
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status = 200)

class UserDashboard(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDashboardSerializer
    def get(self, request):
        user = request.user
        serializer = self.serializer_class(user)
        return Response(serializer.data, status = 200)

class GetInvestmentPlans(views.APIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = InvestmentPlanSerializer
    pagination_class = CustomPagination
    def get(self, request):
        investments = InvestmentPlan.objects.filter(is_active=True).order_by('-end_date')
        serializer = self.serializer_class(investments, many=True)
        return Response(serializer.data, status = 200)


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
            new_coop = CoporativeMembership.objects.create(user = user, membership_id = mem_id)
            new_coop.save()
            new_activity = Activities.objects.create(title="Membership Fee", amount=5000, user=user)
            new_activity.save()
            referal = user.referal
            if referal:
                referal.referal_balance += 2000
                referal.total_referal_balance += 2000
                ref_notification = Notification.objects.create(
                    user=referal,
                    title = "Referal bonus",
                    text= f"N2000 Referal bonus for referring {user.firstname} {user.lastname}"
                    )
                ref_notification.save()
                referal.save()
            user.save()
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
        return Response(data={"message":"success"},status=status.HTTP_201_CREATED)
    
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
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(user=user)
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
        queryset = UserSavings.objects.filter(user=user).order_by("-created_at")
        return queryset

class FundSavings(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AmountPinSerializer
    def post(self, request, id):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        savings = get_object_or_404(UserSavings, pk=id)
        if savings.user != user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            pin = serializer.validated_data["pin"]
            amount = serializer.validated_data["amount"]
            if user.pin != pin:
                return Response(data={"message": "invalid pin"}, status=status.HTTP_403_FORBIDDEN)
            if not savings.is_active:
                return Response(data={"message": "savings plan is no more active"}, status=status.HTTP_403_FORBIDDEN)
            if user.wallet_balance < amount:
                return Response(data={"message": "Insufficent amount in wallet"}, status=status.HTTP_403_FORBIDDEN)
            user.wallet_balance -= amount
            user.save()
            savings.saved += amount
            if savings.saved >= savings.amount:
                savings.goal_met = True
                savings.is_active = False
            savings.save()
            return Response(data={"message":"success"}, status=status.HTTP_202_ACCEPTED)



class WithdrawalView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSeializer
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        if user.wallet_balance < amount:
            return Response(data={"message":"Insufficient Fund"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            serializer.save(user = request.user)
            user.wallet_balance -= amount
            user.save()
            new_activity = Activities.objects.create(
                title="Fund withdrawal",
                amount=amount,
                user = user
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
        return Response(serializer.data, status = 200)

class LoanRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoanRequestSerializer
    def post(self, request):
        user = request.user
        membership = CoporativeMembership.objects.filter(user = user).first()
        if not membership:
            return Response(data={"message":"Not a member of coporative"}, status=status.HTTP_403_FORBIDDEN)
        now = timezone.now()
        memberships_joined = now - timedelta(days=5)
        if membership.date_joined < memberships_joined:
            return Response(data={"message":"Not up to 6 months as a coporative member"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(user=user)
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)

class ReferalViews(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReferalSerializer
    def get(self, request):
        user = request.user
        serializer = self.serializer_class(user)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

class WithdrawReferalBonus(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(Self,request):
        user = request.user
        if user.referal_balance <= 0:
            return Response(data={"message": "No fund in referal balance"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            new_activity = Activities.objects.create(
                user=user,
                title=f"N {user.referal_balance} referal bonus withdrawal",
                activity_type = "CREDIT",
                amount = user.referal_balance)
            new_activity.save()
            user.wallet_balance += user.referal_balance
            user.referal_balance = 0
            user.save()
            return Response(data={"message": "success"}, status = status.HTTP_200_OK)

