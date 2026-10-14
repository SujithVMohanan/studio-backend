from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.models import User


class _RolePermission(BasePermission):
    role: str

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return bool(user.is_superuser or user.role == self.role)


class IsStaffRole(_RolePermission):
    role = User.Role.STAFF
    message = "Staff access required."


class IsMemberRole(_RolePermission):
    role = User.Role.MEMBER
    message = "Member access required."
