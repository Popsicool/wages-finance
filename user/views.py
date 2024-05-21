from django.shortcuts import render
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from .serializers import (
    UserActivitiesSerializer,
    UserDashboardSerializer,
    InvestmentPlanSerializer
)
from .models import Activities, User, InvestmentPlan
from utils.pagination import CustomPagination

# Create your views here.

class UserActivitiesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserActivitiesSerializer
    queryset = Activities.objects.all()
    pagination_class = CustomPagination
    def get(self, request):
        user = request.user
        queryset = queryset.filter(user=user).order_by("-created_at")
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


