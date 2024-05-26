from django.urls import path
from .views import *

urlpatterns = [
    path('activities/', UserActivitiesView.as_view(), name='user_activities'),
    path('dashboard/', UserDashboard.as_view(), name='user_dashboard'),
    path('investment_plans/', GetInvestmentPlans.as_view(), name='get_investment_plans'),
    path('subscribe/', OneTimeSubscription.as_view(), name='one_time_subscription'),
    path('set_pin/', SetPin.as_view(), name='set_pin'),
    path('savings/', UserSavingsView.as_view(), name='user_savings'),
    path('new_savings/', NewSavingsView.as_view(), name='set_pin'),
    path('update_dp/', UpdateDPView.as_view(), name='set_pin'),
]