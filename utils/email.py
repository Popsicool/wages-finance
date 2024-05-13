from django.core.mail import EmailMessage
from django.conf import settings

class SendMail:
    
    @staticmethod
    def send_email(data):
        send_email= EmailMessage(subject=data["subject"],body=data["body"], from_email= settings.EMAIL_FROM_USER,to=[data["user"]])
        send_email.send()
    
    @staticmethod
    def send_invite_mail(data):
        SendMail.send_email(data)
    
    @staticmethod
    def send_welcome_mail(data):
        SendMail.send_email(data)
    
    @staticmethod
    def send_email_verification_mail(info):
        data = {}
        data["subject"] = "Email verification"
        message = f"Dear {info['firstname']} {info['lastname']}\n\nYour Verification code is {info['token']}"
        data["body"] = message
        data["user"] = info["user"]
        SendMail.send_email(data)

    @staticmethod
    def send_password_reset_mail(data, request, redirect_url):
        SendMail.send_email(data)