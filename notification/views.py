from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from user.models import User, Activities
from django.db import transaction
from user.consumers import send_socket_user_notification
from transaction.models import Transaction
# Create your views here.

class Webhook(views.APIView):
    # permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        data = request.data
        t_type = data.get("type")
        t_data = data.get("data")
        if not t_type == "transfer" or not t_data:
            return Response(data={"message":"success"})
        t_status = t_data.get("status")
        creditAccountNumber = t_data.get("creditAccountNumber")
        debitAccountName = t_data.get("debitAccountName")
        source = f"Bank Transfer/{debitAccountName}"
        amount = t_data.get("amount")
        if t_status != "Completed" or not creditAccountNumber or not amount:
            return Response(data={"message":"success"})
        user = User.objects.filter(account_number = creditAccountNumber).first()
        if not user:
            return Response(data={"message":"success"})
        with transaction.atomic():
            user.wallet_balance += amount
            new_activity = Activities.objects.create(title="Wallet Deposit", amount=amount, user=user, activity_type="CREDIT")
            new_transaction = Transaction.objects.create(
                user=user,
                amount = amount,
                source = source,
                status="SUCCESS",
                description = f"N{amount} deposited by {user.firstname}"
            )
            new_transaction.save()
            new_activity.save()
            user.save()
            data = {
                "balance": float(user.wallet_balance),
                "activity":{
                    "title":new_activity.title,
                    "amount": float(new_activity.amount),
                    "activity_type": new_activity.activity_type,
                    "created_at": new_activity.created_at.isoformat()
                }
            }
            send_socket_user_notification(user.id,data)
        return Response(data={"message":"success"})

    # serializer_class = UserActivitiesSerializer

'''
"message": {
        "balance": 40570.0,
        "activity": {
            "title": "N120 Deposit",
            "amount": 120.0,
            "activity_type": "CREDIT",
            "created_at": "2024-07-26T13:27:35.412542+00:00"
        }
    }
}


'''