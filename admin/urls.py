from django.urls import path
from . import views
from authentication.views import SetNewPasswordAPIView

urlpatterns = [
    path('invite/', views.AdminInviteView.as_view(), name='admin_invite'),
    path('login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('request-reset-password-email/', views.RequestPasswordResetEmailView.as_view(),
         name='request-reset-password-email'),
    path('verify_code/', views.VerifyEmailResetCode.as_view(), name='admin_verify_code'),
    path('reset_password/', SetNewPasswordAPIView.as_view(), name='admin_reset_password'),
    path('new_investment/', views.AdminCreateInvestment.as_view(), name='new_investment'),
    path('users/', views.GetUsersView.as_view(), name='new_investment'),
    path('user/<id>', views.GetSingleUserView.as_view(), name='new_investment'),
    path('suspend/<id>', views.SuspendAccount.as_view(), name='suspend_account'),
    path('unsuspend/<id>', views.UnSuspendAccount.as_view(), name='suspend_account'),
    path('withdrawal/', views.GetWithdrawals.as_view(), name='new_investment'),
    path('active_coporative_members/', views.GetCooperativeUsersView.as_view(), name='active_coporative_members'),
    path('coporative_stats/', views.AdminCoporateSavingsDashboard.as_view(), name='admin_coporative_dashboard'),
    path('savings_stats/', views.AdminSavingsStatsView.as_view(), name='admin_savings_dashboard'),
    path('investment_stats/', views.AdminInvestmentDashboards.as_view(), name='admin_investment_dashboard'),
    path('savings/<str:name>/', views.SavingsType.as_view(), name='admin_savings_type'),
    path('single_savings/<str:id>/', views.AdminSingleSavings.as_view(), name='admin_single_savings'),
    path('accept_withdrawal/<id>/', views.ApproveWithdrawal.as_view(), name='accept_withdrawal'),
    path('reject_withdrawal/<id>/', views.RejectWithdrawal.as_view(), name='reject_withdrawal'),
    path("loan_dashboard", views.AdminLoanDashboard.as_view(), name="admin_loan_part"),
    path("loan_overview", views.AdminLoanOverview.as_view(), name="admin_loan_overview"),
    path("accept_loan/<id>", views.AdminAcceptLoan.as_view(), name="admin_accept_loan"),
    path("reject_loan/<id>", views.AdminRejectLoan.as_view(), name="admin_reject_overview"),
]