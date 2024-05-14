from rest_framework import (permissions, generics, viewsets, filters)
from authentication.permissions import IsAdministrator
from rest_framework.response import Response
from user.models import User
from django.contrib.auth.models import Group
from .serializers import (
    AdminInviteSerializer
)
import random
import string
from utils.email import SendMail
from rest_framework import status
# Create your views here.

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password
class AdminInviteView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = AdminInviteSerializer
    queryset = User.objects.filter()
    def post(self, request):
        serializer = AdminInviteSerializer(data=request.data, many=True)
        if serializer.is_valid():
            created = []
            administrators = Group.objects.get(name="administrator")
            adminMember = Group.objects.get(name="member")
            for data in serializer.validated_data:
                email = data['email']
                role = data['role']
                user_exists = User.objects.filter(email=email).exists()
                if user_exists:
                    continue
                    # return Response(data={"message":f'User with {email} already exists'}, status=status.HTTP_400_BAD_REQUEST)
                password = generate_random_password()
                name = email.split('@')
                new_admin = User.objects.create(email=email, firstname=name[0], lastname=name[0],role="ADMIN")
                new_admin.set_password(password)
                new_admin.is_staff = True
                new_admin.is_verified = True
                if role == 'administrator':
                    new_admin.groups.add(administrators)
                elif role == 'member':
                    new_admin.groups.add(adminMember)
                new_admin.save()
                created.append(email)
                data = {"email": email, "password": password, "role": role}
                SendMail.send_invite_mail(data)
            return Response(f"The following accounts were created {created}", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
