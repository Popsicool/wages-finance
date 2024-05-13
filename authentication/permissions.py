from rest_framework import permissions


class IsUser(permissions.BasePermission):
    """
    Global permission check for authorized Users
    """
    message = "Only Users can perform this action"

    def has_permission(self,request,view):
        user = request.user

        if not user:
            return False

        return 'users' == user.role.lower()
            

class IsSubscribed(permissions.BasePermission):
    """
    Global permission check for Subscribers
    """
    message = "Only Subscribers can perform this action"

    def has_permission(self, request, view):
        user = request.user
        if not user:
            return False
        return user.is_subscribed

class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user:
            return False
        return (user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower()) or user.is_superuser
