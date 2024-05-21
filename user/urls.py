from django.urls import path
from .views import *

urlpatterns = [
    path('activities/', UserActivitiesView.as_view(), name='user_activities'),
    path('dashboard/', UserDashboard.as_view(), name='user_dashboard'),
    path('investment_plans/', GetInvestmentPlans.as_view(), name='get_investment_plans'),
]