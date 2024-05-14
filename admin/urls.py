from django.urls import path
from . import views

urlpatterns = [
    path('invite/', views.AdminInviteView.as_view(), name='admin_invite'),
]