from django.urls import path
from .views import *

urlpatterns = [
    path('hook/', Webhook.as_view(), name='user_activities'),
    path('notifications/', UserNotifications.as_view(), name='user_activities'),
    path('mark_as_read/', MarkAsRead.as_view(), name='mark_notification_as_read'),
]