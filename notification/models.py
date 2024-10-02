from django.db import models
from user.models import User

# Create your models here.
NOTIFICATION_TYPE = [
    ("EARNING", "User got earnings"),
    ("DIVIDEND", "User receive dividend on investment"),
    ("LOAN-UPDATE", "Update on loan request"),
    ("USER-TARGET", "Notification for user on their savings target"),
    ("OTHERS", "Other form of notification")
]
NOTIFICATION_STATUS = [
    ("UNREAD", "Unread"),
    ("READ", "Read")
]
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_notification")
    title = models.CharField(max_length=255)
    text = models.TextField()
    type = models.CharField(choices=NOTIFICATION_TYPE, default=NOTIFICATION_TYPE[0][0])
    status = models.CharField(choices=NOTIFICATION_STATUS, default=NOTIFICATION_STATUS[0][0])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} - {self.user.firstname} {self.user.lastname} - {self.status}"