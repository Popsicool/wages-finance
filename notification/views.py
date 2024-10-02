from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, views, permissions, parsers
from rest_framework.response import Response
from user.models import User, Activities
from django.db import transaction
from user.consumers import send_socket_user_notification
from transaction.models import Transaction
from notification.models import Notification
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from notification.serializers import NotificationSerializer, MarkAsRead
from utils.pagination import CustomPagination
from django.db.models import Case, When, F
# Create your views here.



class UserNotifications(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = CustomPagination
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by status',
                              type=openapi.TYPE_STRING, enum=['read', 'unread'], required=False),
        ]
    )
    def get(self, request):
        filter_status = self.request.query_params.get('status', None)
        if filter_status:
            filter_status = filter_status.strip().upper()
            if filter_status not in ["READ", "UNREAD"]:
                filter_status = None
        queryset =  self.get_queryset()
        if filter_status:
            queryset = queryset.filter(status=filter_status)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def get_queryset(self):
        user = self.request.user
        UNREAD = 'UNREAD'
        READ = 'READ'
        queryset = Notification.objects.filter(user=user).order_by(
            Case(
                When(status=UNREAD, then=1),
                When(status=READ, then=0),
                default=0,
            ).desc(),
            '-created_at'
        )
        return queryset

class MarkAsRead(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class =  MarkAsRead
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        mark_notifications = serializer.validated_data["notification_ids"]
        all_notifications = Notification.objects.filter(id__in=mark_notifications, status="UNREAD", user=user)
        for notification in all_notifications:
            notification.status = "READ"
            notification.save()
        return Response({"message": "success"}, status=status.HTTP_200_OK)
            


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
            # data = {
            #     "balance": float(user.wallet_balance),
            #     "activity":{
            #         "title":new_activity.title,
            #         "amount": float(new_activity.amount),
            #         "activity_type": new_activity.activity_type,
            #         "created_at": new_activity.created_at.isoformat()
            #     }
            # }
            # send_socket_user_notification(user.id,data)
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