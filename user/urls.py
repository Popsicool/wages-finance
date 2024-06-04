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
    path('fund_savings/<id>/', FundSavings.as_view(), name='fund_savings'),
    path('update_dp/', UpdateDPView.as_view(), name='set_pin'),
    path('withdrawal_request/', WithdrawalView.as_view(), name='withdrawal_request'),
    path('coop_details/', Coporative_dashboard.as_view(), name='coop_request'),
    path('request_loan/', LoanRequestView.as_view(), name='loan_request'),
]