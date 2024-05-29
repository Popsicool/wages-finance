from django.urls import path
from . import views

urlpatterns = [
    path('invite/', views.AdminInviteView.as_view(), name='admin_invite'),
    path('new_investment/', views.AdminCreateInvestment.as_view(), name='new_investment'),
    path('users/', views.GetUsersView.as_view(), name='new_investment'),
    path('withdrawal/', views.GetWithdrawals.as_view(), name='new_investment'),
    path('accept_withdrawal/<id>/', views.ApproveWithdrawal.as_view(), name='accept_withdrawal'),
    path('reject_withdrawal/<id>/', views.RejectWithdrawal.as_view(), name='reject_withdrawal'),
]