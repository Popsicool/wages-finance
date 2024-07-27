from django.urls import path
from .views import *
urlpatterns = [
    path('activities/', UserActivitiesView.as_view(), name='user_activities'),
    path('dashboard/', UserDashboard.as_view(), name='user_dashboard'),
    path('investment_plans/', GetInvestmentPlans.as_view(),
         name='get_investment_plans'),
    path('invest/<id>/', UserInvest.as_view(), name='user_invest'),
    path('invest_history/', UserInvestmentHistory.as_view(),
         name='user_investment_history'),
    path('subscribe/', OneTimeSubscription.as_view(),
         name='one_time_subscription'),
    path('set_pin/', SetPin.as_view(), name='set_pin'),
    path('savings/', UserSavingsView.as_view(), name='user_savings'),
    path('set_savings/<int:id>', NewSavingsView.as_view(), name='set_pin'),
    path('fund_savings/<int:id>/', FundSavings.as_view(), name='fund_savings'),
    path('update_dp/', UpdateDPView.as_view(), name='set_pin'),
    path('withdrawal_request/', WithdrawalView.as_view(),
         name='withdrawal_request'),
    path('coop_details/', Coporative_dashboard.as_view(), name='coop_request'),
    path('request_loan/', LoanRequestView.as_view(), name='loan_request'),
    path('referals/', ReferalViews.as_view(), name='referals'),
    path('withdraw_referals/', WithdrawReferalBonus.as_view(),
         name='withdraw_referals'),
    path('request_reset_pin_token/', ResetPinToken.as_view(),
         name='request_reset_pin'),
    path('verify_reset_pin_token/', VerifyResetPin.as_view(),
         name='verify_reset_pin'),
    path('change_pin/', ChangePinView.as_view(),
         name='verify_reset_pin'),
    path('test_socket/<id>/', test_socket,
         name='verify_reset_pin'),
]
