from django.shortcuts import render
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from .serializers import (
    UserActivitiesSerializer,
    UserDashboardSerializer,
    InvestmentPlanSerializer,
    SetPinSerializer,
    UpdateDP
)
from .models import Activities, User, InvestmentPlan
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
            user.wallet_balance -= 5000
            new_activity = Activities.objects.create(title="Membership Fee", amount=5000, user=user)
            new_activity.save()
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