from django.urls import path
from . import views

urlpatterns = [
    path('invite/', views.AdminInviteView.as_view(), name='admin_invite'),
    path('new_investment/', views.AdminCreateInvestment.as_view(), name='new_investment'),
    path('users/', views.GetUsersView.as_view(), name='new_investment'),
]