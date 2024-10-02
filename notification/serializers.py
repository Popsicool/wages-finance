from rest_framework import serializers
from notification.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "text", "type", "status", "created_at"]

class MarkAsRead(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        min_length=1
    )