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
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower() and request.user.groups.filter(name='Administrator').exists()) or user.is_superuser

class IsLoanManager(permissions.BasePermission):
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Check if the user is authenticated and belongs to 'loan-officer' group
        return user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower() and request.user.groups.filter(name__in=['loan-manager','Administrator']).exists()
class IsAccountant(permissions.BasePermission):
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Check if the user is authenticated and belongs to 'loan-officer' group
        return user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower() and request.user.groups.filter(name__in=['Accountant','Administrator']).exists()
class IsCustomerSupport(permissions.BasePermission):
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Check if the user is authenticated and belongs to 'loan-officer' group
        return user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower() and request.user.groups.filter(name__in=['Customer-support','Administrator']).exists()
class IsAdminStaff(permissions.BasePermission):
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower()
class IsLoanOfficerOrAccountant(permissions.BasePermission):
    message = "You do not have the required permission to perform this action"
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_staff and user.is_active and user.is_verified and 'admin' == user.role.lower() and request.user.groups.filter(name__in=['loan-manager','Accountant','Administrator']).exists()

