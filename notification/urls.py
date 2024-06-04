from django.urls import path
from .views import *

urlpatterns = [
    path('hook/', Webhook.as_view(), name='user_activities'),
]